import React, { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import {
  MessageSquare,
  Cpu,
  Search,
  Layers,
  BrainCircuit,
  ShieldCheck,
  CheckCircle2,
  FolderArchive,
  FileSpreadsheet,
  Scissors,
  ListFilter,
  Database,
  Activity,
  AlertTriangle,
  XCircle,
  Loader2,
  Clock,
} from "lucide-react";
import { WorkflowNodeData, NodeExecutionStatus } from "../../types/workflow";

const ICON_MAP: Record<string, React.ElementType> = {
  MessageSquare,
  Cpu,
  Search,
  Layers,
  BrainCircuit,
  ShieldCheck,
  CheckCircle2,
  FolderArchive,
  FileSpreadsheet,
  Scissors,
  ListFilter,
  Database,
  Activity,
};

const STATUS_CONFIG: Record<
  NodeExecutionStatus,
  {
    border: string;
    bg: string;
    text: string;
    glow: string;
    icon: React.ElementType | null;
  }
> = {
  idle: {
    border: "border-border-subtle hover:border-text-secondary/50",
    bg: "bg-bg-card/90",
    text: "text-text-secondary",
    glow: "",
    icon: null,
  },
  running: {
    border: "border-accent-blue animate-pulse",
    bg: "bg-bg-card",
    text: "text-accent-blue",
    glow: "shadow-[0_0_15px_rgba(88,166,255,0.3)]",
    icon: Loader2,
  },
  completed: {
    border: "border-accent-green/60",
    bg: "bg-bg-card/95",
    text: "text-accent-green",
    glow: "shadow-[0_0_12px_rgba(63,185,80,0.15)]",
    icon: CheckCircle2,
  },
  warning: {
    border: "border-accent-amber/60",
    bg: "bg-bg-card/95",
    text: "text-accent-amber",
    glow: "shadow-[0_0_12px_rgba(210,153,34,0.2)]",
    icon: AlertTriangle,
  },
  failed: {
    border: "border-accent-red/70",
    bg: "bg-bg-card/95",
    text: "text-accent-red",
    glow: "shadow-[0_0_15px_rgba(248,81,73,0.3)]",
    icon: XCircle,
  },
  skipped: {
    border: "border-border-muted border-dashed opacity-60",
    bg: "bg-bg-darkest/60",
    text: "text-text-muted",
    glow: "",
    icon: null,
  },
};

interface CustomWorkflowNodeProps {
  data: WorkflowNodeData;
}

export const CustomWorkflowNode = memo(({ data }: CustomWorkflowNodeProps) => {
  const IconComponent = ICON_MAP[data.iconName] || Activity;
  const statusCfg = STATUS_CONFIG[data.status] || STATUS_CONFIG.idle;
  const StatusIcon = statusCfg.icon;

  const isSelected = data.isSelected;

  return (
    <div
      className={`
        relative w-[240px] rounded-xl border backdrop-blur-md transition-all duration-200 cursor-pointer
        ${statusCfg.bg} ${statusCfg.border} ${statusCfg.glow}
        ${isSelected ? "ring-2 ring-accent shadow-[0_0_20px_rgba(56,139,253,0.4)]" : "hover:-translate-y-0.5"}
      `}
    >
      {/* Target (Left) Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-accent !border-2 !border-bg-darkest"
      />

      {/* Header */}
      <div className="p-3.5 pb-2.5">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2">
            <div
              className={`p-1.5 rounded-lg border border-border-subtle/50 ${
                data.status === "completed"
                  ? "bg-accent-green/10 text-accent-green"
                  : data.status === "running"
                  ? "bg-accent-blue/10 text-accent-blue animate-spin"
                  : data.status === "warning"
                  ? "bg-accent-amber/10 text-accent-amber"
                  : data.status === "failed"
                  ? "bg-accent-red/10 text-accent-red"
                  : "bg-bg-elevated text-text-secondary"
              }`}
            >
              <IconComponent className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-text-primary tracking-tight line-clamp-1">
                {data.label}
              </h4>
              {data.subtitle && (
                <p className="text-[10px] text-text-secondary font-mono">
                  {data.subtitle}
                </p>
              )}
            </div>
          </div>

          {/* Status Indicator */}
          {StatusIcon && (
            <div className={statusCfg.text}>
              <StatusIcon
                className={`w-3.5 h-3.5 ${
                  data.status === "running" ? "animate-spin" : ""
                }`}
              />
            </div>
          )}
        </div>

        {/* Badge & Timing row */}
        <div className="flex items-center justify-between text-[10px] pt-1.5 border-t border-border-subtle/40">
          <span className="px-1.5 py-0.5 rounded bg-bg-elevated text-text-secondary font-medium font-mono text-[9px]">
            {data.badge || (data.status === "skipped" ? "Skipped" : data.status.toUpperCase())}
          </span>
          {data.durationMs !== undefined && data.status !== "skipped" && (
            <span className="flex items-center gap-1 text-text-secondary font-mono">
              <Clock className="w-2.5 h-2.5 text-text-muted" />
              {data.durationMs > 0 ? `${data.durationMs}ms` : "<1ms"}
            </span>
          )}
        </div>
      </div>

      {/* Stats Snapshot */}
      {data.stats && Object.keys(data.stats).length > 0 && (
        <div className="px-3.5 py-2 bg-bg-darkest/40 rounded-b-xl border-t border-border-subtle/30 grid grid-cols-2 gap-2 text-[10px]">
          {Object.entries(data.stats).map(([k, v]) => (
            <div key={k} className="overflow-hidden">
              <span className="text-text-muted block text-[9px] uppercase tracking-wider">{k}</span>
              <span className="text-text-primary font-mono font-medium truncate block">{String(v)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Source (Right) Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-accent !border-2 !border-bg-darkest"
      />
    </div>
  );
});
