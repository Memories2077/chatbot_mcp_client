// Configuration for API endpoints
export const getBackendUrl = (): string => {
    if (typeof window !== 'undefined') {
        // Client-side: use environment variable or fallback to window location
        return (
        process.env.NEXT_PUBLIC_BACKEND_URL ||
        `${window.location.protocol}//${window.location.hostname}:8000`
        );
    }
    // Server-side fallback (Docker internal network or local dev)
    // When running in a container, backend is reachable as 'backend'
    const port = process.env.BACKEND_PORT || '8000';
    return process.env.NEXT_PUBLIC_BACKEND_URL || `http://backend:${port}`;
};

export const BACKEND_API = {
    chat: () => `${getBackendUrl()}/chat`,
    health: () => `${getBackendUrl()}/health`,
};
