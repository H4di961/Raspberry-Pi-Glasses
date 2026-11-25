import { createServerFn } from "@tanstack/react-start";

interface AnalyzeImageInput {
  imageDataUrl: string;
  question: string;
}

interface GeminiResponse {
  candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
  error?: { message?: string };
}

const parseImageDataUrl = (dataUrl: string) => {
  const match = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/.exec(dataUrl);
  if (!match) throw new Error("The selected image format is not supported.");
  return { mimeType: match[1], data: match[2] };
};

const cleanPlainText = (text: string) =>
  text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();

export const analyzeImage = createServerFn({ method: "POST" })
  .validator((input: AnalyzeImageInput) => {
    if (!input.question.trim()) throw new Error("A question is required.");
    if (input.imageDataUrl.length > 20_000_000) {
      throw new Error("The selected image is too large for analysis.");
    }
    parseImageDataUrl(input.imageDataUrl);
    return input;
  })
  .handler(async ({ data }) => {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error(
        "Gemini is not configured. Add GEMINI_API_KEY to .env.local and restart the server.",
      );
    }

    const image = parseImageDataUrl(data.imageDataUrl);
    const model = process.env.GEMINI_MODEL ?? "gemini-3.5-flash";
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
        body: JSON.stringify({
          system_instruction: {
            parts: [
              {
                text: "Answer clearly and accurately in natural plain text. Do not use Markdown, asterisks, hash headings, backticks, or other formatting symbols. Use short paragraphs and simple numbered lists only when helpful.",
              },
            ],
          },
          contents: [
            {
              role: "user",
              parts: [
                { inline_data: { mime_type: image.mimeType, data: image.data } },
                { text: data.question },
              ],
            },
          ],
        }),
      },
    );

    const result = (await response.json()) as GeminiResponse;
    if (!response.ok) {
      console.error("Gemini request failed", response.status, result.error?.message);
      throw new Error(
        response.status === 429
          ? "Gemini is temporarily rate-limited. Please try again shortly."
          : "Gemini could not analyze this image. Check the API key and try again.",
      );
    }

    const rawAnswer = result.candidates?.[0]?.content?.parts
      ?.map((part) => part.text)
      .filter((text): text is string => Boolean(text))
      .join("\n")
      .trim();
    if (!rawAnswer) throw new Error("Gemini returned no description for this image.");
    return { answer: cleanPlainText(rawAnswer) };
  });
