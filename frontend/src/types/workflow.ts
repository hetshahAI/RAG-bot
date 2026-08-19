import { Node } from "@xyflow/react";
import { RAGTraceEvent, RetrievalChunk, CitationItem } from "./backend";

export type NodeExecutionStatus = "idle" | "running" | "completed" | "warning" | "failed" | "skipped";

export interface WorkflowNodeData extends Record<string, unknown> {
  id: string;
  label: string;
  category: "injection" | "playground";
  subtitle?: string;
  iconName: string;
  status: NodeExecutionStatus;
  durationMs?: number;
  badge?: string;
  stats?: Record<string, string | number>;
  details?: Record<string, any>;
  isSelected?: boolean;
  isHero?: boolean;
}

export type CustomWorkflowNode = Node<WorkflowNodeData, "customNode">;

export interface SelectedNodeInfo {
  nodeId: string;
  category: "injection" | "playground";
  label: string;
  status: NodeExecutionStatus;
  durationMs?: number;
  details: Record<string, any>;
  retrievalChunks?: RetrievalChunk[];
  citations?: CitationItem[];
  answer?: string;
  rawTraceEvent?: RAGTraceEvent;
}
