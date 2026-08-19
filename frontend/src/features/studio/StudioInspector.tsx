import React, { useState } from "react";
import {
  X,
  FolderArchive,
  FileSpreadsheet,
  Scissors,
  Cpu,
  ListFilter,
  Database,
  Trash2,
  CheckCircle2,
} from "lucide-react";
import {
  DocumentListResponse,
  EmbeddingInfoResponse,
  IndexStateModel,
  VectorStoreInfoResponse,
} from "../../types/backend";
import { Badge } from "../../components/common/Badge";
import { JsonViewer } from "../../components/common/JsonViewer";
import { api } from "../../api/endpoints";

interface StudioInspectorProps {
  selectedNodeId: string | null;
  onClose: () => void;
  documents?: DocumentListResponse | null;
  indexState?: IndexStateModel | null;
  embeddingInfo?: EmbeddingInfoResponse | null;
  vectorInfo?: VectorStoreInfoResponse | null;
  onRefresh?: () => void;
}

export const StudioInspector: React.FC<StudioInspectorProps> = ({
  selectedNodeId,
  onClose,
  documents,
  indexState,
  embeddingInfo,
  vectorInfo,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<"specs" | "json">("specs");
  const [isClearing, setIsClearing] = useState(false);
  const [clearMessage, setClearMessage] = useState<string | null>(null);

  if (!selectedNodeId) return null;

  const handleClearVectorStore = async () => {
    if (!confirm("Are you sure you want to clear all vectors in ChromaDB? Active indexed chunks will be cleared until the next reindex.")) {
      return;
    }
    setIsClearing(true);
    try {
      const res = await api.clearVectorStore();
      setClearMessage(res.message);
      onRefresh?.();
      setTimeout(() => setClearMessage(null), 4000);
    } catch (err: any) {
      alert("Failed to clear vector store: " + err.message);
    } finally {
      setIsClearing(false);
    }
  };

  const getNodeInfo = (nodeId: string) => {
    switch (nodeId) {
      case "documents":
        return {
          title: "Raw Document Storage",
          desc: "Persisted JSON metadata & normalized content in data/raw/",
          icon: FolderArchive,
        };
      case "ingestion":
        return {
          title: "Ingestion & Multimodal Parser",
          desc: "Extracts TXT, PDF page boundaries, and OCR image text",
          icon: FileSpreadsheet,
        };
      case "chunking":
        return {
          title: "Deterministic Chunking Service",
          desc: "Recursive separator chunking with deterministic IDs",
          icon: Scissors,
        };
      case "embedding":
        return {
          title: "Dense Embedding Generator",
          desc: "BAAI/bge-small-en-v1.5 384-dimensional vector encoder",
          icon: Cpu,
        };
      case "indexing":
        return {
          title: "Index State & Knowledge Boundary",
          desc: "Atomic selection state mapping active documents to ChromaDB",
          icon: ListFilter,
        };
      case "vector_store":
        return {
          title: "Persistent ChromaDB Store",
          desc: "Local HNSW cosine index stored in data/indexes/chroma/",
          icon: Database,
        };
      default:
        return {
          title: "Node Inspector",
          desc: "Pipeline configuration and state",
          icon: Database,
        };
    }
  };

  const nodeInfo = getNodeInfo(selectedNodeId);
  const Icon = nodeInfo.icon;

  return (
    <div className="w-96 border-l border-border-subtle bg-bg-card/95 backdrop-blur-md flex flex-col h-full overflow-hidden shadow-2xl z-20">
      {/* Header */}
      <div className="p-4 border-b border-border-subtle flex items-center justify-between gap-2 bg-bg-darkest/50">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-bg-elevated text-accent-blue border border-border-subtle">
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text-primary font-mono">
              {nodeInfo.title}
            </h3>
            <p className="text-[11px] text-text-muted mt-0.5">{nodeInfo.desc}</p>
          </div>
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
          onClick={() => setActiveTab("specs")}
          className={`py-2 px-3 border-b-2 font-medium transition-colors ${
            activeTab === "specs"
              ? "border-accent text-accent-blue font-semibold"
              : "border-transparent text-text-muted hover:text-text-secondary"
          }`}
        >
          Specifications
        </button>
        <button
          onClick={() => setActiveTab("json")}
          className={`py-2 px-3 border-b-2 font-medium transition-colors ${
            activeTab === "json"
              ? "border-accent text-accent-blue font-semibold"
              : "border-transparent text-text-muted hover:text-text-secondary"
          }`}
        >
          State JSON
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === "json" ? (
          <JsonViewer
            data={{
              nodeId: selectedNodeId,
              documents,
              indexState,
              embeddingInfo,
              vectorInfo,
            }}
            title={`State: ${selectedNodeId}`}
            maxHeight="max-h-[600px]"
          />
        ) : (
          <>
            {/* 1. DOCUMENTS */}
            {selectedNodeId === "documents" && (
              <div className="space-y-3 text-xs font-mono">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle">
                    <span className="text-[10px] text-text-muted block uppercase">
                      Total Ingested
                    </span>
                    <span className="text-xl font-bold text-text-primary">
                      {documents?.total_count || 0}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle">
                    <span className="text-[10px] text-text-muted block uppercase">
                      Active In Index
                    </span>
                    <span className="text-xl font-bold text-accent-green">
                      {documents?.active_count || 0}
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2 text-text-secondary">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Storage Path</span>
                    <span className="text-text-primary">backend/data/raw/</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">File Persistence</span>
                    <span className="text-text-primary">Normalized JSON</span>
                  </div>
                </div>
              </div>
            )}

            {/* 2. INGESTION */}
            {selectedNodeId === "ingestion" && (
              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2">
                  <span className="text-[10px] text-text-muted uppercase block">
                    Supported Formats
                  </span>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {["TXT", "PDF (pypdf)", "PNG (OCR)", "JPG (OCR)", "WEBP (OCR)"].map(
                      (fmt) => (
                        <Badge key={fmt} variant="blue" size="sm">
                          {fmt}
                        </Badge>
                      )
                    )}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2 text-text-secondary">
                  <div className="flex justify-between">
                    <span className="text-text-muted">OCR Engine</span>
                    <span className="text-text-primary font-bold">Tesseract (eng)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">PDF Page Extraction</span>
                    <span className="text-accent-green font-bold">Enabled</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Normalization</span>
                    <span className="text-text-primary">Linebreaks & Spacing</span>
                  </div>
                </div>
              </div>
            )}

            {/* 3. CHUNKING */}
            {selectedNodeId === "chunking" && (
              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2.5">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Chunk Size</span>
                    <span className="text-accent-blue font-bold">
                      {indexState?.chunking_config?.chunk_size || 512} chars
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Chunk Overlap</span>
                    <span className="text-accent-purple font-bold">
                      {indexState?.chunking_config?.chunk_overlap || 64} chars
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Hierarchy Separator</span>
                    <span className="text-text-primary">\n\n (Paragraphs)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Chunk ID Determinism</span>
                    <span className="text-accent-green font-bold">Enabled</span>
                  </div>
                </div>
              </div>
            )}

            {/* 4. EMBEDDING */}
            {selectedNodeId === "embedding" && (
              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2.5">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Dense Model</span>
                    <span className="text-text-primary font-bold">
                      {embeddingInfo?.model_name || "BAAI/bge-small-en-v1.5"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Vector Dimension</span>
                    <span className="text-accent-blue font-bold">
                      {embeddingInfo?.dimension || 384} Dimensions
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Compute Device</span>
                    <span className="text-text-primary">
                      {embeddingInfo?.device || "cpu"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">L2 Normalization</span>
                    <span className="text-accent-green font-bold">
                      {embeddingInfo?.normalize_embeddings ? "True" : "False"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* 5. INDEXING */}
            {selectedNodeId === "indexing" && (
              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Schema Version</span>
                    <Badge variant="purple">{indexState?.indexing_version || "v1"}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Active Document IDs</span>
                    <span className="text-accent-green font-bold">
                      {indexState?.active_document_ids?.length || 0} Docs
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Last Updated</span>
                    <span className="text-text-muted text-[10px]">
                      {indexState?.updated_at
                        ? new Date(indexState.updated_at).toLocaleTimeString()
                        : "N/A"}
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[11px] text-text-muted block">
                    Active Indexed Documents
                  </span>
                  <div className="p-2 rounded-lg bg-bg-darkest border border-border-subtle max-h-48 overflow-y-auto space-y-1">
                    {indexState?.active_document_ids && indexState.active_document_ids.length > 0 ? (
                      indexState.active_document_ids.map((id) => (
                        <div key={id} className="text-[11px] text-text-secondary truncate">
                          • {id}
                        </div>
                      ))
                    ) : (
                      <p className="text-[11px] text-text-muted text-center py-2">
                        No active documents indexed.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 6. VECTOR STORE */}
            {selectedNodeId === "vector_store" && (
              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle space-y-2.5">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Provider</span>
                    <span className="text-text-primary font-bold">
                      {vectorInfo?.provider || "chromadb"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Collection</span>
                    <span className="text-accent-blue font-bold">
                      {vectorInfo?.collection_name || "rag_documents"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Indexed Points</span>
                    <span className="text-accent-green font-bold">
                      {vectorInfo?.point_count || 0} Vectors
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Distance Metric</span>
                    <span className="text-text-primary">Cosine</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Persistence Path</span>
                    <span className="text-text-muted text-[10px] truncate max-w-[180px]">
                      {vectorInfo?.persistence_path || "data/indexes/chroma"}
                    </span>
                  </div>
                </div>

                {/* Clear collection button */}
                <button
                  onClick={handleClearVectorStore}
                  disabled={isClearing}
                  className="w-full py-2 px-3 rounded-lg border border-accent-red/30 bg-accent-red/10 hover:bg-accent-red/20 text-accent-red font-mono text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>{isClearing ? "Clearing..." : "Clear Vector Store"}</span>
                </button>

                {clearMessage && (
                  <p className="text-[11px] text-accent-green text-center font-mono">
                    {clearMessage}
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
