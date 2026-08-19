import React from "react";
import { Activity, ShieldCheck, Database, CheckCircle2, XCircle } from "lucide-react";
import { HealthResponse, VectorStoreInfoResponse, IndexStateModel } from "../../types/backend";

interface StatusFooterProps {
  health?: HealthResponse | null;
  vectorInfo?: VectorStoreInfoResponse | null;
  indexState?: IndexStateModel | null;
  lastLatencyMs?: number | null;
}

export const StatusFooter: React.FC<StatusFooterProps> = ({
  health,
  vectorInfo,
  indexState,
  lastLatencyMs,
}) => {
  const isHealthy = health?.status === "ok";

  return (
    <footer className="h-7 bg-bg-darkest border-t border-border-subtle/80 px-4 flex items-center justify-between text-[11px] font-mono text-text-muted select-none shrink-0 z-10">
      {/* Left status items */}
      <div className="flex items-center gap-4">
        {/* Backend API status */}
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              isHealthy ? "bg-accent-green shadow-[0_0_6px_#3fb950]" : "bg-accent-red"
            }`}
          />
          <span className="text-text-secondary">
            API: {isHealthy ? "Online" : "Connecting..."}
          </span>
        </div>

        {/* Vector DB status */}
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              vectorInfo?.collection_exists ? "bg-accent-blue shadow-[0_0_6px_#58a6ff]" : "bg-accent-amber"
            }`}
          />
          <span className="text-text-secondary">
            ChromaDB: {vectorInfo?.collection_exists ? "Active" : "Uninitialized"}
          </span>
        </div>

        {/* Active Index */}
        <div className="flex items-center gap-1">
          <Database className="w-3 h-3 text-text-muted" />
          <span>Version: {indexState?.indexing_version || "v1"}</span>
        </div>
      </div>

      {/* Right latency & security note */}
      <div className="flex items-center gap-4">
        {lastLatencyMs !== undefined && lastLatencyMs !== null && (
          <div className="flex items-center gap-1">
            <Activity className="w-3 h-3 text-accent-blue" />
            <span className="text-text-secondary">{lastLatencyMs}ms</span>
          </div>
        )}

        <div className="flex items-center gap-1 text-text-muted">
          <ShieldCheck className="w-3 h-3 text-accent-green" />
          <span>Strict Evidence Guardrails Active</span>
        </div>
      </div>
    </footer>
  );
};
