import { cn } from "@/lib/utils";

type Status = "online" | "offline" | "pending";

interface StatusPillProps {
  status: Status;
  label: string;
  sublabel?: string;
}

const dotClass: Record<Status, string> = {
  online: "bg-[var(--success)] shadow-[0_0_12px_var(--success)]",
  offline: "bg-[var(--danger)]",
  pending: "bg-[var(--warning)] animate-pulse",
};

export function StatusPill({ status, label, sublabel }: StatusPillProps) {
  return (
    <div className="flex items-center gap-3">
      <span className="relative flex h-2.5 w-2.5 shrink-0">
        <span
          className={cn(
            "absolute inset-0 rounded-full",
            status === "online" && "animate-pulse-ring",
          )}
        />
        <span className={cn("h-2.5 w-2.5 rounded-full", dotClass[status])} />
      </span>
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-foreground">
          {label}
        </div>
        {sublabel ? (
          <div className="truncate text-xs text-muted-foreground">
            {sublabel}
          </div>
        ) : null}
      </div>
    </div>
  );
}
