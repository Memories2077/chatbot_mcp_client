// Configuration for API endpoints
export const getBackendUrl = (): string => {
    // Docker mode: A full URL is provided at build time.
    if (process.env.NEXT_PUBLIC_BACKEND_URL) {
        return process.env.NEXT_PUBLIC_BACKEND_URL;
    }

    // Local development mode: Construct the URL from a port number.
    // Note: This requires NEXT_PUBLIC_BACKEND_PORT in your local .env file.
    const port = process.env.NEXT_PUBLIC_BACKEND_PORT || '8000';

    if (typeof window !== 'undefined') {
        // Client-side (Local Dev): construct from hostname and port.
        return `${window.location.protocol}//${window.location.hostname}:${port}`;
    }

    // Server-side (Local Dev, for SSR): construct from localhost and port.
    return `http://localhost:${port}`;
};

export const BACKEND_API = {
    chat: () => `${getBackendUrl()}/chat`,
    health: () => `${getBackendUrl()}/health`,
};

export const MODEL_CONFIG = {
  gemini: {
    defaultModel: 'gemini-2.5-flash',
    models: ['gemini-2.5-flash', 'gemini-2.5-pro'],
  },
  groq: {
    defaultModel: 'llama-3.3-70b-versatile',
    models: [
      'meta-llama/llama-4-scout-17b-16e-instruct',
      'moonshotai/kimi-k2-instruct',
      'moonshotai/kimi-k2-instruct-0905',
      'allam-2-7b',
      'llama-3.1-8b-instant',
      'llama-3.3-70b-versatile',
      'qwen/qwen3-32b',
      'openai/gpt-oss-120b',
      'openai/gpt-oss-20b',
      'groq/compound',
      'groq/compound-mini',
    ],
  },
  metaclaw: {
    defaultModel: 'gemini-2.5-flash',
    models: [
      'gemini-2.5-flash',
      'gemini-2.5-pro',
      'llama-3.3-70b-versatile',
      'qwen/qwen3-32b',
      'claude-3-5-sonnet-20241022'
    ],
  },
};
