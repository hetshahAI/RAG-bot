import React, { useState, useRef } from "react";
import {
  X,
  UploadCloud,
  FileText,
  FileCode,
  Image as ImageIcon,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { api } from "../../api/endpoints";
import { DocumentIngestResponse } from "../../types/backend";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (res: DocumentIngestResponse) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [tab, setTab] = useState<"file" | "text">("file");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name);
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUploading(true);
    setError(null);

    try {
      let result: DocumentIngestResponse;
      if (tab === "file") {
        if (!file) {
          throw new Error("Please select a file to ingest.");
        }
        result = await api.ingestFile(file, title.trim() || undefined);
      } else {
        if (!text.trim()) {
          throw new Error("Text content cannot be empty.");
        }
        result = await api.ingestText(text.trim(), title.trim() || undefined);
      }

      onSuccess(result);
      onClose();
      // Reset
      setFile(null);
      setTitle("");
      setText("");
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.message || "Failed to ingest document.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl bg-bg-card border border-border-subtle shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between bg-bg-darkest/40">
          <div>
            <h3 className="text-sm font-bold text-text-primary font-mono">
              Ingest New Document
            </h3>
            <p className="text-[11px] text-text-muted">
              Add documents to raw knowledge storage (TXT, PDF, OCR Images)
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-bg-elevated text-text-muted hover:text-text-primary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-border-subtle bg-bg-darkest/20 text-xs font-mono">
          <button
            type="button"
            onClick={() => setTab("file")}
            className={`flex-1 py-2.5 text-center font-medium transition-colors ${
              tab === "file"
                ? "border-b-2 border-accent text-accent-blue font-bold bg-bg-card"
                : "text-text-muted hover:text-text-secondary"
            }`}
          >
            File Ingestion (PDF / TXT / OCR Image)
          </button>
          <button
            type="button"
            onClick={() => setTab("text")}
            className={`flex-1 py-2.5 text-center font-medium transition-colors ${
              tab === "text"
                ? "border-b-2 border-accent text-accent-blue font-bold bg-bg-card"
                : "text-text-muted hover:text-text-secondary"
            }`}
          >
            Plain Text Paste
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs font-sans">
          {/* Title Input */}
          <div>
            <label className="block text-[11px] font-mono text-text-muted mb-1">
              Document Title / Label (Optional)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. system_architecture_spec.pdf"
              className="w-full px-3 py-2 bg-bg-darkest rounded-lg border border-border-subtle focus:border-accent text-text-primary outline-none font-mono text-xs"
            />
          </div>

          {/* File Upload Zone */}
          {tab === "file" ? (
            <div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".txt,.pdf,.png,.jpg,.jpeg,.webp"
                className="hidden"
              />
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                className="border-2 border-dashed border-border-subtle hover:border-accent-blue/60 rounded-xl p-6 text-center cursor-pointer bg-bg-darkest/40 hover:bg-bg-darkest/70 transition-all"
              >
                <div className="w-10 h-10 rounded-full bg-bg-elevated flex items-center justify-center mx-auto mb-2 text-accent-blue">
                  <UploadCloud className="w-5 h-5" />
                </div>
                {file ? (
                  <div className="space-y-1">
                    <p className="font-semibold text-text-primary font-mono">
                      {file.name}
                    </p>
                    <p className="text-[10px] text-text-muted font-mono">
                      {(file.size / 1024).toFixed(1)} KB • Click to change
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-text-primary font-medium">
                      Drag and drop file here, or browse
                    </p>
                    <p className="text-[10px] text-text-muted font-mono mt-1">
                      Supports .txt, .pdf, .png, .jpg, .webp (OCR extracted)
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Text Input */
            <div>
              <label className="block text-[11px] font-mono text-text-muted mb-1">
                Raw Text Content *
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste normalized text content here..."
                rows={6}
                className="w-full p-3 bg-bg-darkest rounded-lg border border-border-subtle focus:border-accent text-text-primary outline-none font-mono text-xs leading-relaxed"
                required
              />
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="p-2.5 rounded-lg bg-accent-red/10 border border-accent-red/30 text-accent-red font-mono text-[11px] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle/50">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-2 rounded-lg bg-bg-elevated hover:bg-bg-hover text-text-secondary text-xs font-mono transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUploading || (tab === "file" && !file) || (tab === "text" && !text.trim())}
              className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-blue text-white text-xs font-mono font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-md shadow-accent/20"
            >
              {isUploading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Ingesting...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Store Document</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
