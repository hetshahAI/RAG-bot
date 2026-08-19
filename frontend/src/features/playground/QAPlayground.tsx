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
  Send,
  Sparkles,
  Sliders,
  AlertCircle,
  HelpCircle,
  RotateCcw,
  Zap,
} from "lucide-react";
import { api } from "../../api/endpoints";
import { RAGAskResponse, RAGExecutionTrace } from "../../types/backend";
import { CustomWorkflowNode } from "../../components/nodes/CustomWorkflowNode";
import { buildQAGraph } from "../../lib/traceAdapter";
import { QAInspector } from "./QAInspector";
import { Badge } from "../../components/common/Badge";

const PRESET_QUESTIONS = [
  "What embedding model does this pipeline use?",
  "What vector database is used and where is it stored?",
  "How does deterministic chunking work in this system?",
  "What is the recipe for chocolate sourdough bread?",
];

export const QAPlayground: React.FC = () => {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState<number>(5);
  const [showSettings, setShowSettings] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Execution state
  const [response, setResponse] = useState<RAGAskResponse | null>(null);
  const [trace, setTrace] = useState<RAGExecutionTrace | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("answer");
  const [highlightedChunkId, setHighlightedChunkId] = useState<string | null>(null);

  const nodeTypes = useMemo(
    () => ({
      customNode: CustomWorkflowNode,
    }),
    []
  );

  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildQAGraph(null, null, null),
    []
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Synchronize graph when response or selection changes
  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = buildQAGraph(
      response,
      trace,
      selectedNodeId
    );
    setNodes(newNodes);
    setEdges(newEdges);
  }, [response, trace, selectedNodeId, setNodes, setEdges]);

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      setSelectedNodeId(node.id);
    },
    []
  );

  const executeAsk = async (queryToAsk?: string) => {
    const activeQuery = (queryToAsk || question).trim();
    if (!activeQuery) return;

    setIsLoading(true);
    setError(null);
    setSelectedNodeId("answer");

    try {
      // 1. Trigger production RAG ask
      const askResult = await api.askRAG(activeQuery, topK);
      setResponse(askResult);

      // 2. Fetch execution trace
      if (askResult.run_id) {
        try {
          const traceResult = await api.getRunTrace(askResult.run_id);
          setTrace(traceResult);
        } catch (traceErr) {
          console.warn("Failed to fetch execution trace:", traceErr);
        }
      }
    } catch (err: any) {
      console.error("RAG Ask failed:", err);
      setError(err.message || "Failed to execute question against RAG pipeline.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectChunk = (chunkId: string) => {
    setHighlightedChunkId(chunkId);
    setSelectedNodeId("retrieval");
  };

  return (
    <div className="flex h-full w-full relative overflow-hidden bg-bg-darkest">
      {/* Center Visual Workflow Canvas Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 relative">
        {/* Top Query Bar */}
        <div className="p-4 border-b border-border-subtle bg-bg-dark/90 backdrop-blur-md z-10 space-y-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              executeAsk();
            }}
            className="flex items-center gap-2"
          >
            <div className="flex-1 relative flex items-center">
              <div className="absolute left-3.5 text-text-muted">
                <Sparkles className="w-4 h-4 text-accent-blue" />
              </div>
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask any question to inspect knowledge base reasoning & evidence..."
                disabled={isLoading}
                className="w-full pl-10 pr-24 py-2.5 bg-bg-darkest rounded-xl border border-border-subtle hover:border-accent-blue/50 focus:border-accent focus:ring-1 focus:ring-accent text-xs font-sans text-text-primary placeholder:text-text-muted transition-all outline-none"
              />
              <button
                type="button"
                onClick={() => setShowSettings(!showSettings)}
                className={`absolute right-3 p-1 rounded-lg text-text-muted hover:text-text-primary transition-colors ${
                  showSettings ? "bg-bg-elevated text-accent-blue" : ""
                }`}
                title="Retrieval Settings"
              >
                <Sliders className="w-3.5 h-3.5" />
              </button>
            </div>

            <button
              type="submit"
              disabled={isLoading || !question.trim()}
              className="px-4 py-2.5 rounded-xl bg-accent hover:bg-accent-blue text-white font-medium text-xs font-mono transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-accent/20 shrink-0"
            >
              {isLoading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Ask RAG</span>
                </>
              )}
            </button>
          </form>

          {/* Quick presets & top_k slider */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px] font-mono text-text-muted flex items-center gap-1">
                <Zap className="w-3 h-3 text-accent-amber" /> Presets:
              </span>
              {PRESET_QUESTIONS.map((pq, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setQuestion(pq);
                    executeAsk(pq);
                  }}
                  disabled={isLoading}
                  className="px-2 py-0.5 rounded-md bg-bg-card border border-border-subtle hover:border-text-secondary/50 text-[11px] font-mono text-text-secondary hover:text-text-primary transition-colors truncate max-w-xs"
                >
                  {pq}
                </button>
              ))}
            </div>

            {showSettings && (
              <div className="flex items-center gap-2 font-mono text-xs text-text-secondary bg-bg-card px-3 py-1 rounded-lg border border-border-subtle">
                <span>Top K Chunks:</span>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-16 h-1 bg-bg-elevated accent-accent cursor-pointer"
                />
                <span className="text-accent-blue font-bold">{topK}</span>
              </div>
            )}
          </div>

          {/* Error Alert */}
          {error && (
            <div className="p-3 rounded-lg bg-accent-red/10 border border-accent-red/30 text-accent-red text-xs font-mono flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-accent-red hover:underline"
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

          {/* Canvas overlay instruction */}
          <div className="absolute top-4 left-4 pointer-events-none text-[11px] font-mono text-text-muted bg-bg-dark/80 px-2.5 py-1 rounded-md border border-border-subtle/50 backdrop-blur-sm">
            💡 Click on any node to inspect evidence, context, and timings
          </div>
        </div>
      </div>

      {/* Right Side Inspector Drawer / Panel */}
      {selectedNodeId && response && (
        <QAInspector
          selectedNodeId={selectedNodeId}
          onClose={() => setSelectedNodeId(null)}
          response={response}
          trace={trace}
          onSelectChunk={handleSelectChunk}
          highlightedChunkId={highlightedChunkId}
        />
      )}
    </div>
  );
};
