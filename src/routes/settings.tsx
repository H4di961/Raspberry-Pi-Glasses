import { createFileRoute } from "@tanstack/react-router";
import { Check, Cpu, Eye, EyeOff, Key, Moon, Wifi } from "lucide-react";
import { useState } from "react";
import { GlassCard } from "@/components/glass-card";
import { MobileShell } from "@/components/mobile-shell";
import { ScreenHeader } from "@/components/screen-header";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Lens" },
      {
        name: "description",
        content:
          "Configure your Raspberry Pi connection, AI provider, and preferences.",
      },
      { property: "og:title", content: "Lens — Settings" },
      {
        property: "og:description",
        content: "Configure Raspberry Pi and AI provider.",
      },
    ],
  }),
  component: Settings,
});

const PROVIDERS = ["Gemini", "GPT", "Claude", "Local"] as const;
type Provider = (typeof PROVIDERS)[number];

function Settings() {
  const [ip, setIp] = useState("192.168.1.42");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [provider, setProvider] = useState<Provider>("Gemini");
  const [dark, setDark] = useState(true);
  const [testState, setTestState] = useState<"idle" | "testing" | "ok">("idle");

  const runTest = () => {
    setTestState("testing");
    setTimeout(() => setTestState("ok"), 1200);
  };

  return (
    <MobileShell>
      <ScreenHeader title="Settings" back={{ to: "/" }} />

      <main className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 pb-[max(env(safe-area-inset-bottom),1.5rem)]">
        {/* Pi */}
        <Section icon={<Wifi className="h-4 w-4" />} title="Raspberry Pi">
          <Field label="IP Address">
            <input
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              inputMode="decimal"
              placeholder="192.168.1.42"
              className="w-full bg-transparent text-base tracking-wide outline-none placeholder:text-muted-foreground/50"
            />
          </Field>

          <button
            onClick={runTest}
            disabled={testState === "testing"}
            className={cn(
              "flex items-center justify-center gap-2 rounded-2xl py-3.5 text-sm font-medium transition-all active:scale-[0.98]",
              testState === "ok"
                ? "bg-[var(--success)]/15 text-[var(--success)]"
                : "glass-subtle",
            )}
          >
            {testState === "ok" ? (
              <>
                <Check className="h-4 w-4" /> Connected
              </>
            ) : testState === "testing" ? (
              <>Testing…</>
            ) : (
              <>Test Connection</>
            )}
          </button>
        </Section>

        {/* AI */}
        <Section icon={<Cpu className="h-4 w-4" />} title="AI Provider">
          <div className="grid grid-cols-2 gap-2">
            {PROVIDERS.map((p) => {
              const active = provider === p;
              return (
                <button
                  key={p}
                  onClick={() => setProvider(p)}
                  className={cn(
                    "rounded-2xl border py-3 text-sm font-medium transition-all active:scale-[0.98]",
                    active
                      ? "border-foreground/30 bg-foreground/10 text-foreground"
                      : "border-[var(--glass-border)] bg-transparent text-muted-foreground",
                  )}
                >
                  {p}
                </button>
              );
            })}
          </div>

          <Field
            label="API Key"
            icon={<Key className="h-3.5 w-3.5" />}
            action={
              <button
                onClick={() => setShowKey((v) => !v)}
                className="text-muted-foreground hover:text-foreground"
                aria-label={showKey ? "Hide" : "Show"}
              >
                {showKey ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            }
          >
            <input
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              type={showKey ? "text" : "password"}
              placeholder="AIza••••••••"
              className="w-full bg-transparent text-base tracking-wide outline-none placeholder:text-muted-foreground/50"
            />
          </Field>
        </Section>

        {/* Preferences */}
        <Section icon={<Moon className="h-4 w-4" />} title="Appearance">
          <GlassCard variant="subtle" className="!p-4">
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
              <div className="min-w-0">
                <p className="text-sm font-medium">Dark Mode</p>
                <p className="truncate text-xs text-muted-foreground">
                  Optimized for low-light use
                </p>
              </div>
              <Toggle on={dark} onChange={setDark} />
            </div>
          </GlassCard>
        </Section>

        <p className="pt-2 pb-2 text-center text-[11px] tracking-wider text-muted-foreground/60 uppercase">
          Lens · v0.1 · Personal Build
        </p>
      </main>
    </MobileShell>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-2.5">
      <div className="flex items-center gap-2 px-1">
        <span className="text-muted-foreground">{icon}</span>
        <h2 className="text-[11px] font-medium tracking-[0.2em] text-muted-foreground uppercase">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}

function Field({
  label,
  icon,
  action,
  children,
}: {
  label: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <GlassCard variant="subtle" className="!p-4">
      <div className="mb-1 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-[11px] tracking-wider text-muted-foreground uppercase">
          {icon}
          {label}
        </div>
        {action}
      </div>
      {children}
    </GlassCard>
  );
}

function Toggle({
  on,
  onChange,
}: {
  on: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={on}
      onClick={() => onChange(!on)}
      className={cn(
        "relative h-7 w-12 shrink-0 rounded-full border transition-all",
        on
          ? "border-foreground/30 bg-foreground/20"
          : "border-[var(--glass-border)] bg-transparent",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 h-5 w-5 rounded-full bg-foreground shadow-md transition-all",
          on ? "left-[22px]" : "left-0.5",
        )}
      />
    </button>
  );
}
