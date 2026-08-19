import React, { useState } from "react";
import {
  Files,
  Plus,
  RotateCw,
  Search,
  FileText,
  FileCode,
  Image as ImageIcon,
  CheckCircle2,
  XCircle,
  Calendar,
  Layers,
} from "lucide-react";
import { DocumentListResponse, DocumentSummary } from "../../types/backend";
import { Badge } from "../../components/common/Badge";
import { UploadModal } from "../studio/UploadModal";
import { api } from "../../api/endpoints";

interface DocumentsViewProps {
  documents: DocumentListResponse | null;
  onRefresh: () => void;
}

export const DocumentsView: React.FC<DocumentsViewProps> = ({
  documents,
  onRefresh,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<string>("all");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isReindexing, setIsReindexing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const docList = documents?.documents || [];

  const filteredDocs = docList.filter((doc) => {
    const matchesSearch =
      (doc.title || doc.document_id).toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType =
      filterType === "all" || doc.source_type.toLowerCase() === filterType.toLowerCase();
    return matchesSearch && matchesType;
  });

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const handleSelectAll = () => {
    if (selectedIds.size === filteredDocs.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredDocs.map((d) => d.document_id)));
    }
  };

  const handleReindexSelected = async () => {
    if (selectedIds.size === 0) return;
    setIsReindexing(true);
    setMessage(null);
    try {
      const res = await api.executeReindex(Array.from(selectedIds));
      setMessage(`Successfully reindexed ${res.selected_document_count} documents into ${res.chunk_count} chunks.`);
      onRefresh();
      setTimeout(() => setMessage(null), 5000);
    } catch (err: any) {
      alert("Reindex failed: " + err.message);
    } finally {
      setIsReindexing(false);
    }
  };

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case "pdf":
        return <FileText className="w-4 h-4 text-accent-red" />;
      case "image":
        return <ImageIcon className="w-4 h-4 text-accent-purple" />;
      default:
        return <FileCode className="w-4 h-4 text-accent-blue" />;
    }
  };

  return (
    <div className="h-full flex flex-col p-6 overflow-hidden bg-bg-darkest space-y-4">
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-text-primary font-mono flex items-center gap-2">
            <Files className="w-5 h-5 text-accent-blue" />
            <span>Document Repository</span>
          </h2>
          <p className="text-xs text-text-muted">
            Manage raw documents stored in data/raw/ and control active knowledge base indexing
          </p>
        </div>

        <div className="flex items-center gap-2">
          {selectedIds.size > 0 && (
            <button
              onClick={handleReindexSelected}
              disabled={isReindexing}
              className="px-3.5 py-2 rounded-xl bg-accent-green/20 hover:bg-accent-green/30 border border-accent-green/40 text-accent-green text-xs font-mono font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isReindexing ? "animate-spin" : ""}`} />
              <span>Reindex Selected ({selectedIds.size})</span>
            </button>
          )}

          <button
            onClick={() => setIsUploadOpen(true)}
            className="px-4 py-2 rounded-xl bg-accent hover:bg-accent-blue text-white text-xs font-mono font-medium flex items-center gap-2 shadow-lg shadow-accent/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Ingest Document</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between gap-3 bg-bg-card p-3 rounded-xl border border-border-subtle text-xs">
        <div className="flex items-center gap-2 flex-1 max-w-md bg-bg-darkest px-3 py-1.5 rounded-lg border border-border-subtle">
          <Search className="w-3.5 h-3.5 text-text-muted" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search documents by title or ID..."
            className="w-full bg-transparent text-text-primary placeholder:text-text-muted outline-none font-mono text-xs"
          />
        </div>

        <div className="flex items-center gap-2 font-mono">
          <span className="text-text-muted text-[11px]">Filter:</span>
          {["all", "txt", "pdf", "image"].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium uppercase transition-colors ${
                filterType === type
                  ? "bg-accent text-white"
                  : "bg-bg-elevated text-text-secondary hover:text-text-primary"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {message && (
        <div className="p-3 rounded-lg bg-accent-green/10 border border-accent-green/30 text-accent-green text-xs font-mono flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {/* Document Table */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-border-subtle bg-bg-card shadow-sm">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="sticky top-0 bg-bg-darkest/95 border-b border-border-subtle font-mono text-text-muted text-[11px] uppercase tracking-wider backdrop-blur-sm z-10">
            <tr>
              <th className="p-3.5 w-10 text-center">
                <input
                  type="checkbox"
                  checked={selectedIds.size === filteredDocs.length && filteredDocs.length > 0}
                  onChange={handleSelectAll}
                  className="rounded bg-bg-elevated border-border-subtle text-accent focus:ring-0 cursor-pointer"
                />
              </th>
              <th className="p-3.5">Document Title / ID</th>
              <th className="p-3.5">Format</th>
              <th className="p-3.5">Size</th>
              <th className="p-3.5">Active In Index</th>
              <th className="p-3.5">Ingestion Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle/50 font-sans">
            {filteredDocs.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-text-muted font-mono text-xs">
                  No documents match your query. Click "Ingest Document" to add files.
                </td>
              </tr>
            ) : (
              filteredDocs.map((doc) => {
                const isSelected = selectedIds.has(doc.document_id);
                return (
                  <tr
                    key={doc.document_id}
                    onClick={() => toggleSelect(doc.document_id)}
                    className={`hover:bg-bg-darkest/50 transition-colors cursor-pointer ${
                      isSelected ? "bg-accent/5" : ""
                    }`}
                  >
                    <td className="p-3.5 text-center" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(doc.document_id)}
                        className="rounded bg-bg-elevated border-border-subtle text-accent focus:ring-0 cursor-pointer"
                      />
                    </td>
                    <td className="p-3.5">
                      <div className="flex items-center gap-2.5">
                        {getSourceIcon(doc.source_type)}
                        <div>
                          <p className="font-semibold text-text-primary font-mono text-xs">
                            {doc.title || "Untitled"}
                          </p>
                          <p className="text-[10px] text-text-muted font-mono">
                            {doc.document_id}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="p-3.5">
                      <Badge variant="blue" size="sm">
                        {doc.source_type.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="p-3.5 font-mono text-text-secondary text-xs">
                      {doc.character_count} chars
                      {doc.page_count ? ` (${doc.page_count} pgs)` : ""}
                    </td>
                    <td className="p-3.5">
                      {doc.is_active ? (
                        <span className="inline-flex items-center gap-1.5 text-accent-green font-mono text-xs">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Active Index</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-text-muted font-mono text-xs">
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Unindexed</span>
                        </span>
                      )}
                    </td>
                    <td className="p-3.5 font-mono text-[11px] text-text-muted">
                      {new Date(doc.created_at).toLocaleString()}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={() => onRefresh()}
      />
    </div>
  );
};
