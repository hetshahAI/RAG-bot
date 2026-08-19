import React, { useState } from "react";
import {
  Settings,
  Cpu,
  Database,
  Search,
  BrainCircuit,
  Server,
  Code,
  Shield,
} from "lucide-react";
import {
  EmbeddingInfoResponse,
  HealthResponse,
  IndexStateModel,
  VectorStoreInfoResponse,
} from "../../types/backend";
import { Badge } from "../../components/common/Badge";
import { JsonViewer } from "../../components/common/JsonViewer";
import { api } from "../../api/endpoints";

interface SettingsViewProps {
  health: HealthResponse | null;
  indexState: IndexStateModel | null;
  embeddingInfo: EmbeddingInfoResponse | null;
  vectorInfo: VectorStoreInfoResponse | null;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  health,
  indexState,
  embeddingInfo,
  vectorInfo,
}) => {
  const [testText, setTestText] = useState("Testing dense vector generation.");
  const [testResult, setTestResult] = useState<any>(null);
  const [isTesting, setIsTesting] = useState(false);

  const handleTestEmbedding = async () => {
    if (!testText.trim()) return;
    setIsTesting(true);
    try {
      const res = await api.testEmbedding([testText.trim()]);
      setTestResult(res);
    } catch (err: any) {
      alert("Embedding test failed: " + err.message);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6 bg-bg-darkest font-sans">
      <div>
        <h2 className="text-base font-bold text-text-primary font-mono flex items-center gap-2">
          <Settings className="w-5 h-5 text-accent-blue" />
          <span>System & Pipeline Configuration</span>
        </h2>
        <p className="text-xs text-text-muted">
          Read-only technical configurations, model specifications, and vector store parameters
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 text-xs font-mono">
        {/* Retrieval Config */}
        <div className="p-4 rounded-xl bg-bg-card border border-border-subtle space-y-3">
          <div className="flex items-center gap-2 text-text-primary font-bold">
            <Search className="w-4 h-4 text-accent-blue" />
            <span>Retrieval & Candidate Quality</span>
          </div>
          <div className="space-y-2 text-text-secondary">
            <div className="flex justify-between">
              <span className="text-text-muted">Top K Chunks</span>
              <span className="text-text-primary font-bold">5</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Candidate K Limit</span>
              <span className="text-text-primary">10</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Similarity Threshold</span>
              <span className="text-accent-green font-bold">0.50 (Candidate Filter)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Max Context Chunks</span>
              <span className="text-text-primary">10</span>
            </div>
          </div>
        </div>

        {/* LLM Provider */}
        <div className="p-4 rounded-xl bg-bg-card border border-border-subtle space-y-3">
          <div className="flex items-center gap-2 text-text-primary font-bold">
            <BrainCircuit className="w-4 h-4 text-accent-purple" />
            <span>LLM Provider & Model</span>
          </div>
          <div className="space-y-2 text-text-secondary">
            <div className="flex justify-between">
              <span className="text-text-muted">Model</span>
              <span className="text-text-primary font-bold">mlx-community/Qwen3.6-35B-A3B-4bit</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Provider</span>
              <span className="text-text-primary">OpenAI-Compatible</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Temperature</span>
              <span className="text-accent-green font-bold">0.0 (Strict Grounding)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Endpoint Base</span>
              <span className="text-text-muted text-[10px]">https://exo.manysphere.info/v1</span>
            </div>
          </div>
        </div>

        {/* Vector DB Spec */}
        <div className="p-4 rounded-xl bg-bg-card border border-border-subtle space-y-3">
          <div className="flex items-center gap-2 text-text-primary font-bold">
            <Database className="w-4 h-4 text-accent-green" />
            <span>ChromaDB Vector Store</span>
          </div>
          <div className="space-y-2 text-text-secondary">
            <div className="flex justify-between">
              <span className="text-text-muted">Provider</span>
              <span className="text-text-primary">Local Persistent ChromaDB</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Collection Name</span>
              <span className="text-accent-blue font-bold">
                {vectorInfo?.collection_name || "rag_documents"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Metric</span>
              <span className="text-text-primary">Cosine Distance (1 - cos)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Persistence Directory</span>
              <span className="text-text-muted text-[10px]">
                {vectorInfo?.persistence_path || "backend/data/indexes/chroma"}
              </span>
            </div>
          </div>
        </div>

        {/* Embedding Spec */}
        <div className="p-4 rounded-xl bg-bg-card border border-border-subtle space-y-3">
          <div className="flex items-center gap-2 text-text-primary font-bold">
            <Cpu className="w-4 h-4 text-accent-amber" />
            <span>Embedding Model Specifications</span>
          </div>
          <div className="space-y-2 text-text-secondary">
            <div className="flex justify-between">
              <span className="text-text-muted">Model Name</span>
              <span className="text-text-primary font-bold">
                {embeddingInfo?.model_name || "BAAI/bge-small-en-v1.5"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Dimension</span>
              <span className="text-accent-blue font-bold">384 Dimensions</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Device</span>
              <span className="text-text-primary">{embeddingInfo?.device || "cpu"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">L2 Normalization</span>
              <span className="text-accent-green font-bold">Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Embedding Diagnostic Playground */}
      <div className="p-4 rounded-xl bg-bg-card border border-border-subtle space-y-3 text-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-text-primary font-bold font-mono">
            <Code className="w-4 h-4 text-accent-blue" />
            <span>Embedding Generation Test</span>
          </div>
          <Badge variant="blue" size="sm">POST /api/v1/embeddings/test</Badge>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="Type text to generate and inspect vector coordinates..."
            className="flex-1 px-3 py-2 bg-bg-darkest rounded-lg border border-border-subtle focus:border-accent text-text-primary font-mono text-xs outline-none"
          />
          <button
            onClick={handleTestEmbedding}
            disabled={isTesting || !testText.trim()}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-blue text-white font-mono text-xs font-medium transition-colors disabled:opacity-50"
          >
            {isTesting ? "Generating..." : "Generate Vector"}
          </button>
        </div>

        {testResult && (
          <div className="mt-3">
            <JsonViewer data={testResult} title="Embedding Test Result" maxHeight="max-h-48" />
          </div>
        )}
      </div>
    </div>
  );
};
