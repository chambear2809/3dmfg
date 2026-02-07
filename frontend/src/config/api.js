/**
 * API Configuration
 *
 * Centralized API URL configuration.
 *
 * When accessed via HTTPS reverse proxy (like Caddy), use relative URLs
 * so requests go through the proxy. Otherwise use localhost for dev.
 */
const getApiUrl = () => {
  // Runtime config injected by docker-entrypoint.sh at container startup
  const runtimeUrl = window.__FILAOPS_CONFIG__?.API_URL;
  if (runtimeUrl) {
    return runtimeUrl;
  }

  // Build-time Vite env var
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // If accessed via HTTPS or non-localhost domain, use relative URLs
  // (requests will go through the reverse proxy)
  if (
    window.location.protocol === "https:" ||
    (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1")
  ) {
    return "";  // Relative URLs: /api/v1/... goes through Caddy
  }

  // Local development - direct to backend
  return "http://localhost:8000";
};

export const API_URL = getApiUrl();

