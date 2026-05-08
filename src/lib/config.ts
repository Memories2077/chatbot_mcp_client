// Configuration for browser-facing API endpoints.
export const getBackendUrl = (): string => {
  // Preferred browser/public setting: full FastAPI URL.
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL;
  }

  // Backward-compatible local development fallback: construct from a public port.
  // Prefer NEXT_PUBLIC_BACKEND_URL in new environments.
  const port = process.env.NEXT_PUBLIC_BACKEND_PORT || "8000";

  if (typeof window !== "undefined") {
    // Client-side (Local Dev): construct from hostname and port.
    return `${window.location.protocol}//${window.location.hostname}:${port}`;
  }

  // Server-side (Local Dev, for SSR): construct from localhost and port.
  return `http://localhost:${port}`;
};

export const BACKEND_API = {
  chat: () => `${getBackendUrl()}/chat`,
  health: () => `${getBackendUrl()}/health`,
  mcpMetadata: () => `${getBackendUrl()}/mcp/metadata`,
  mcpServers: () => `${getBackendUrl()}/mcp/servers`,
  mcpFeedback: (serverId: string) =>
    `${getBackendUrl()}/mcp/${encodeURIComponent(serverId)}/feedback`,
};

export interface BackendHealth {
  status: "healthy" | "unhealthy" | string;
  service: string;
  metaclawEnabled: boolean;
  effectiveProvider: "metaclaw" | "gemini" | "groq" | string;
  configuredFallbacks: string[];
  langgraphApiUrl?: string;
  mcpGenUrl?: string;
  detail?: string;
}

export async function fetchBackendHealth(): Promise<BackendHealth> {
  const response = await fetch(BACKEND_API.health(), { method: "GET" });
  if (!response.ok) {
    throw new Error(`Backend health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

export const MODEL_CONFIG = {
  gemini: {
    defaultModel: "gemini-2.5-flash",
    models: ["gemini-2.5-flash", "gemini-2.5-pro"],
  },
  groq: {
    defaultModel: "llama-3.3-70b-versatile",
    models: [
      "meta-llama/llama-4-scout-17b-16e-instruct",
      "moonshotai/kimi-k2-instruct",
      "moonshotai/kimi-k2-instruct-0905",
      "allam-2-7b",
      "llama-3.1-8b-instant",
      "llama-3.3-70b-versatile",
      "qwen/qwen3-32b",
      "openai/gpt-oss-120b",
      "openai/gpt-oss-20b",
      "groq/compound",
      "groq/compound-mini",
    ],
  },
};
