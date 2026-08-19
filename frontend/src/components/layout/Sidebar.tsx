import React from "react";
import {
  LayoutDashboard,
  Workflow,
  Sparkles,
  Files,
  Settings,
  Layers,
} from "lucide-react";

export type NavTab = "dashboard" | "studio" | "playground" | "documents" | "settings";

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const navItems = [
    {
      id: "playground" as NavTab,
      label: "Q/A Playground",
      icon: Sparkles,
      tag: "Hero",
      description: "Visual query execution & evidence",
    },
    {
      id: "studio" as NavTab,
      label: "Injection Studio",
      icon: Workflow,
      description: "Pipeline indexing & chunking",
    },
    {
      id: "documents" as NavTab,
      label: "Documents",
      icon: Files,
      description: "Raw ingested documents",
    },
    {
      id: "dashboard" as NavTab,
      label: "Dashboard",
      icon: LayoutDashboard,
      description: "System stats & overview",
    },
    {
      id: "settings" as NavTab,
      label: "Settings",
      icon: Settings,
      description: "Vector DB & model config",
    },
  ];

  return (
    <aside className="w-64 bg-bg-dark border-r border-border-subtle flex flex-col justify-between select-none shrink-0 h-screen">
      {/* Brand Header */}
      <div>
        <div className="p-4 border-b border-border-subtle/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue via-accent-purple to-accent flex items-center justify-center shadow-lg shadow-accent/20">
              <Layers className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-text-primary tracking-wider font-mono flex items-center gap-1.5">
                OMNICORE <span className="text-accent-blue text-[11px] font-normal">RAG</span>
              </h1>
              <p className="text-[10px] text-text-muted font-mono tracking-tight">
                Visual Evidence Explorer
              </p>
            </div>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="p-2 space-y-1">
          <div className="px-3 py-2 text-[10px] uppercase font-mono tracking-wider text-text-muted">
            Workspace
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? "bg-accent/15 text-accent-blue border border-accent/30 shadow-sm"
                    : "text-text-secondary hover:text-text-primary hover:bg-bg-card/70"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive
                        ? "text-accent-blue"
                        : "text-text-muted group-hover:text-text-secondary"
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.tag && (
                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-accent-purple/20 text-accent-purple border border-accent-purple/30">
                    {item.tag}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer info */}
      <div className="p-3 border-t border-border-subtle/70 bg-bg-darkest/40">
        <div className="flex items-center justify-between text-[11px] text-text-muted font-mono">
          <span>Engine</span>
          <span className="text-text-secondary">FastAPI + Chroma</span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-text-muted font-mono mt-1">
          <span>Embedding</span>
          <span className="text-text-secondary">bge-small (384d)</span>
        </div>
      </div>
    </aside>
  );
};
