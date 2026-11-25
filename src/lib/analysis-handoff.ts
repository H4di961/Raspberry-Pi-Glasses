export interface AnalysisHandoff {
  imageDataUrl: string;
  question: string;
  capturedAt: string;
}

const STORAGE_KEY = "lens.analysis-handoff";

export function saveAnalysisHandoff(handoff: AnalysisHandoff) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(handoff));
}

export function getAnalysisHandoff(): AnalysisHandoff | null {
  const stored = sessionStorage.getItem(STORAGE_KEY);

  if (!stored) return null;

  try {
    const parsed: unknown = JSON.parse(stored);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "imageDataUrl" in parsed &&
      "question" in parsed &&
      "capturedAt" in parsed &&
      typeof parsed.imageDataUrl === "string" &&
      typeof parsed.question === "string" &&
      typeof parsed.capturedAt === "string"
    ) {
      return parsed as AnalysisHandoff;
    }
  } catch {
    // Ignore malformed or stale browser storage.
  }

  sessionStorage.removeItem(STORAGE_KEY);
  return null;
}
