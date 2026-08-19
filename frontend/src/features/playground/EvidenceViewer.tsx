import React, { useState } from "react";
import {
  FileText,
  ChevronDown,
  ChevronUp,
  FileCode,
  Image as ImageIcon,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { RetrievalChunk } from "../../types/backend";
import { Badge } from "../../components/common/Badge";

interface EvidenceViewerProps {
  chunks: RetrievalChunk[];
  threshold?: number;
  highlightChunkId?: string | null;
  onSelectChunk?: (chunkId: string) => void;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  chunks,
  threshold = 0.5,
  highlightChunkId,
  onSelectChunk,
}) => {
  const [expandedChunkIds, setExpandedChunkIds] = useState<Set<string>>(
    new Set(chunks.slice(0, 2).map((c) => c.chunk_id))
  );

  const toggleExpand = (chunkId: string) => {
    const next = new Set(expandedChunkIds);
    if (next.has(chunkId)) {
      next.delete(chunkId);
    } else {
      next.add(chunkId);
    }
    setExpandedChunkIds(next);
  };

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case "pdf":
        return <FileText className="w-3.5 h-3.5 text-accent-red" />;
      case "image":
        return <ImageIcon className="w-3.5 h-3.5 text-accent-purple" />;
      default:
        return <FileCode className="w-3.5 h-3.5 text-accent-blue" />;
    }
  };

  if (chunks.length === 0) {
    return (
      <div className="p-6 rounded-xl border border-dashed border-border-subtle bg-bg-card/50 text-center text-xs text-text-muted font-mono">
        No candidate evidence chunks available for this execution.
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {chunks.map((chunk, idx) => {
        const isExpanded = expandedChunkIds.has(chunk.chunk_id);
        const isHighlighted = highlightChunkId === chunk.chunk_id;
        const scorePercent = Math.round(chunk.similarity_score * 100);
        const passesThreshold = chunk.similarity_score >= threshold;

        return (
          <div
            key={chunk.chunk_id}
            id={`chunk-${chunk.chunk_id}`}
            onClick={() => onSelectChunk?.(chunk.chunk_id)}
            className={`
              rounded-xl border transition-all overflow-hidden cursor-pointer
              ${
                isHighlighted
                  ? "border-accent-blue bg-accent-blue/5 shadow-[0_0_15px_rgba(56,139,253,0.25)] ring-1 ring-accent-blue"
                  : "border-border-subtle bg-bg-card/90 hover:border-text-secondary/40"
              }
            `}
          >
            {/* Chunk Header */}
            <div className="p-3 flex items-center justify-between gap-3 bg-bg-darkest/30">
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="flex items-center justify-center w-5 h-5 rounded bg-bg-elevated text-text-primary text-[10px] font-mono font-bold">
                  #{idx + 1}
                </span>
                <div className="flex items-center gap-1.5 min-w-0">
                  {getSourceIcon(chunk.source_type)}
                  <span className="text-xs font-semibold text-text-primary truncate font-mono">
                    {chunk.title || "Untitled Document"}
                  </span>
                </div>
                <Badge
                  variant={passesThreshold ? "success" : "warning"}
                  size="sm"
                >
                  {chunk.source_type.toUpperCase()}
                </Badge>
              </div>

              {/* Similarity Score */}
              <div className="flex items-center gap-3 shrink-0">
                <div className="text-right">
                  <div className="flex items-center gap-1 font-mono text-xs font-semibold text-text-primary">
                    <Sparkles className="w-3 h-3 text-accent-blue" />
                    <span>{chunk.similarity_score.toFixed(4)}</span>
                  </div>
                  <div className="w-20 h-1.5 rounded-full bg-bg-elevated mt-1 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        chunk.similarity_score >= 0.8
                          ? "bg-accent-green"
                          : chunk.similarity_score >= 0.6
                          ? "bg-accent-blue"
                          : "bg-accent-amber"
                      }`}
                      style={{ width: `${scorePercent}%` }}
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleExpand(chunk.chunk_id);
                  }}
                  className="p-1 rounded hover:bg-bg-elevated text-text-muted hover:text-text-primary transition-colors"
                >
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Chunk Body Content */}
            <div className="p-3 text-xs">
              <p
                className={`text-text-secondary leading-relaxed font-sans select-text ${
                  isExpanded ? "" : "line-clamp-2"
                }`}
              >
                {chunk.content}
              </p>

              {/* Metadata tags */}
              {isExpanded && (
                <div className="mt-3 pt-2.5 border-t border-border-subtle/50 flex flex-wrap items-center gap-2 text-[10px] font-mono text-text-muted">
                  <span className="text-text-secondary">
                    Chunk ID: <span className="text-text-primary">{chunk.chunk_id}</span>
                  </span>
                  <span>•</span>
                  <span>
                    Doc ID: <span className="text-text-primary">{chunk.document_id}</span>
                  </span>
                  {chunk.metadata && chunk.metadata.page_number && (
                    <>
                      <span>•</span>
                      <span className="text-accent-purple font-semibold">
                        Page {chunk.metadata.page_number}
                      </span>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
