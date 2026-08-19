import { Edge } from "@xyflow/react";
import { RAGAskResponse, RAGExecutionTrace, RAGTraceEvent } from "../types/backend";
import { CustomWorkflowNode, NodeExecutionStatus } from "../types/workflow";

export interface GraphBuildResult {
  nodes: CustomWorkflowNode[];
  edges: Edge[];
}

interface RawNodeItem {
  id: string;
  label: string;
  subtitle: string;
  iconName: string;
  status: NodeExecutionStatus;
  durationMs?: number;
  badge?: string;
  stats?: Record<string, string | number>;
  details: Record<string, any>;
  isHero?: boolean;
}

export function buildQAGraph(
  response: RAGAskResponse | null,
  trace: RAGExecutionTrace | null,
  selectedNodeId: string | null = null
): GraphBuildResult {
  const eventsByNode: Record<string, RAGTraceEvent> = {};
  if (trace && trace.events) {
    trace.events.forEach((evt) => {
      eventsByNode[evt.node] = evt;
    });
  }

  // Helper to map status
  const getStatus = (nodeName: string): NodeExecutionStatus => {
    if (!response) return "idle";
    const evt = eventsByNode[nodeName];
    if (!evt) {
      if (response.status === "insufficient_evidence" && (nodeName === "context_builder" || nodeName === "llm" || nodeName === "validator")) {
        return "skipped";
      }
      return "completed";
    }
    if (evt.status === "failed") return "failed";
    if (evt.status === "skipped") return "skipped";
    if (evt.status === "completed") {
      if (nodeName === "validator" && response.status === "insufficient_evidence") {
        return "warning";
      }
      return "completed";
    }
    return "idle";
  };

  const getDuration = (nodeName: string): number | undefined => {
    const evt = eventsByNode[nodeName];
    return evt ? evt.duration_ms : undefined;
  };

  const getDetails = (nodeName: string): Record<string, any> => {
    const evt = eventsByNode[nodeName];
    return evt ? evt.details : {};
  };

  const isInsufficient = response?.status === "insufficient_evidence";

  // Define 7 pipeline nodes horizontally or with clean spacing
  const rawNodes: RawNodeItem[] = [
    {
      id: "query",
      label: "User Query",
      subtitle: "Input Prompt",
      iconName: "MessageSquare",
      status: getStatus("query"),
      durationMs: getDuration("query"),
      badge: "Stage 1",
      stats: {
        Length: response ? `${response.question.length} chars` : "-",
      },
      details: {
        question: response?.question || "",
        ...getDetails("query"),
      },
    },
    {
      id: "embedding",
      label: "Query Embedding",
      subtitle: "Dense Vector 384d",
      iconName: "Cpu",
      status: getStatus("embedding"),
      durationMs: getDuration("embedding"),
      badge: "BGE-Small",
      stats: {
        Model: "BAAI/bge-small-en-v1.5",
        Dimensions: 384,
      },
      details: {
        model: "BAAI/bge-small-en-v1.5",
        dimension: 384,
        ...getDetails("embedding"),
      },
    },
    {
      id: "retrieval",
      label: "ChromaDB Retrieval",
      subtitle: "Candidate Filter",
      iconName: "Search",
      status: getStatus("retrieval"),
      durationMs: getDuration("retrieval"),
      badge: response ? `${response.retrieval.chunk_count} Chunks` : undefined,
      stats: {
        Found: response ? response.retrieval.chunk_count : 0,
        Threshold: response ? response.retrieval.threshold : 0.5,
      },
      details: {
        status: response?.retrieval.status || "idle",
        threshold: response?.retrieval.threshold || 0.5,
        chunk_count: response?.retrieval.chunk_count || 0,
        chunks: response?.retrieval.chunks || [],
        ...getDetails("retrieval"),
      },
    },
    {
      id: "context_builder",
      label: "Context Builder",
      subtitle: "Prompt Grounding",
      iconName: "Layers",
      status: getStatus("context_builder"),
      durationMs: getDuration("context_builder"),
      badge: "Isolated",
      stats: {
        Sources: response?.retrieval.chunks ? new Set(response.retrieval.chunks.map(c => c.document_id)).size : 0,
        Chunks: response?.retrieval.chunks.length || 0,
      },
      details: {
        included_chunks: response?.retrieval.chunks || [],
        ...getDetails("context_builder"),
      },
    },
    {
      id: "llm",
      label: "LLM Reasoning",
      subtitle: "Qwen3.6-35B-A3B",
      iconName: "BrainCircuit",
      status: getStatus("llm"),
      durationMs: getDuration("llm"),
      badge: isInsufficient ? "Abstained" : "Synthesized",
      stats: {
        Temp: 0.0,
        Outcome: response?.llm.status || "-",
      },
      details: {
        provider: "openai-compatible",
        model: "mlx-community/Qwen3.6-35B-A3B-4bit",
        temperature: 0.0,
        outcome: response?.llm.status || "idle",
        ...getDetails("llm"),
      },
    },
    {
      id: "validator",
      label: "Citation Validator",
      subtitle: "Hallucination Check",
      iconName: "ShieldCheck",
      status: getStatus("validator"),
      durationMs: getDuration("validator"),
      badge: isInsufficient ? "Review" : "100% Grounded",
      stats: {
        Citations: response?.llm.citations.length || 0,
        Status: isInsufficient ? "Abstain" : "Verified",
      },
      details: {
        citations: response?.llm.citations || [],
        is_grounded: !isInsufficient && (response?.llm.citations.length ?? 0) > 0,
        ...getDetails("validator"),
      },
    },
    {
      id: "answer",
      label: "Grounded Answer",
      subtitle: "Synthesized Output",
      iconName: "CheckCircle2",
      status: getStatus("answer"),
      durationMs: getDuration("answer"),
      badge: isInsufficient ? "Abstention" : "Verified",
      isHero: true,
      stats: {
        Result: isInsufficient ? "Abstained" : "Answered",
        Citations: response?.llm.citations.length || 0,
      },
      details: {
        status: response?.status || "idle",
        answer: response?.llm.answer || "",
        citations: response?.llm.citations || [],
        ...getDetails("answer"),
      },
    },
  ];

  // Layout calculations
  const X_SPACING = 270;
  const Y_OFFSET = 120;

  const nodes: CustomWorkflowNode[] = rawNodes.map((rn, idx) => ({
    id: rn.id,
    type: "customNode",
    position: { x: idx * X_SPACING, y: Y_OFFSET },
    data: {
      id: rn.id,
      label: rn.label,
      category: "playground",
      subtitle: rn.subtitle,
      iconName: rn.iconName,
      status: rn.status,
      durationMs: rn.durationMs,
      badge: rn.badge,
      stats: rn.stats,
      details: rn.details,
      isSelected: selectedNodeId === rn.id,
      isHero: rn.isHero,
    },
  }));

  // Build sequential edges
  const edges: Edge[] = [];
  for (let i = 0; i < rawNodes.length - 1; i++) {
    const sourceNode = rawNodes[i];
    const targetNode = rawNodes[i + 1];
    const isEdgeActive = sourceNode.status === "completed" && targetNode.status !== "idle" && targetNode.status !== "skipped";

    edges.push({
      id: `e-${sourceNode.id}-${targetNode.id}`,
      source: sourceNode.id,
      target: targetNode.id,
      animated: isEdgeActive,
      style: {
        stroke: isEdgeActive ? "#388bfd" : "#30363d",
        strokeWidth: isEdgeActive ? 2.5 : 1.5,
        strokeDasharray: targetNode.status === "skipped" ? "4 4" : undefined,
      },
    });
  }

  return { nodes, edges };
}
