import React, { useState, useEffect, useCallback } from "react";
import { Shell } from "./components/layout/Shell";
import { NavTab } from "./components/layout/Sidebar";
import { QAPlayground } from "./features/playground/QAPlayground";
import { InjectionStudio } from "./features/studio/InjectionStudio";
import { DocumentsView } from "./features/documents/DocumentsView";
import { DashboardView } from "./features/dashboard/DashboardView";
import { SettingsView } from "./features/settings/SettingsView";
import { api } from "./api/endpoints";
import {
  DocumentListResponse,
  EmbeddingInfoResponse,
  HealthResponse,
  IndexStateModel,
  VectorStoreInfoResponse,
} from "./types/backend";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>("playground");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentListResponse | null>(null);
  const [indexState, setIndexState] = useState<IndexStateModel | null>(null);
  const [embeddingInfo, setEmbeddingInfo] = useState<EmbeddingInfoResponse | null>(null);
  const [vectorInfo, setVectorInfo] = useState<VectorStoreInfoResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);

  const fetchSystemData = useCallback(async () => {
    setIsRefreshing(true);
    const t0 = performance.now();
    try {
      const [h, d, s, e, v] = await Promise.allSettled([
        api.getHealth(),
        api.getDocuments(),
        api.getIndexState(),
        api.getEmbeddingInfo(),
        api.getVectorStoreInfo(),
      ]);

      if (h.status === "fulfilled") setHealth(h.value);
      if (d.status === "fulfilled") setDocuments(d.value);
      if (s.status === "fulfilled") setIndexState(s.value);
      if (e.status === "fulfilled") setEmbeddingInfo(e.value);
      if (v.status === "fulfilled") setVectorInfo(v.value);

      const duration = Math.round(performance.now() - t0);
      setLastLatencyMs(duration);
    } catch (err) {
      console.error("System refresh error:", err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchSystemData();
    const interval = setInterval(fetchSystemData, 30000); // 30s polling
    return () => clearInterval(interval);
  }, [fetchSystemData]);

  const getPageInfo = (tab: NavTab) => {
    switch (tab) {
      case "playground":
        return {
          title: "Q/A Playground",
          subtitle: "Interactive workflow execution graph & evidence inspection",
        };
      case "studio":
        return {
          title: "Injection Studio",
          subtitle: "Document ingestion, chunking, embedding, & selective reindexing canvas",
        };
      case "documents":
        return {
          title: "Documents",
          subtitle: "Knowledge base document management & active selection",
        };
      case "dashboard":
        return {
          title: "Dashboard",
          subtitle: "System overview, active index metrics, & pipeline health",
        };
      case "settings":
        return {
          title: "Settings",
          subtitle: "Technical specifications, model dimensions, & vector DB paths",
        };
    }
  };

  const pageInfo = getPageInfo(activeTab);

  return (
    <Shell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      title={pageInfo.title}
      subtitle={pageInfo.subtitle}
      health={health}
      indexState={indexState}
      vectorInfo={vectorInfo}
      onRefresh={fetchSystemData}
      isRefreshing={isRefreshing}
      lastLatencyMs={lastLatencyMs}
    >
      {activeTab === "playground" && <QAPlayground />}
      {activeTab === "studio" && (
        <InjectionStudio
          documents={documents}
          indexState={indexState}
          embeddingInfo={embeddingInfo}
          vectorInfo={vectorInfo}
          onRefreshAll={fetchSystemData}
        />
      )}
      {activeTab === "documents" && (
        <DocumentsView documents={documents} onRefresh={fetchSystemData} />
      )}
      {activeTab === "dashboard" && (
        <DashboardView
          health={health}
          documents={documents}
          indexState={indexState}
          embeddingInfo={embeddingInfo}
          vectorInfo={vectorInfo}
          onNavigate={(tab) => setActiveTab(tab as NavTab)}
        />
      )}
      {activeTab === "settings" && (
        <SettingsView
          health={health}
          indexState={indexState}
          embeddingInfo={embeddingInfo}
          vectorInfo={vectorInfo}
        />
      )}
    </Shell>
  );
};
