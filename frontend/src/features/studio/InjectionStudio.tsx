import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  NodeMouseHandler,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Plus,
  RotateCw,
  Eye,
  CheckSquare,
  Square,
  Layers,
  Sparkles,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { api } from "../../api/endpoints";
import {
  DocumentListResponse,
  DocumentSummary,
  EmbeddingInfoResponse,
  IndexStateModel,
  ReindexPreviewResponse,
  ReindexResponse,
  VectorStoreInfoResponse,
} from "../../types/backend";
import { CustomWorkflowNode } from "../../components/nodes/CustomWorkflowNode";
import { buildStudioGraph, StudioState } from "../../lib/studioAdapter";
import { StudioInspector } from "./StudioInspector";
import { UploadModal } from "./UploadModal";
import { Badge } from "../../components/common/Badge";

interface InjectionStudioProps {
  documents: DocumentListResponse | null;
  indexState: IndexStateModel | null;
  embeddingInfo: EmbeddingInfoResponse | null;
  vectorInfo: VectorStoreInfoResponse | null;
  onRefreshAll: () => void;
}

export const InjectionStudio: React.FC<InjectionStudioProps> = ({
  documents,
  indexState,
  embeddingInfo,
  vectorInfo,
  onRefreshAll,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("chunking");
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Reindexing selection state
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [isReindexing, setIsReindexing] = useState(false);
  const [reindexResult, setReindexResult] = useState<ReindexResponse | null>(null);
  const [previewResult, setPreviewResult] = useState<ReindexPreviewResponse | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync active documents to selection on first load
  useEffect(() => {
    if (documents?.documents) {
      const activeIds = documents.documents
        .filter((d) => d.is_active)
        .map((d) => d.document_id);
      setSelectedDocIds(new Set(activeIds));
    }
  }, [documents]);

  const nodeTypes = useMemo(
    () => ({
      customNode: CustomWorkflowNode,
    }),
    []
  );

  const studioState: StudioState = useMemo(
    () => ({
      documents,
      indexState,
      embeddingInfo,
      vectorInfo,
      reindexExecution: reindexResult,
      isReindexing,
    }),
    [documents, indexState, embeddingInfo, vectorInfo, reindexResult, isReindexing]
  );

  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildStudioGraph(studioState, selectedNodeId),
    []
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Synchronize graph when state or selection updates
  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = buildStudioGraph(
      studioState,
      selectedNodeId
    );
    setNodes(newNodes);
    setEdges(newEdges);
  }, [studioState, selectedNodeId, setNodes, setEdges]);

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      setSelectedNodeId(node.id);
    },
    []
  );

  const toggleSelectAll = () => {
    if (!documents?.documents) return;
    if (selectedDocIds.size === documents.documents.length) {
      setSelectedDocIds(new Set());
    } else {
      setSelectedDocIds(new Set(documents.documents.map((d) => d.document_id)));
    }
  };

  const toggleDocSelect = (docId: string) => {
    const next = new Set(selectedDocIds);
    if (next.has(docId)) {
      next.delete(docId);
    } else {
      next.add(docId);
    }
    setSelectedDocIds(next);
  };

  const handlePreviewReindex = async () => {
    if (selectedDocIds.size === 0) {
      setError("Please select at least one document to preview.");
      return;
    }
    setError(null);
    try {
      const preview = await api.previewReindex(Array.from(selectedDocIds));
      setPreviewResult(preview);
      setIsPreviewOpen(true);
    } catch (err: any) {
      setError(err.message || "Failed to preview chunking.");
    }
  };

  const handleExecuteReindex = async () => {
    if (selectedDocIds.size === 0) {
      setError("Please select at least one document to reindex.");
      return;
    }
    setIsReindexing(true);
    setError(null);
    try {
      const res = await api.executeReindex(Array.from(selectedDocIds));
      setReindexResult(res);
      onRefreshAll();
      setIsPreviewOpen(false);
    } catch (err: any) {
      setError(err.message || "Reindexing failed.");
    } finally {
      setIsReindexing(false);
    }
  };

  return (
    <div className="flex h-full w-full relative overflow-hidden bg-bg-darkest">
      {/* Center Canvas Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 relative">
        {/* Top Control Bar */}
        <div className="p-4 border-b border-border-subtle bg-bg-dark/90 backdrop-blur-md z-10 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsUploadOpen(true)}
                className="px-3.5 py-2 rounded-xl bg-accent hover:bg-accent-blue text-white font-medium text-xs font-mono transition-all flex items-center gap-2 shadow-lg shadow-accent/20"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Ingest Document</span>
              </button>

              <button
                onClick={handlePreviewReindex}
                disabled={selectedDocIds.size === 0}
                className="px-3.5 py-2 rounded-xl bg-bg-card border border-border-subtle hover:border-text-secondary/50 text-text-secondary hover:text-text-primary text-xs font-mono transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                <Eye className="w-3.5 h-3.5 text-accent-purple" />
                <span>Preview Chunks</span>
              </button>
            </div>

            {/* Reindex Action Button */}
            <button
              onClick={handleExecuteReindex}
              disabled={isReindexing || selectedDocIds.size === 0}
              className="px-4 py-2 rounded-xl bg-accent-green/20 hover:bg-accent-green/30 border border-accent-green/40 text-accent-green font-medium text-xs font-mono transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-accent-green/10"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isReindexing ? "animate-spin" : ""}`} />
              <span>
                {isReindexing
                  ? "Indexing Selected..."
                  : `Reindex Selected (${selectedDocIds.size})`}
              </span>
            </button>
          </div>

          {/* Document selection quick drawer/pills */}
          {documents?.documents && documents.documents.length > 0 && (
            <div className="flex items-center justify-between text-xs font-mono border-t border-border-subtle/50 pt-2">
              <div className="flex items-center gap-2 overflow-x-auto py-1 max-w-2xl">
                <button
                  onClick={toggleSelectAll}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-bg-card border border-border-subtle text-[11px] text-text-secondary hover:text-text-primary shrink-0"
                >
                  {selectedDocIds.size === documents.documents.length ? (
                    <CheckSquare className="w-3 h-3 text-accent-blue" />
                  ) : (
                    <Square className="w-3 h-3" />
                  )}
                  <span>Select All</span>
                </button>

                {documents.documents.map((doc) => {
                  const isSelected = selectedDocIds.has(doc.document_id);
                  return (
                    <button
                      key={doc.document_id}
                      onClick={() => toggleDocSelect(doc.document_id)}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-mono transition-all shrink-0 ${
                        isSelected
                          ? "bg-accent/15 border-accent/40 text-accent-blue font-semibold"
                          : "bg-bg-darkest border-border-subtle text-text-muted hover:border-text-secondary/40"
                      }`}
                    >
                      <span>{doc.title || doc.document_id.slice(0, 10)}</span>
                      <span className="text-[9px] px-1 rounded bg-bg-elevated uppercase">
                        {doc.source_type}
                      </span>
                    </button>
                  );
                })}
              </div>

              <span className="text-[11px] text-text-muted shrink-0 pl-2">
                {selectedDocIds.size}/{documents.total_count} documents selected
              </span>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-2.5 rounded-lg bg-accent-red/10 border border-accent-red/30 text-accent-red font-mono text-[11px] flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Reindex completion success banner */}
          {reindexResult && (
            <div className="p-2.5 rounded-lg bg-accent-green/10 border border-accent-green/30 text-accent-green font-mono text-[11px] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                <span>
                  Reindex Complete: {reindexResult.selected_document_count} documents indexed into {reindexResult.chunk_count} chunks ({reindexResult.embedding_count} embeddings generated).
                </span>
              </div>
              <button
                onClick={() => setReindexResult(null)}
                className="hover:underline text-[10px]"
              >
                Dismiss
              </button>
            </div>
          )}
        </div>

        {/* Workflow React Flow Canvas */}
        <div className="flex-1 relative w-full h-full bg-bg-darkest">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.3}
            maxZoom={1.8}
            defaultViewport={{ x: 50, y: 100, zoom: 0.85 }}
            proOptions={{ hideAttribution: true }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color="#21262d"
            />
            <Controls position="bottom-left" showInteractive={false} />
          </ReactFlow>

          {/* Canvas info overlay */}
          <div className="absolute top-4 left-4 pointer-events-none text-[11px] font-mono text-text-muted bg-bg-dark/80 px-2.5 py-1 rounded-md border border-border-subtle/50 backdrop-blur-sm">
            ⚙️ Click on any injection node to inspect chunking, embeddings, and vector storage
          </div>
        </div>
      </div>

      {/* Right Side Inspector */}
      {selectedNodeId && (
        <StudioInspector
          selectedNodeId={selectedNodeId}
          onClose={() => setSelectedNodeId(null)}
          documents={documents}
          indexState={indexState}
          embeddingInfo={embeddingInfo}
          vectorInfo={vectorInfo}
          onRefresh={onRefreshAll}
        />
      )}

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={() => {
          onRefreshAll();
        }}
      />

      {/* Preview Chunks Modal */}
      {isPreviewOpen && previewResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-bg-card border border-border-subtle shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-border-subtle flex items-center justify-between bg-bg-darkest/40">
              <h3 className="text-sm font-bold text-text-primary font-mono flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent-purple" />
                <span>Chunking Preview ({previewResult.total_chunk_count} Chunks)</span>
              </h3>
              <button
                onClick={() => setIsPreviewOpen(false)}
                className="p-1 rounded-lg hover:bg-bg-elevated text-text-muted hover:text-text-primary"
              >
                ✕
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 text-xs font-mono">
              {/* Statistics Grid */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle">
                  <span className="text-[10px] text-text-muted block uppercase">
                    Average Size
                  </span>
                  <span className="text-base font-bold text-text-primary">
                    {previewResult.chunk_statistics.avg_chunk_size.toFixed(1)} chars
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle">
                  <span className="text-[10px] text-text-muted block uppercase">
                    Min / Max Size
                  </span>
                  <span className="text-base font-bold text-accent-blue">
                    {previewResult.chunk_statistics.min_chunk_size} / {previewResult.chunk_statistics.max_chunk_size}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-bg-darkest border border-border-subtle">
                  <span className="text-[10px] text-text-muted block uppercase">
                    Selected Docs
                  </span>
                  <span className="text-base font-bold text-accent-green">
                    {previewResult.selected_document_count}
                  </span>
                </div>
              </div>

              {/* Sample Chunks */}
              <div className="space-y-2">
                <span className="text-text-muted text-[11px] block">Sample Chunks</span>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {previewResult.sample_chunks.map((sc) => (
                    <div
                      key={sc.chunk_id}
                      className="p-3 rounded-lg bg-bg-darkest border border-border-subtle text-xs"
                    >
                      <div className="flex justify-between items-center text-[10px] text-accent-blue font-bold mb-1">
                        <span>{sc.chunk_id}</span>
                        <Badge size="sm">{sc.character_count} chars</Badge>
                      </div>
                      <p className="text-text-secondary font-sans leading-relaxed">
                        {sc.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-border-subtle flex justify-end gap-2 bg-bg-darkest/30">
              <button
                onClick={() => setIsPreviewOpen(false)}
                className="px-3 py-1.5 rounded-lg bg-bg-elevated text-text-secondary hover:text-text-primary text-xs font-mono"
              >
                Close
              </button>
              <button
                onClick={handleExecuteReindex}
                className="px-4 py-1.5 rounded-lg bg-accent-green/20 hover:bg-accent-green/30 border border-accent-green/40 text-accent-green text-xs font-mono font-bold"
              >
                Confirm & Reindex
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
