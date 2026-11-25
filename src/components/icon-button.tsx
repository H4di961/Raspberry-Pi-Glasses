import { cn } from "@/lib/utils";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  label?: string;
  variant?: "glass" | "ghost";
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, label, className, variant = "glass", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "group flex flex-col items-center gap-2 transition-all active:scale-95",
          className,
        )}
        {...props}
      >
        <span
          className={cn(
            "grid h-14 w-14 place-items-center rounded-2xl transition-all",
            "border border-[var(--glass-border)]",
            variant === "glass"
              ? "glass-subtle group-hover:bg-[var(--glass-strong)]"
              : "bg-transparent group-hover:bg-[var(--glass)]",
          )}
        >
          {icon}
        </span>
        {label ? (
          <span className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            {label}
          </span>
        ) : null}
      </button>
    );
  },
);
IconButton.displayName = "IconButton";
