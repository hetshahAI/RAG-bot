import React from "react";
import { Sidebar, NavTab } from "./Sidebar";
import { Topbar } from "./Topbar";
import { StatusFooter } from "./StatusFooter";
import { HealthResponse, IndexStateModel, VectorStoreInfoResponse } from "../../types/backend";

interface ShellProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  title: string;
  subtitle?: string;
  health?: HealthResponse | null;
  indexState?: IndexStateModel | null;
  vectorInfo?: VectorStoreInfoResponse | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  lastLatencyMs?: number | null;
  children: React.ReactNode;
}

export const Shell: React.FC<ShellProps> = ({
  activeTab,
  onTabChange,
  title,
  subtitle,
  health,
  indexState,
  vectorInfo,
  onRefresh,
  isRefreshing,
  lastLatencyMs,
  children,
}) => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-darkest font-sans">
      {/* Navigation Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={onTabChange} />

      {/* Main App Canvas / Body */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        <Topbar
          title={title}
          subtitle={subtitle}
          indexState={indexState}
          vectorInfo={vectorInfo}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
        />

        {/* Dynamic page content */}
        <main className="flex-1 min-h-0 relative overflow-hidden bg-bg-darkest">
          {children}
        </main>

        <StatusFooter
          health={health}
          vectorInfo={vectorInfo}
          indexState={indexState}
          lastLatencyMs={lastLatencyMs}
        />
      </div>
    </div>
  );
};
