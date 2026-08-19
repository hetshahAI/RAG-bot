import React from "react";
import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  text?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  text,
}) => {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  }[size];

  return (
    <div className="flex flex-col items-center justify-center gap-2 p-4 text-text-secondary">
      <Loader2 className={`${sizeClasses} animate-spin text-accent-blue`} />
      {text && <p className="text-xs font-mono">{text}</p>}
    </div>
  );
};
