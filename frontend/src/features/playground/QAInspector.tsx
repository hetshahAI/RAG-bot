import React, { useState } from "react";
import {
  X,
  Sparkles,
  ShieldCheck,
  Cpu,
  Layers,
  BrainCircuit,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Copy,
  Check,
  FileText,
  Search,
} from "lucide-react";
import { RAGAskResponse, RAGExecutionTrace } from "../../types/backend";
import { Badge } from "../../components/common/Badge";
import { EvidenceViewer } from "./EvidenceViewer";
import { JsonViewer } from "../../components/common/JsonViewer";

interface QAInspectorProps {
  selectedNodeId: string | null;
  onClose: () => void;
  response: RAGAskResponse | null;
  trace: RAGExecutionTrace | null;
  onSelectChunk?: (chunkId: string) => void;
  highlightedChunkId?: string | null;
}

export const QAInspector: React.FC<QAInspectorProps> = ({
  selectedNodeId,
  onClose,
  response,
  trace,
  onSelectChunk,
  highlightedChunkId,
}) => {
  const [activeTab, setActiveTab] = useState<"overview" | "raw">("overview");
  const [copied, setCopied] = useState(false);

  if (!selectedNodeId || !response) return null;

  const currentEvent = trace?.events?.find((e) => e.node === selectedNodeId);
  const isInsufficient = response.status === "insufficient_evidence";

  const handleCopyAnswer = () => {
    if (response.llm.answer) {
      navigator.clipboard.writeText(response.llm.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getNodeTitle = (nodeId: string) => {
    switch (nodeId) {
      case "query":
        return { title: "User Query", desc: "Input question received by the pipeline" };
      case "embedding":
        return { title: "Embedding Vector", desc: "Dense semantic representation" };
      case "retrieval":
        return { title: "ChromaDB Candidate Evidence", desc: "Similarity filtered candidate chunks" };
      case "context_builder":
        return { title: "Context Grounding Prompt", desc: "Constructed prompt passed to LLM" };
      case "llm":
        return { title: "LLM Reasoning Engine", desc: "Answerability analysis & synthesis" };
      case "validator":
        return { title: "Citation & Grounding Validator", desc: "Hallucination & authenticity check" };
      case "answer":
        return { title: "Final Grounded Response", desc: "Validated answer with source citations" };
      default:
        return { title: "Node Inspector", desc: "Node details and execution trace" };
    }
  };

  const nodeInfo = getNodeTitle(selectedNodeId);

  return (
    <div className="w-96 border-l border-border-subtle bg-bg-card/95 backdrop-blur-md flex flex-col h-full overflow-hidden shadow-2xl z-20">
      {/* Header */}
      <div className="p-4 border-b border-border-subtle flex items-center justify-between gap-2 bg-bg-darkest/50">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-text-primary font-mono tracking-tight">
              {nodeInfo.title}
            </h3>
            {currentEvent?.duration_ms !== undefined && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-elevated text-text-secondary flex items-center gap-1">
                <Clock className="w-2.5 h-2.5 text-accent-blue" />
                {currentEvent.duration_ms}ms
              </span>
            )}
          </div>
          <p className="text-[11px] text-text-muted mt-0.5">{nodeInfo.desc}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-bg-elevated text-text-muted hover:text-text-primary transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center px-4 border-b border-border-subtle/70 bg-bg-darkest/20 text-xs font-mono">
        <button
          onClick={() => setActiveTab("overview")}
          className={`py-2 px-3 border-b-2 font-medium transition-colors ${
            activeTab === "overview"
              ? "border-accent text-accent-blue font-semibold"
              : "border-transparent text-text-muted hover:text-text-secondary"
          }`}
        >
          Analysis
        </button>
        <button
          onClick={() => setActiveTab("raw")}
          className={`py-2 px-3 border-b-2 font-medium transition-colors ${
            activeTab === "raw"
              ? "border-accent text-accent-blue font-semibold"
              : "border-transparent text-text-muted hover:text-text-secondary"
          }`}
        >
          Trace JSON
        </button>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === "raw" ? (
          <JsonViewer
            data={currentEvent || { nodeId: selectedNodeId, response }}
            title={`Trace Event: ${selectedNodeId}`}
            maxHeight="max-h-[600px]"
          />
        ) : (
          <>
            {/* Node-specific detailed views */}

            {/* 1. QUERY */}
            {selectedNodeId === "query" && (
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle text-xs">
                  <span className="text-[10px] uppercase font-mono text-text-muted block mb-1">
                    Input Question
                  </span>
                  <p className="text-text-primary font-medium leading-relaxed select-text">
                    "{response.question}"
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-bg-darkest border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">Length</span>
                    <span className="text-text-primary font-bold">
                      {response.question.length} chars
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-bg-darkest border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">Run ID</span>
                    <span className="text-accent-blue font-bold truncate block">
                      {response.run_id}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* 2. EMBEDDING */}
            {selectedNodeId === "embedding" && (
              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Model</span>
                    <span className="text-text-primary font-bold">BAAI/bge-small-en-v1.5</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Vector Dimension</span>
                    <span className="text-accent-blue font-bold">384 Dimensions</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">L2 Normalized</span>
                    <span className="text-accent-green font-bold">True</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Device</span>
                    <span className="text-text-primary">CPU / Accelerated</span>
                  </div>
                </div>
              </div>
            )}

            {/* 3. RETRIEVAL */}
            {selectedNodeId === "retrieval" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-text-muted">
                    Candidate Chunks ({response.retrieval.chunk_count})
                  </span>
                  <Badge variant="blue" size="sm">
                    Threshold: {response.retrieval.threshold}
                  </Badge>
                </div>
                <EvidenceViewer
                  chunks={response.retrieval.chunks}
                  threshold={response.retrieval.threshold}
                  highlightChunkId={highlightedChunkId}
                  onSelectChunk={onSelectChunk}
                />
              </div>
            )}

            {/* 4. CONTEXT BUILDER */}
            {selectedNodeId === "context_builder" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-text-muted">Assembled Context</span>
                  <span className="text-accent-purple">
                    {response.retrieval.chunks.length} Chunks Embedded
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle text-xs font-mono text-text-secondary leading-relaxed overflow-y-auto max-h-96 select-text">
                  {response.retrieval.chunks.map((c, i) => (
                    <div key={c.chunk_id} className="mb-3 pb-3 border-b border-border-subtle/50 last:border-0">
                      <span className="text-accent-blue font-semibold block mb-1">
                        [Chunk #{i + 1} | {c.title} | {c.chunk_id}]
                      </span>
                      <p className="text-text-primary font-sans">{c.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 5. LLM */}
            {selectedNodeId === "llm" && (
              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Model</span>
                    <span className="text-text-primary font-bold">mlx-community/Qwen3.6-35B-A3B-4bit</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Temperature</span>
                    <span className="text-accent-green font-bold">0.0 (Deterministic)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Provider</span>
                    <span className="text-text-primary">OpenAI-Compatible</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Outcome</span>
                    <Badge variant={isInsufficient ? "warning" : "success"}>
                      {response.llm.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              </div>
            )}

            {/* 6. VALIDATOR */}
            {selectedNodeId === "validator" && (
              <div className="space-y-3">
                <div
                  className={`p-3.5 rounded-xl border ${
                    isInsufficient
                      ? "bg-accent-amber/10 border-accent-amber/30 text-accent-amber"
                      : "bg-accent-green/10 border-accent-green/30 text-accent-green"
                  }`}
                >
                  <div className="flex items-center gap-2 font-mono font-bold text-xs">
                    {isInsufficient ? (
                      <>
                        <AlertTriangle className="w-4 h-4" />
                        <span>Abstention / Insufficient Evidence</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-4 h-4" />
                        <span>100% Evidence Grounded</span>
                      </>
                    )}
                  </div>
                  <p className="text-[11px] mt-1 text-text-secondary font-sans leading-relaxed">
                    {isInsufficient
                      ? "The knowledge base did not contain sufficient verified evidence to answer reliably. The LLM abstained without hallucinating."
                      : "All factual claims in the answer correspond to verified candidate chunks in ChromaDB."}
                  </p>
                </div>

                {/* Validated Citations */}
                <div className="space-y-2">
                  <span className="text-xs font-mono text-text-muted block">
                    Validated Citations ({response.llm.citations.length})
                  </span>
                  {response.llm.citations.map((cit, idx) => (
                    <div
                      key={cit.chunk_id}
                      onClick={() => onSelectChunk?.(cit.chunk_id)}
                      className="p-2.5 rounded-lg bg-bg-darkest border border-border-subtle hover:border-accent-blue transition-colors cursor-pointer text-xs font-mono flex items-center justify-between"
                    >
                      <div>
                        <span className="text-accent-blue font-bold block">
                          #{idx + 1} {cit.title || "Document"}
                        </span>
                        <span className="text-[10px] text-text-muted">{cit.chunk_id}</span>
                      </div>
                      <Badge variant="success" size="sm">
                        Verified
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 7. ANSWER */}
            {selectedNodeId === "answer" && (
              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-bg-darkest border border-border-subtle">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={isInsufficient ? "warning" : "success"}>
                      {isInsufficient ? "ABSTAINED" : "GROUNDED ANSWER"}
                    </Badge>
                    <button
                      onClick={handleCopyAnswer}
                      className="flex items-center gap-1 text-[11px] font-mono text-text-muted hover:text-text-primary px-2 py-1 rounded hover:bg-bg-elevated transition-colors"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3 text-accent-green" />
                          <span className="text-accent-green">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-text-primary leading-relaxed font-sans select-text whitespace-pre-wrap">
                    {response.llm.answer}
                  </p>
                </div>

                {/* Citations block */}
                {response.llm.citations.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-mono text-text-muted block">
                      Supporting Evidence Sources ({response.llm.citations.length})
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {response.llm.citations.map((cit) => (
                        <button
                          key={cit.chunk_id}
                          onClick={() => onSelectChunk?.(cit.chunk_id)}
                          className="px-2.5 py-1 rounded-lg bg-bg-elevated border border-border-subtle hover:border-accent-blue text-text-primary font-mono text-[11px] transition-colors flex items-center gap-1.5"
                        >
                          <FileText className="w-3 h-3 text-accent-blue" />
                          <span>{cit.title || cit.chunk_id}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
