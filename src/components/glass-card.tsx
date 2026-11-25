import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "strong" | "subtle";
}

export function GlassCard({
  className,
  variant = "default",
  ...props
}: GlassCardProps) {
  const variantClass =
    variant === "strong"
      ? "glass-strong"
      : variant === "subtle"
        ? "glass-subtle"
        : "glass";
  return (
    <div
      className={cn(
        variantClass,
        "rounded-3xl p-5 transition-all duration-300",
        className,
      )}
      {...props}
    />
  );
}
