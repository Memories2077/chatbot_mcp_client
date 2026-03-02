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
