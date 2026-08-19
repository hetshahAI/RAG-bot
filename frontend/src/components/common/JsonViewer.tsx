import React, { useState } from "react";
import { Copy, Check } from "lucide-react";

interface JsonViewerProps {
  data: any;
  title?: string;
  maxHeight?: string;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  title,
  maxHeight = "max-h-72",
}) => {
  const [copied, setCopied] = useState(false);

  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-border-subtle bg-bg-darkest overflow-hidden text-xs">
      <div className="flex items-center justify-between px-3 py-1.5 bg-bg-card border-b border-border-subtle text-[11px] text-text-secondary">
        <span className="font-mono">{title || "JSON Payload"}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-text-primary transition-colors text-[11px] px-1.5 py-0.5 rounded hover:bg-bg-elevated"
          title="Copy JSON"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-accent-green" />
              <span className="text-accent-green font-mono">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre
        className={`p-3 font-mono text-[11px] text-text-secondary overflow-auto leading-relaxed select-text ${maxHeight}`}
      >
        {jsonString}
      </pre>
    </div>
  );
};
