import React from "react";
import { RefreshCw, Database, Sparkles, Activity } from "lucide-react";
import { IndexStateModel, VectorStoreInfoResponse } from "../../types/backend";

interface TopbarProps {
  title: string;
  subtitle?: string;
  indexState?: IndexStateModel | null;
  vectorInfo?: VectorStoreInfoResponse | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const Topbar: React.FC<TopbarProps> = ({
  title,
  subtitle,
  indexState,
  vectorInfo,
  onRefresh,
  isRefreshing = false,
}) => {
  return (
    <header className="h-14 border-b border-border-subtle bg-bg-dark/80 backdrop-blur-md px-6 flex items-center justify-between shrink-0 select-none z-10">
      {/* Title section */}
      <div>
        <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          {title}
        </h2>
        {subtitle && (
          <p className="text-[11px] text-text-muted font-mono">{subtitle}</p>
        )}
      </div>

      {/* Right status badges & actions */}
      <div className="flex items-center gap-3">
        {/* Active Index pill */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-bg-card border border-border-subtle text-xs font-mono">
          <Database className="w-3.5 h-3.5 text-accent-purple" />
          <span className="text-text-muted">Index:</span>
          <span className="text-text-primary font-semibold">
            {indexState?.indexing_version || "v1"}
          </span>
          <span className="text-border-subtle">|</span>
          <span className="text-accent-green font-medium">
            {indexState?.active_document_ids?.length || 0} Docs Active
          </span>
        </div>

        {/* Vector store points */}
        {vectorInfo && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-bg-card border border-border-subtle text-xs font-mono text-text-secondary">
            <span className="text-text-muted">Vectors:</span>
            <span className="text-accent-blue font-medium">
              {vectorInfo.point_count} pts
            </span>
          </div>
        )}

        {/* Refresh button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1.5 rounded-lg border border-border-subtle bg-bg-card hover:bg-bg-elevated text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
            title="Refresh System Data"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-accent-blue" : ""}`}
            />
          </button>
        )}
      </div>
    </header>
  );
};
