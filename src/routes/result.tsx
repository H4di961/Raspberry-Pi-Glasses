import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import {
  Camera,
  ImageIcon,
  LoaderCircle,
  MessageCirclePlus,
  Save,
  Sparkles,
  Volume2,
} from "lucide-react";
import { GlassCard } from "@/components/glass-card";
import { MobileShell } from "@/components/mobile-shell";
import { ScreenHeader } from "@/components/screen-header";
import { getAnalysisHandoff } from "@/lib/analysis-handoff";
import { analyzeImage } from "@/lib/gemini-analysis";

export const Route = createFileRoute("/result")({
  head: () => ({
    meta: [
      { title: "Result — Lens" },
      {
        name: "description",
        content: "AI analysis of the captured frame from your camera glasses.",
      },
      { property: "og:title", content: "Lens — Result" },
      {
        property: "og:description",
        content: "AI analysis of the captured frame.",
      },
    ],
  }),
  component: Result,
});

function Result() {
  const [handoff] = useState(() => (typeof window === "undefined" ? null : getAnalysisHandoff()));
  const runAnalysis = useServerFn(analyzeImage);
  const hasStartedRef = useRef(false);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(Boolean(handoff));

  const requestAnalysis = useCallback(async () => {
    if (!handoff) return;
    setIsLoading(true);
    setError("");
    try {
      const result = await runAnalysis({
        data: { imageDataUrl: handoff.imageDataUrl, question: handoff.question },
      });
      setAnswer(result.answer);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Gemini could not analyze this image. Please try again.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [handoff, runAnalysis]);

  useEffect(() => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;
    void requestAnalysis();
  }, [requestAnalysis]);
  return (
    <MobileShell>
      <ScreenHeader title="Result" subtitle="Gemini · 1.4s" back={{ to: "/" }} />

      <main className="flex flex-1 flex-col gap-4 overflow-y-auto px-5 pb-[max(env(safe-area-inset-bottom),1.5rem)]">
        {/* Captured image */}
        <GlassCard variant="strong" className="relative overflow-hidden !p-0">
          <div className="aspect-[4/3] w-full bg-[radial-gradient(120%_80%_at_30%_30%,oklch(0.38_0.06_60)_0%,oklch(0.18_0.02_270)_75%)]">
            {handoff ? (
              <img
                src={handoff.imageDataUrl}
                alt="Captured for analysis"
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="grid h-full place-items-center">
                <ImageIcon className="h-10 w-10 text-foreground/40" strokeWidth={1.25} />
              </div>
            )}
          </div>
          <div className="absolute top-3 left-3 rounded-full bg-black/40 px-2.5 py-1 text-[10px] tracking-wider backdrop-blur-md">
            CAPTURED · 19:42
          </div>
        </GlassCard>

        {/* Question */}
        <GlassCard variant="subtle" className="!p-3.5">
          <p className="text-[11px] tracking-wider text-muted-foreground uppercase">You asked</p>
          <p className="mt-1 text-sm">{handoff?.question ?? "What am I looking at?"}</p>
        </GlassCard>

        {/* Answer */}
        <GlassCard className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-[var(--accent)]/15 text-[var(--accent)]">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <span className="text-[11px] tracking-wider text-muted-foreground uppercase">
              Answer
            </span>
          </div>
          <div
            className="space-y-3 text-[15px] leading-relaxed whitespace-pre-line text-foreground/90"
            aria-live="polite"
          >
            {isLoading && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <LoaderCircle className="h-4 w-4 animate-spin" />
                <span>Analyzing your image...</span>
              </div>
            )}
            {!isLoading && answer}
            {!isLoading && error && (
              <div className="space-y-3" role="alert">
                <p className="text-red-200">{error}</p>
                <button
                  type="button"
                  onClick={() => void requestAnalysis()}
                  className="glass-subtle rounded-xl px-4 py-2 text-sm font-medium transition-all active:scale-[0.98]"
                >
                  Try again
                </button>
              </div>
            )}
            {!handoff && (
              <p className="text-muted-foreground">
                No image is ready for analysis. Capture or upload one first.
              </p>
            )}
          </div>
        </GlassCard>

        {/* Actions */}
        <div className="flex flex-col gap-2.5 pt-1">
          <button className="glass-strong flex items-center justify-center gap-2 rounded-2xl py-4 text-sm font-medium transition-all active:scale-[0.98]">
            <Volume2 className="h-4 w-4" />
            Speak Answer
          </button>

          <div className="grid grid-cols-2 gap-2.5">
            <button className="glass-subtle flex items-center justify-center gap-2 rounded-2xl py-3.5 text-sm font-medium transition-all active:scale-[0.98]">
              <MessageCirclePlus className="h-4 w-4" />
              Ask Another
            </button>
            <Link
              to="/"
              className="glass-subtle flex items-center justify-center gap-2 rounded-2xl py-3.5 text-sm font-medium transition-all active:scale-[0.98]"
            >
              <Camera className="h-4 w-4" />
              Capture Again
            </Link>
          </div>

          <button className="flex items-center justify-center gap-2 rounded-2xl py-3 text-xs text-muted-foreground transition-colors hover:text-foreground">
            <Save className="h-3.5 w-3.5" />
            Save Conversation
          </button>
        </div>
      </main>
    </MobileShell>
  );
}
