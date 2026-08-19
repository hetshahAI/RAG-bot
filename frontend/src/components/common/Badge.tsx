import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "purple" | "blue" | "outline";
  size?: "sm" | "md";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "default",
  size = "sm",
  className = "",
}) => {
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";

  const variantClasses = {
    default: "bg-bg-elevated text-text-secondary border border-border-subtle",
    success: "bg-accent-green/10 text-accent-green border border-accent-green/30",
    warning: "bg-accent-amber/10 text-accent-amber border border-accent-amber/30",
    error: "bg-accent-red/10 text-accent-red border border-accent-red/30",
    purple: "bg-accent-purple/10 text-accent-purple border border-accent-purple/30",
    blue: "bg-accent-blue/10 text-accent-blue border border-accent-blue/30",
    outline: "bg-transparent text-text-muted border border-border-subtle",
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono font-medium rounded-md tracking-tight ${sizeClasses} ${variantClasses} ${className}`}
    >
      {children}
    </span>
  );
};
