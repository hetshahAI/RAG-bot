import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.core.config import settings
from app.models.schemas import (
    CitationItem,
    RAGAskResponse,
    RAGExecutionTrace,
    RAGLLMDetail,
    RAGRetrievalDetail,
    RAGTraceEvent,
    RetrievalChunk,
    RetrievalResponse,
)
from app.services.index_state import get_index_state_service
from app.services.interfaces import (
    IIndexStateService,
    ILLMClient,
    IRAGService,
    IRetrievalService,
)
from app.services.llm import get_llm_client
from app.services.retrieval import get_retrieval_service

logger = logging.getLogger("rag-backend.rag")

ABSTENTION_ANSWER = "I don't have enough information in the selected knowledge base to answer this question."

SYSTEM_GROUNDING_PROMPT = """You are a knowledge-base question answering assistant.

Answer the user's question using the provided retrieved context.

First determine whether the retrieved context contains enough information to answer the question.

If the context contains enough information:
- formulate the best answer from the context
- synthesize information across multiple retrieved chunks when necessary
- do not invent facts
- do not introduce factual information that is not supported by the retrieved context.

If the context does not contain enough information:
- return insufficient_evidence
- do not use your pretrained knowledge to fill missing information.

The retrieved context is the only factual knowledge source for this answer.

OUTPUT FORMAT REQUIREMENTS:
You MUST respond with a single, valid JSON object matching this schema:
{
  "status": "answered" | "insufficient_evidence",
  "answer": "<formulated answer from context, or abstention message if insufficient_evidence>",
  "citations": [
    {
      "chunk_id": "<exact chunk_id from context>",
      "document_id": "<exact document_id from context>",
      "title": "<exact document title or filename from context>"
    }
  ]
}

If status is "insufficient_evidence", citations MUST be an empty array [] and answer should state that the knowledge base does not contain enough information.
Do NOT enclose your response in backticks or markdown if possible, return valid raw JSON only."""


# ============================================================================
# Privacy & Security Sanitization for Traces
# ============================================================================


def sanitize_trace_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure no secrets, API keys, tokens, or sensitive credentials appear in execution traces."""
    sensitive_substrings = ("key", "secret", "token", "password", "auth", "bearer")
    sanitized: Dict[str, Any] = {}
    for k, v in details.items():
        k_lower = k.lower()
        if any(s in k_lower for s in sensitive_substrings):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_trace_details(v)
        elif isinstance(v, (str, int, float, bool, list)):
            sanitized[k] = v
        else:
            sanitized[k] = str(v)
    return sanitized


# ============================================================================
# Execution Trace Store
# ============================================================================


class ExecutionTracer:
    """Thread-safe in-memory store for RAG execution traces."""

    def __init__(self, max_runs: int = 200):
        self._lock = threading.Lock()
        self._runs: Dict[str, RAGExecutionTrace] = {}
        self._max_runs = max_runs

    def save_trace(self, trace: RAGExecutionTrace) -> None:
        """Store an execution trace, evicting oldest if capacity exceeded."""
        with self._lock:
            if len(self._runs) >= self._max_runs:
                oldest_key = next(iter(self._runs))
                del self._runs[oldest_key]
            self._runs[trace.run_id] = trace

    def get_trace(self, run_id: str) -> Optional[RAGExecutionTrace]:
        """Retrieve an execution trace by run_id."""
        with self._lock:
            return self._runs.get(run_id)


# ============================================================================
# Answer Validator
# ============================================================================


class AnswerValidator:
    """Strict validator for structured LLM outputs and citations."""

    @staticmethod
    def extract_json_payload(raw_text: str) -> Dict[str, Any]:
        """Extract and parse JSON from raw LLM output, stripping potential markdown blocks."""
        cleaned = raw_text.strip()
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        return json.loads(cleaned)

    @classmethod
    def validate(
        cls,
        raw_llm_output: str,
        retrieved_chunks: List[RetrievalChunk],
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate LLM output against grounding and citation constraints."""
        # 1. Parse JSON
        try:
            data = cls.extract_json_payload(raw_llm_output)
        except Exception as e:
            return False, f"LLM output is not valid JSON: {str(e)}", None

        if not isinstance(data, dict):
            return False, "LLM output is not a JSON object.", None

        status = data.get("status")
        if status not in ("answered", "insufficient_evidence"):
            return False, f"Invalid status field '{status}'. Must be 'answered' or 'insufficient_evidence'.", None

        # 2. If status == insufficient_evidence
        if status == "insufficient_evidence":
            return True, "LLM reported insufficient evidence.", data

        # 3. If status == answered
        answer = data.get("answer")
        if not answer or not isinstance(answer, str) or not answer.strip():
            return False, "Answer field is empty or missing despite status='answered'.", None

        citations = data.get("citations")
        if citations is None:
            citations = []
        if not isinstance(citations, list):
            return False, "Citations field must be a list.", None

        # 4. Strict Citation Validation: every citation must match an actually retrieved chunk
        retrieved_ids_map: Dict[str, RetrievalChunk] = {c.chunk_id: c for c in retrieved_chunks}
        validated_citations: List[CitationItem] = []

        for idx, cit in enumerate(citations):
            if isinstance(cit, str):
                chunk_id = cit.strip()
                if chunk_id not in retrieved_ids_map:
                    return (
                        False,
                        f"Citation at index {idx} references unretrieved chunk_id: '{chunk_id}'.",
                        None,
                    )
                origin_chunk = retrieved_ids_map[chunk_id]
                validated_citations.append(
                    CitationItem(
                        chunk_id=origin_chunk.chunk_id,
                        document_id=origin_chunk.document_id,
                        title=origin_chunk.title,
                    )
                )
            elif isinstance(cit, dict):
                chunk_id = cit.get("chunk_id")
                if not chunk_id or chunk_id not in retrieved_ids_map:
                    return (
                        False,
                        f"Citation at index {idx} references unretrieved or hallucinated chunk_id: '{chunk_id}'.",
                        None,
                    )
                origin_chunk = retrieved_ids_map[chunk_id]
                validated_citations.append(
                    CitationItem(
                        chunk_id=origin_chunk.chunk_id,
                        document_id=origin_chunk.document_id,
                        title=origin_chunk.title,
                    )
                )
            else:
                return False, f"Citation at index {idx} is not an object or string.", None

        data["validated_citations"] = validated_citations
        return True, "Validation successful.", data


