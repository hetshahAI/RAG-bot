import { Edge } from "@xyflow/react";
import {
  DocumentListResponse,
  EmbeddingInfoResponse,
  IndexStateModel,
  ReindexResponse,
  VectorStoreInfoResponse,
} from "../types/backend";
import { CustomWorkflowNode, NodeExecutionStatus } from "../types/workflow";

export interface StudioState {
  documents?: DocumentListResponse | null;
  indexState?: IndexStateModel | null;
  embeddingInfo?: EmbeddingInfoResponse | null;
  vectorStoreInfo?: VectorStoreInfoResponse | null;
  reindexExecution?: ReindexResponse | null;
  isReindexing?: boolean;
}

interface RawStudioNodeItem {
  id: string;
  label: string;
  subtitle: string;
  iconName: string;
  status: NodeExecutionStatus;
  badge?: string;
  stats?: Record<string, string | number>;
  details: Record<string, any>;
  isHero?: boolean;
}

export function buildStudioGraph(
  state: StudioState,
  selectedNodeId: string | null = null
): { nodes: CustomWorkflowNode[]; edges: Edge[] } {
  const isReindexing = state.isReindexing;
  const isDone = !!state.reindexExecution;

  const getStageStatus = (_: number): NodeExecutionStatus => {
    if (isReindexing) return "running";
    if (isDone) return "completed";
    return "completed";
  };

  const rawNodes: RawStudioNodeItem[] = [
    {
      id: "documents",
      label: "Raw Documents",
      subtitle: "data/raw/ Storage",
      iconName: "FolderArchive",
      status: getStageStatus(0),
      badge: `${state.documents?.total_count || 0} Total`,
      stats: {
        Total: state.documents?.total_count || 0,
        Active: state.documents?.active_count || 0,
      },
      details: {
        total_documents: state.documents?.total_count || 0,
        active_documents: state.documents?.active_count || 0,
        documents: state.documents?.documents || [],
        storage_path: "backend/data/raw/",
      },
    },
    {
      id: "ingestion",
      label: "Ingestion / Parser",
      subtitle: "TXT, PDF, OCR (Tesseract)",
      iconName: "FileSpreadsheet",
      status: getStageStatus(1),
      badge: "Multi-modal",
      stats: {
        Engines: "pypdf, OCR",
        Formats: "txt, pdf, img",
      },
      details: {
        supported_formats: ["txt", "pdf", "png", "jpg", "jpeg", "webp"],
        ocr_engine: "tesseract (eng)",
        normalization: "whitespace, linebreaks",
      },
    },
    {
      id: "chunking",
      label: "Deterministic Chunking",
      subtitle: "Recursive Separator",
      iconName: "Scissors",
      status: getStageStatus(2),
      badge: "512 chars",
      stats: {
        Size: state.indexState?.chunking_config?.chunk_size || 512,
        Overlap: state.indexState?.chunking_config?.chunk_overlap || 64,
      },
      details: {
        chunk_size: state.indexState?.chunking_config?.chunk_size || 512,
        chunk_overlap: state.indexState?.chunking_config?.chunk_overlap || 64,
        separator: "\\n\\n",
        deterministic_ids: "chunk_{doc_id}_{index}",
      },
    },
    {
      id: "embedding",
      label: "Embedding Generator",
      subtitle: "BAAI/bge-small-en-v1.5",
      iconName: "Cpu",
      status: getStageStatus(3),
      badge: "384d / L2 Norm",
      stats: {
        Dimension: state.embeddingInfo?.dimension || 384,
        Device: state.embeddingInfo?.device || "cpu",
      },
      details: {
        model_name: state.embeddingInfo?.model_name || "BAAI/bge-small-en-v1.5",
        dimension: state.embeddingInfo?.dimension || 384,
        device: state.embeddingInfo?.device || "cpu",
        normalize_embeddings: state.embeddingInfo?.normalize_embeddings ?? true,
      },
    },
    {
      id: "indexing",
      label: "Selective Index State",
      subtitle: "Knowledge Boundary",
      iconName: "ListFilter",
      status: getStageStatus(4),
      badge: state.indexState?.indexing_version || "v1",
      stats: {
        Version: state.indexState?.indexing_version || "v1",
        ActiveDocs: state.indexState?.active_document_ids?.length || 0,
      },
      details: {
        indexing_version: state.indexState?.indexing_version || "v1",
        active_document_ids: state.indexState?.active_document_ids || [],
        updated_at: state.indexState?.updated_at || "N/A",
        state_file: "backend/data/indexes/index_state.json",
      },
    },
    {
      id: "vector_store",
      label: "ChromaDB Store",
      subtitle: "Persistent Vector Index",
      iconName: "Database",
      status: getStageStatus(5),
      badge: `${state.vectorStoreInfo?.point_count || 0} Vectors`,
      isHero: true,
      stats: {
        Vectors: state.vectorStoreInfo?.point_count || 0,
        Metric: "cosine",
      },
      details: {
        provider: state.vectorStoreInfo?.provider || "chromadb",
        collection_name: state.vectorStoreInfo?.collection_name || "rag_documents",
        point_count: state.vectorStoreInfo?.point_count || 0,
        dimension: state.vectorStoreInfo?.vector_dimension || 384,
        persistence_path: state.vectorStoreInfo?.persistence_path || "backend/data/indexes/chroma",
      },
    },
  ];

  const X_SPACING = 270;
  const Y_OFFSET = 120;

  const nodes: CustomWorkflowNode[] = rawNodes.map((rn, idx) => ({
    id: rn.id,
    type: "customNode",
    position: { x: idx * X_SPACING, y: Y_OFFSET },
    data: {
      id: rn.id,
      label: rn.label,
      category: "injection",
      subtitle: rn.subtitle,
      iconName: rn.iconName,
      status: rn.status,
      badge: rn.badge,
      stats: rn.stats,
      details: rn.details,
      isSelected: selectedNodeId === rn.id,
      isHero: rn.isHero,
    },
  }));

  const edges: Edge[] = [];
  for (let i = 0; i < rawNodes.length - 1; i++) {
    const sourceNode = rawNodes[i];
    const targetNode = rawNodes[i + 1];

    edges.push({
      id: `e-studio-${sourceNode.id}-${targetNode.id}`,
      source: sourceNode.id,
      target: targetNode.id,
      animated: isReindexing,
      style: {
        stroke: isReindexing ? "#388bfd" : "#30363d",
        strokeWidth: 2,
      },
    });
  }

  return { nodes, edges };
}
