import React, { useState } from "react";
import {
  LayoutDashboard,
  Database,
  Cpu,
  Layers,
  Sparkles,
  Files,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Workflow,
  Search,
} from "lucide-react";
import {
  DocumentListResponse,
  EmbeddingInfoResponse,
  HealthResponse,
  IndexStateModel,
  VectorStoreInfoResponse,
} from "../../types/backend";
import { Badge } from "../../components/common/Badge";

interface DashboardViewProps {
  health: HealthResponse | null;
  documents: DocumentListResponse | null;
  indexState: IndexStateModel | null;
  embeddingInfo: EmbeddingInfoResponse | null;
  vectorInfo: VectorStoreInfoResponse | null;
  onNavigate: (tab: "playground" | "studio" | "documents") => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  health,
  documents,
  indexState,
  embeddingInfo,
  vectorInfo,
  onNavigate,
}) => {
  const [quickQuery, setQuickQuery] = useState("");

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6 bg-bg-darkest font-sans">
      {/* Welcome Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-bg-card via-bg-elevated to-bg-card border border-border-subtle shadow-xl flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-accent-purple/20 text-accent-purple text-[10px] font-mono font-bold uppercase tracking-wider border border-accent-purple/30">
              Visual RAG Infrastructure
            </span>
            <span className="text-text-muted text-xs font-mono">• Production Ready</span>
          </div>
          <h2 className="text-xl font-bold text-text-primary tracking-tight font-mono">
            OMNICORE RAG Studio
          </h2>
          <p className="text-xs text-text-secondary max-w-xl">
            Inspect live embeddings, candidate vector similarity, prompt context synthesis, and grounded claim validation in real-time.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate("playground")}
            className="px-4 py-2.5 rounded-xl bg-accent hover:bg-accent-blue text-white text-xs font-mono font-semibold flex items-center gap-2 transition-all shadow-lg shadow-accent/20"
          >
            <Sparkles className="w-4 h-4" />
            <span>Launch Q/A Playground</span>
          </button>

          <button
            onClick={() => onNavigate("studio")}
            className="px-4 py-2.5 rounded-xl bg-bg-card hover:bg-bg-elevated border border-border-subtle text-text-primary text-xs font-mono transition-all flex items-center gap-2"
          >
            <Workflow className="w-4 h-4 text-accent-purple" />
            <span>Injection Studio</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-4 gap-4">
        {/* Total Documents */}
        <div
          onClick={() => onNavigate("documents")}
          className="p-4 rounded-xl bg-bg-card border border-border-subtle hover:border-text-secondary/50 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-text-muted mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">Raw Ingestion</span>
            <Files className="w-4 h-4 text-accent-blue group-hover:scale-110 transition-transform" />
          </div>
          <p className="text-2xl font-bold text-text-primary font-mono">
            {documents?.total_count || 0}
          </p>
          <p className="text-[10px] text-text-muted font-mono mt-1">
            Total files stored in data/raw/
          </p>
        </div>

        {/* Active Index Documents */}
        <div
          onClick={() => onNavigate("studio")}
          className="p-4 rounded-xl bg-bg-card border border-border-subtle hover:border-text-secondary/50 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-text-muted mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">Active Index</span>
            <Layers className="w-4 h-4 text-accent-green group-hover:scale-110 transition-transform" />
          </div>
          <p className="text-2xl font-bold text-accent-green font-mono">
            {documents?.active_count || 0}
          </p>
          <p className="text-[10px] text-text-muted font-mono mt-1">
            Documents indexed in ChromaDB
          </p>
        </div>

        {/* ChromaDB Vectors */}
        <div
          onClick={() => onNavigate("studio")}
          className="p-4 rounded-xl bg-bg-card border border-border-subtle hover:border-text-secondary/50 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-text-muted mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">Vector Store</span>
            <Database className="w-4 h-4 text-accent-purple group-hover:scale-110 transition-transform" />
          </div>
          <p className="text-2xl font-bold text-text-primary font-mono">
            {vectorInfo?.point_count || 0}
          </p>
          <p className="text-[10px] text-text-muted font-mono mt-1">
            384d points in {vectorInfo?.collection_name || "rag_documents"}
          </p>
        </div>

        {/* Embedding Dimension */}
        <div className="p-4 rounded-xl bg-bg-card border border-border-subtle">
          <div className="flex items-center justify-between text-text-muted mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">Embedding Engine</span>
            <Cpu className="w-4 h-4 text-accent-amber" />
          </div>
          <p className="text-2xl font-bold text-text-primary font-mono">
            {embeddingInfo?.dimension || 384}d
          </p>
          <p className="text-[10px] text-text-muted font-mono mt-1 truncate">
            {embeddingInfo?.model_name || "BAAI/bge-small-en-v1.5"}
          </p>
        </div>
      </div>

      {/* Pipeline Architecture Highlights */}
      <div className="grid grid-cols-2 gap-4">
        {/* Strict Grounding Card */}
        <div className="p-5 rounded-xl bg-bg-card border border-border-subtle space-y-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-accent-green" />
            <h3 className="text-sm font-bold text-text-primary font-mono">
              Strict Grounding & Guardrails
            </h3>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            The pipeline guarantees evidence grounding: if candidate chunks score below quality threshold or if evidence is insufficient, the LLM safely abstains without fabricating facts or using pretrained assumptions.
          </p>
          <div className="flex items-center gap-2 pt-2 border-t border-border-subtle/50 text-[11px] font-mono text-text-muted">
            <span className="text-accent-green">✓ Chunk ID Verification</span>
            <span>•</span>
            <span className="text-accent-blue">✓ Threshold 0.50</span>
            <span>•</span>
            <span className="text-accent-purple">✓ Full Lifecycle Traces</span>
          </div>
        </div>

        {/* Multimodal Ingestion Card */}
        <div className="p-5 rounded-xl bg-bg-card border border-border-subtle space-y-3">
          <div className="flex items-center gap-2">
            <Workflow className="w-5 h-5 text-accent-blue" />
            <h3 className="text-sm font-bold text-text-primary font-mono">
              Multimodal Ingestion Pipeline
            </h3>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            Supports UTF-8 text files, PDF document page extraction, and image OCR text recognition using Tesseract OCR, with deterministic chunking and atomic ChromaDB reindexing.
          </p>
          <div className="flex items-center gap-2 pt-2 border-t border-border-subtle/50 text-[11px] font-mono text-text-muted">
            <span>TXT / PDF / PNG / JPG / WEBP</span>
            <span>•</span>
            <span className="text-text-secondary">512 char chunks (64 overlap)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