# ============================================================================
# RAG Service Implementation
# ============================================================================


class RAGService(IRAGService):
    """Orchestrator for the strict grounded RAG question-answering pipeline."""

    def __init__(
        self,
        retrieval_service: Optional[IRetrievalService] = None,
        llm_client: Optional[ILLMClient] = None,
        index_state_service: Optional[IIndexStateService] = None,
        tracer: Optional[ExecutionTracer] = None,
    ):
        self.retrieval_service = retrieval_service or get_retrieval_service()
        self.llm_client = llm_client or get_llm_client()
        self.index_state_service = index_state_service or get_index_state_service()
        self.tracer = tracer or _default_tracer

    def _create_event(
        self,
        node: str,
        status: str,
        started_at: datetime,
        completed_at: datetime,
        details: Dict[str, Any],
    ) -> RAGTraceEvent:
        duration_ms = max(0.0, (completed_at - started_at).total_seconds() * 1000.0)
        return RAGTraceEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            node=node,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round(duration_ms, 2),
            details=sanitize_trace_details(details),
        )

    def _build_context_prompt(self, question: str, chunks: List[RetrievalChunk]) -> str:
        """Construct prompt containing ONLY retrieved candidate context blocks and user question."""
        context_blocks = []
        for c in chunks:
            title_str = c.title or "Untitled Document"
            block = (
                f"[Document: {title_str} | Document ID: {c.document_id} | Chunk ID: {c.chunk_id}]\n"
                f"{c.content}"
            )
            context_blocks.append(block)

        joined_context = "\n\n".join(context_blocks)
        return (
            f"=== KNOWLEDGE BASE CONTEXT ===\n"
            f"{joined_context}\n\n"
            f"=== USER QUESTION ===\n"
            f"{question}"
        )

    def ask(
        self,
        question: str,
        top_k: Optional[int] = None,
    ) -> RAGAskResponse:
        """Execute complete grounded RAG QA pipeline returning both retrieval details and LLM output."""
        if not question or not question.strip():
            raise ValueError("Question cannot be empty or whitespace only.")

        clean_question = question.strip()
        run_id = f"run_{uuid.uuid4().hex}"
        trace_events: List[RAGTraceEvent] = []

        # Get active document state
        active_state = self.index_state_service.get_state()
        active_doc_count = len(active_state.active_document_ids)

        # --------------------------------------------------------------------
        # Node 1: query
        # --------------------------------------------------------------------
        t_start = datetime.now(timezone.utc)
        trace_events.append(
            self._create_event(
                node="query",
                status="completed",
                started_at=t_start,
                completed_at=datetime.now(timezone.utc),
                details={
                    "question": clean_question,
                    "top_k_override": top_k,
                    "active_documents": active_state.active_document_ids,
                },
            )
        )

        # --------------------------------------------------------------------
        # Node 2: embedding & retrieval
        # --------------------------------------------------------------------
        t_ret_start = datetime.now(timezone.utc)
        retrieval_response: Optional[RetrievalResponse] = None
        try:
            t_emb_start = datetime.now(timezone.utc)
            retrieval_response = self.retrieval_service.retrieve(
                question=clean_question,
                top_k=top_k,
            )
            t_ret_end = datetime.now(timezone.utc)

            # Node: embedding
            trace_events.append(
                self._create_event(
                    node="embedding",
                    status="completed",
                    started_at=t_emb_start,
                    completed_at=t_ret_end,
                    details={
                        "model": settings.rag.embedding.model_name,
                        "dimension": settings.rag.embedding.dimension,
                        "device": settings.rag.embedding.device,
                    },
                )
            )

            # Node: retrieval
            trace_events.append(
                self._create_event(
                    node="retrieval",
                    status="completed",
                    started_at=t_ret_start,
                    completed_at=t_ret_end,
                    details={
                        "status": retrieval_response.status,
                        "chunk_count": retrieval_response.chunk_count,
                        "threshold": retrieval_response.threshold,
                        "retrieved_chunk_ids": [c.chunk_id for c in retrieval_response.chunks],
                    },
                )
            )
        except Exception as e:
            t_ret_end = datetime.now(timezone.utc)
            logger.error("Retrieval failed during RAG ask: %s", e)
            trace_events.append(
                self._create_event(
                    node="retrieval",
                    status="failed",
                    started_at=t_ret_start,
                    completed_at=t_ret_end,
                    details={"error": str(e)},
                )
            )
            trace_events.append(
                self._create_event(
                    node="answer",
                    status="completed",
                    started_at=t_ret_end,
                    completed_at=datetime.now(timezone.utc),
                    details={"outcome": "insufficient_evidence", "reason": "retrieval_error"},
                )
            )
            full_trace = RAGExecutionTrace(
                run_id=run_id,
                question=clean_question,
                active_document_count=active_doc_count,
                events=trace_events,
            )
            self.tracer.save_trace(full_trace)
            return RAGAskResponse(
                run_id=run_id,
                status="insufficient_evidence",
                question=clean_question,
                retrieval=RAGRetrievalDetail(
                    status="no_candidates",
                    chunk_count=0,
                    threshold=settings.rag.retrieval.similarity_threshold,
                    chunks=[],
                ),
                llm=RAGLLMDetail(
                    status="insufficient_evidence",
                    answer=ABSTENTION_ANSWER,
                    citations=[],
                ),
            )

        # --------------------------------------------------------------------
        # Check Candidate Availability
        # --------------------------------------------------------------------
        retrieval_detail = RAGRetrievalDetail(
            status=retrieval_response.status,
            chunk_count=retrieval_response.chunk_count,
            threshold=retrieval_response.threshold,
            chunks=retrieval_response.chunks,
        )

        has_candidates = len(retrieval_response.chunks) > 0

        if not has_candidates:
            t_now = datetime.now(timezone.utc)
            for skipped_node in ("context_builder", "llm", "validator"):
                trace_events.append(
                    self._create_event(
                        node=skipped_node,
                        status="skipped",
                        started_at=t_now,
                        completed_at=t_now,
                        details={"reason": "no_candidate_chunks_found"},
                    )
                )

            trace_events.append(
                self._create_event(
                    node="answer",
                    status="completed",
                    started_at=t_now,
                    completed_at=datetime.now(timezone.utc),
                    details={"outcome": "insufficient_evidence", "llm_called": False},
                )
            )

            full_trace = RAGExecutionTrace(
                run_id=run_id,
                question=clean_question,
                active_document_count=active_doc_count,
                events=trace_events,
            )
            self.tracer.save_trace(full_trace)

            return RAGAskResponse(
                run_id=run_id,
                status="insufficient_evidence",
                question=clean_question,
                retrieval=retrieval_detail,
                llm=RAGLLMDetail(
                    status="insufficient_evidence",
                    answer=ABSTENTION_ANSWER,
                    citations=[],
                ),
            )

        # --------------------------------------------------------------------
        # Node 3: context_builder
        # --------------------------------------------------------------------
        t_ctx_start = datetime.now(timezone.utc)
        user_prompt = self._build_context_prompt(clean_question, retrieval_response.chunks)
        messages = [
            {"role": "system", "content": SYSTEM_GROUNDING_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        trace_events.append(
            self._create_event(
                node="context_builder",
                status="completed",
                started_at=t_ctx_start,
                completed_at=datetime.now(timezone.utc),
                details={
                    "chunks_included": len(retrieval_response.chunks),
                    "prompt_length_chars": len(user_prompt),
                },
            )
        )

        # --------------------------------------------------------------------
        # Node 4: llm (Answerability Analysis & Synthesis)
        # --------------------------------------------------------------------
        t_llm_start = datetime.now(timezone.utc)
        raw_llm_output = ""
        try:
            raw_llm_output = self.llm_client.generate_chat_completion(
                messages=messages,
                temperature=settings.rag.llm.temperature,
                max_tokens=settings.rag.llm.max_tokens,
                response_format={"type": "json_object"},
            )
            trace_events.append(
                self._create_event(
                    node="llm",
                    status="completed",
                    started_at=t_llm_start,
                    completed_at=datetime.now(timezone.utc),
                    details={
                        "model": settings.rag.llm.model,
                        "provider": settings.rag.llm.provider,
                        "response_length_chars": len(raw_llm_output),
                    },
                )
            )
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            trace_events.append(
                self._create_event(
                    node="llm",
                    status="failed",
                    started_at=t_llm_start,
                    completed_at=datetime.now(timezone.utc),
                    details={"error": str(e)},
                )
            )
            t_now = datetime.now(timezone.utc)
            trace_events.append(
                self._create_event(
                    node="validator",
                    status="skipped",
                    started_at=t_now,
                    completed_at=t_now,
                    details={"reason": "llm_call_failed"},
                )
            )
            trace_events.append(
                self._create_event(
                    node="answer",
                    status="completed",
                    started_at=t_now,
                    completed_at=datetime.now(timezone.utc),
                    details={"outcome": "insufficient_evidence", "reason": "llm_error"},
                )
            )
            full_trace = RAGExecutionTrace(
                run_id=run_id,
                question=clean_question,
                active_document_count=active_doc_count,
                events=trace_events,
            )
            self.tracer.save_trace(full_trace)
            return RAGAskResponse(
                run_id=run_id,
                status="insufficient_evidence",
                question=clean_question,
                retrieval=retrieval_detail,
                llm=RAGLLMDetail(
                    status="insufficient_evidence",
                    answer=ABSTENTION_ANSWER,
                    citations=[],
                ),
            )

        # --------------------------------------------------------------------
        # Node 5: validator
        # --------------------------------------------------------------------
        t_val_start = datetime.now(timezone.utc)
        is_valid, validation_reason, parsed_data = AnswerValidator.validate(
            raw_llm_output=raw_llm_output,
            retrieved_chunks=retrieval_response.chunks,
        )

        if not is_valid or not parsed_data:
            trace_events.append(
                self._create_event(
                    node="validator",
                    status="failed",
                    started_at=t_val_start,
                    completed_at=datetime.now(timezone.utc),
                    details={"is_valid": False, "reason": validation_reason},
                )
            )
            trace_events.append(
                self._create_event(
                    node="answer",
                    status="completed",
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    details={"outcome": "insufficient_evidence", "reason": "validator_rejected"},
                )
            )
            full_trace = RAGExecutionTrace(
                run_id=run_id,
                question=clean_question,
                active_document_count=active_doc_count,
                events=trace_events,
            )
            self.tracer.save_trace(full_trace)
            return RAGAskResponse(
                run_id=run_id,
                status="insufficient_evidence",
                question=clean_question,
                retrieval=retrieval_detail,
                llm=RAGLLMDetail(
                    status="insufficient_evidence",
                    answer=ABSTENTION_ANSWER,
                    citations=[],
                ),
            )

        trace_events.append(
            self._create_event(
                node="validator",
                status="completed",
                started_at=t_val_start,
                completed_at=datetime.now(timezone.utc),
                details={
                    "is_valid": True,
                    "status_field": parsed_data.get("status"),
                    "citations_validated": len(parsed_data.get("validated_citations", [])),
                },
            )
        )

        # --------------------------------------------------------------------
        # Node 6: answer (Final Response Assembly)
        # --------------------------------------------------------------------
        t_ans_start = datetime.now(timezone.utc)
        final_status = parsed_data.get("status", "answered")

        if final_status == "insufficient_evidence":
            final_answer = ABSTENTION_ANSWER
            citations: List[CitationItem] = []
        else:
            final_answer = parsed_data.get("answer", "").strip()
            citations = parsed_data.get("validated_citations", [])

        trace_events.append(
            self._create_event(
                node="answer",
                status="completed",
                started_at=t_ans_start,
                completed_at=datetime.now(timezone.utc),
                details={
                    "outcome": final_status,
                    "citation_count": len(citations),
                    "answer_length": len(final_answer),
                },
            )
        )

        full_trace = RAGExecutionTrace(
            run_id=run_id,
            question=clean_question,
            active_document_count=active_doc_count,
            events=trace_events,
        )
        self.tracer.save_trace(full_trace)

        return RAGAskResponse(
            run_id=run_id,
            status=final_status,
            question=clean_question,
            retrieval=retrieval_detail,
            llm=RAGLLMDetail(
                status=final_status,
                answer=final_answer,
                citations=citations,
            ),
        )

    def get_run_trace(self, run_id: str) -> Optional[RAGExecutionTrace]:
        """Retrieve stored execution trace by run_id."""
        return self.tracer.get_trace(run_id)


_default_tracer = ExecutionTracer()
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> IRAGService:
    """Dependency provider for RAGService."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
