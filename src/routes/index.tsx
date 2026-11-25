import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  ImageUp,
  LoaderCircle,
  Mic,
  RotateCcw,
  Settings,
  Sparkles,
  Wifi,
  X,
} from "lucide-react";
import { GlassCard } from "@/components/glass-card";
import { IconButton } from "@/components/icon-button";
import { MobileShell } from "@/components/mobile-shell";
import { StatusPill } from "@/components/status-pill";
import { saveAnalysisHandoff } from "@/lib/analysis-handoff";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Lens — AI Camera Glasses" },
      {
        name: "description",
        content: "Live preview from your Raspberry Pi camera glasses. Capture and ask.",
      },
      { property: "og:title", content: "Lens — Home" },
      {
        property: "og:description",
        content: "Live preview from your Raspberry Pi camera glasses.",
      },
    ],
  }),
  component: Home,
});

function Home() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const requestIdRef = useRef(0);
  const [previewState, setPreviewState] = useState<
    "idle" | "requesting" | "live" | "image" | "error"
  >("idle");
  const [imageDataUrl, setImageDataUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [prompt, setPrompt] = useState("What am I looking at?");

  const stopCamera = useCallback(() => {
    requestIdRef.current += 1;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  useEffect(() => stopCamera, [stopCamera]);

  const cameraErrorMessage = (error: unknown) => {
    if (!(error instanceof DOMException)) {
      return "The camera could not be started. Please try again.";
    }
    if (error.name === "NotAllowedError" || error.name === "SecurityError") {
      return "Camera permission was denied. Allow access in your browser settings or upload a photo.";
    }
    if (error.name === "NotFoundError" || error.name === "OverconstrainedError") {
      return "No available camera was found on this device.";
    }
    if (error.name === "NotReadableError" || error.name === "AbortError") {
      return "The camera is already in use or could not be read. Close other camera apps and try again.";
    }
    return "The camera could not be started. Please try again.";
  };

  const startCamera = async () => {
    stopCamera();
    setImageDataUrl(null);
    setErrorMessage("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMessage(
        "This browser does not support camera access. Please upload a photo instead.",
      );
      setPreviewState("error");
      return;
    }

    const requestId = requestIdRef.current;
    setPreviewState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "user" } },
        audio: false,
      });
      if (requestId !== requestIdRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      setPreviewState("live");
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      setErrorMessage(cameraErrorMessage(error));
      setPreviewState("error");
    }
  };

  useEffect(() => {
    if (previewState === "live" && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      void videoRef.current.play().catch(() => {
        setErrorMessage("The camera preview could not be played. Please try again.");
        stopCamera();
        setPreviewState("error");
      });
    }
  }, [previewState, stopCamera]);

  const snapPhoto = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) {
      setErrorMessage("The camera image is not ready yet. Wait a moment and try again.");
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setErrorMessage("The photo could not be captured in this browser.");
      setPreviewState("error");
      stopCamera();
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    setImageDataUrl(canvas.toDataURL("image/jpeg", 0.9));
    stopCamera();
    setPreviewState("image");
  };

  const cancelCamera = () => {
    stopCamera();
    setErrorMessage("");
    setPreviewState("idle");
  };

  const chooseFile = () => fileInputRef.current?.click();

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    stopCamera();
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setErrorMessage("Choose a JPEG, PNG, or WebP image.");
      setPreviewState("error");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== "string") {
        setErrorMessage("The selected image could not be loaded.");
        setPreviewState("error");
        return;
      }
      const testImage = new Image();
      testImage.onload = () => {
        setImageDataUrl(reader.result as string);
        setErrorMessage("");
        setPreviewState("image");
      };
      testImage.onerror = () => {
        setErrorMessage("The selected file is not a readable image.");
        setPreviewState("error");
      };
      testImage.src = reader.result;
    };
    reader.onerror = () => {
      setErrorMessage("The selected image could not be loaded.");
      setPreviewState("error");
    };
    reader.readAsDataURL(file);
  };

  const analyze = () => {
    if (!imageDataUrl) {
      setErrorMessage("Capture or upload an image before analyzing it.");
      setPreviewState("error");
      return;
    }
    const question = prompt.trim();
    if (!question) {
      setErrorMessage("Write a question for Gemini before analyzing the image.");
      return;
    }
    try {
      saveAnalysisHandoff({
        imageDataUrl,
        question,
        capturedAt: new Date().toISOString(),
      });
      void navigate({ to: "/result" });
    } catch {
      setErrorMessage("This image is too large to prepare for analysis. Try a smaller image.");
      setPreviewState("error");
    }
  };

  const controlClass =
    "glass-subtle flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all active:scale-[0.98] disabled:opacity-50";

  return (
    <MobileShell>
      <header className="px-5 pt-[max(env(safe-area-inset-top),1rem)] pb-4">
        <p className="text-xs tracking-[0.2em] text-muted-foreground uppercase">Lens</p>
      </header>

      <main className="flex flex-1 flex-col gap-4 px-5 pb-[max(env(safe-area-inset-bottom),1.5rem)]">
        {/* Status bar */}
        <GlassCard variant="subtle" className="!p-3.5">
          <div className="grid grid-cols-2 gap-3">
            <StatusPill status="online" label="Raspberry Pi" sublabel="192.168.1.42" />
            <StatusPill status="pending" label="Gemini" sublabel="Ready" />
          </div>
        </GlassCard>

        {/* Camera preview */}
        <GlassCard variant="strong" className="relative flex-1 overflow-hidden !p-0">
          <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_30%,oklch(0.32_0.04_270)_0%,oklch(0.16_0.012_270)_70%)]" />
          {previewState !== "live" && previewState !== "image" && (
            <div className="absolute inset-0 animate-shimmer opacity-40" />
          )}

          <div className="absolute top-4 left-4 flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-[var(--danger)]/90">
              <span className="h-1.5 w-1.5 rounded-full bg-white" />
            </span>
            <span className="text-xs font-medium tracking-wider uppercase">
              {previewState === "live" ? "Live" : previewState === "image" ? "Ready" : "Camera"}
            </span>
          </div>
          <div className="absolute top-4 right-4 flex items-center gap-1.5 rounded-full bg-black/30 px-2.5 py-1 text-[10px] backdrop-blur-md">
            <Wifi className="h-3 w-3" />
            <span>Pi Cam v3 Wide</span>
          </div>

          <div className="relative flex h-full min-h-[340px] flex-col items-center justify-center gap-4 p-6 text-center">
            {previewState === "live" && (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="absolute inset-0 h-full w-full object-cover"
              />
            )}
            {previewState === "image" && imageDataUrl && (
              <img
                src={imageDataUrl}
                alt="Selected for analysis"
                className="absolute inset-0 h-full w-full object-cover"
                onError={() => {
                  setImageDataUrl(null);
                  setErrorMessage("The selected image could not be displayed.");
                  setPreviewState("error");
                }}
              />
            )}
            {(previewState === "idle" || previewState === "error") && (
              <>
                <Camera className="h-10 w-10 text-foreground/60" strokeWidth={1.25} />
                <p
                  className={`max-w-[260px] text-sm ${previewState === "error" ? "text-red-200" : "text-muted-foreground"}`}
                  role={previewState === "error" ? "alert" : undefined}
                >
                  {previewState === "error"
                    ? errorMessage
                    : "Waiting for stream from camera glasses…"}
                </p>
              </>
            )}
            {previewState === "requesting" && (
              <>
                <LoaderCircle className="h-9 w-9 animate-spin text-foreground/70" />
                <p className="text-sm text-muted-foreground">Starting camera...</p>
              </>
            )}
            <div className="relative z-10 mt-auto flex w-full flex-wrap justify-center gap-2">
              {(previewState === "idle" || previewState === "error") && (
                <>
                  <button type="button" className={controlClass} onClick={startCamera}>
                    <Camera className="h-4 w-4" />
                    Use camera
                  </button>
                  <button type="button" className={controlClass} onClick={chooseFile}>
                    <ImageUp className="h-4 w-4" />
                    Upload photo
                  </button>
                </>
              )}
              {previewState === "live" && (
                <>
                  <button
                    type="button"
                    className={`${controlClass} bg-white text-black`}
                    onClick={snapPhoto}
                  >
                    <Camera className="h-4 w-4" />
                    Snap photo
                  </button>
                  <button type="button" className={controlClass} onClick={cancelCamera}>
                    <X className="h-4 w-4" />
                    Cancel camera
                  </button>
                </>
              )}
              {previewState === "image" && (
                <>
                  <button
                    type="button"
                    className={controlClass}
                    onClick={() => {
                      setImageDataUrl(null);
                      setPreviewState("idle");
                    }}
                  >
                    <RotateCcw className="h-4 w-4" />
                    Retake
                  </button>
                  <button type="button" className={controlClass} onClick={startCamera}>
                    <Camera className="h-4 w-4" />
                    Use camera
                  </button>
                  <button type="button" className={controlClass} onClick={chooseFile}>
                    <ImageUp className="h-4 w-4" />
                    Upload another
                  </button>
                  <button
                    type="button"
                    className={`${controlClass} bg-white text-black`}
                    onClick={analyze}
                    disabled={!prompt.trim()}
                  >
                    <Sparkles className="h-4 w-4" />
                    Analyze
                  </button>
                </>
              )}
            </div>
          </div>
          <canvas ref={canvasRef} className="hidden" aria-hidden="true" />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handleFileChange}
          />

          {/* corner ticks */}
          {[
            "left-3 top-3 border-t border-l rounded-tl-xl",
            "right-3 top-3 border-t border-r rounded-tr-xl",
            "left-3 bottom-3 border-b border-l rounded-bl-xl",
            "right-3 bottom-3 border-b border-r rounded-br-xl",
          ].map((c) => (
            <span key={c} className={`absolute h-5 w-5 border-foreground/30 ${c}`} />
          ))}
        </GlassCard>

        {/* AI hint */}
        <GlassCard variant="subtle" className="!p-3.5">
          <div className="flex items-start gap-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--accent)]/15 text-[var(--accent)]">
              <Sparkles className="h-4 w-4" />
            </span>
            {previewState === "image" ? (
              <div className="min-w-0 flex-1">
                <label
                  htmlFor="analysis-prompt"
                  className="mb-1.5 block text-[11px] tracking-wider text-muted-foreground uppercase"
                >
                  Ask Gemini about this image
                </label>
                <textarea
                  id="analysis-prompt"
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  maxLength={1000}
                  rows={2}
                  placeholder="What would you like to know?"
                  className="min-h-20 w-full resize-y rounded-xl border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-[var(--accent)]/60"
                />
              </div>
            ) : (
              <p className="min-w-0 pt-1.5 text-sm text-muted-foreground">
                Tap capture, then ask anything about the scene.
              </p>
            )}
          </div>
        </GlassCard>

        {/* Action row */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-end gap-6 pt-2">
          <IconButton icon={<Mic className="h-5 w-5" />} label="Voice" />

          <button
            type="button"
            aria-label="Capture"
            onClick={startCamera}
            className="group relative grid h-20 w-20 place-items-center rounded-full transition-all active:scale-95"
          >
            <span className="absolute inset-0 rounded-full bg-gradient-to-b from-white to-white/70 shadow-[0_20px_50px_-10px_oklch(0_0_0/60%)]" />
            <span className="absolute inset-1.5 rounded-full border border-black/10" />
            <span className="absolute inset-3 rounded-full bg-white" />
            <Camera className="relative z-10 h-6 w-6 text-black" strokeWidth={2} />
          </button>

          <Link to="/settings" className="flex flex-col items-center gap-2">
            <IconButton icon={<Settings className="h-5 w-5" />} label="Settings" tabIndex={-1} />
          </Link>
        </div>
      </main>
    </MobileShell>
  );
}
