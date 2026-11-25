import { Link } from "@tanstack/react-router";
import { ChevronLeft } from "lucide-react";
import type { ReactNode } from "react";

interface ScreenHeaderProps {
  title: string;
  back?: { to: string; label?: string };
  right?: ReactNode;
  subtitle?: string;
}

export function ScreenHeader({ title, back, right, subtitle }: ScreenHeaderProps) {
  return (
    <header className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-5 pt-[max(env(safe-area-inset-top),1rem)] pb-4">
      <div className="min-w-[40px]">
        {back ? (
          <Link
            to={back.to}
            className="glass-subtle grid h-10 w-10 place-items-center rounded-full transition-all active:scale-90"
            aria-label={back.label ?? "Back"}
          >
            <ChevronLeft className="h-5 w-5" />
          </Link>
        ) : null}
      </div>
      <div className="min-w-0 text-center">
        <h1 className="truncate font-display text-xl font-medium">{title}</h1>
        {subtitle ? (
          <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
        ) : null}
      </div>
      <div className="min-w-[40px] justify-self-end">{right}</div>
    </header>
  );
}
