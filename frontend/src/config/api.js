/**
 * API Configuration
 *
 * Prefer same-origin API requests unless an explicit API URL is configured.
 * This keeps auth cookies first-party and avoids login loops when the frontend
 * is opened via localhost aliases such as 127.0.0.1.
 */
function normalizeExplicitUrl(value) {
  if (typeof value !== "string") return "";

  const trimmed = value.trim();
  if (!trimmed || trimmed === "undefined" || trimmed === "null") {
    return "";
  }

  return trimmed.replace(/\/+$/, "");
}

export function resolveApiUrl({
  runtimeUrl,
  viteUrl,
  isDev = false,
} = {}) {
  const explicitRuntimeUrl = normalizeExplicitUrl(runtimeUrl);
  if (explicitRuntimeUrl) {
    return explicitRuntimeUrl;
  }

  const explicitViteUrl = normalizeExplicitUrl(viteUrl);
  if (explicitViteUrl) {
    return explicitViteUrl;
  }

  // Default to same-origin so cookies stay first-party. Local Vite dev uses
  // a proxy in vite.config.js, so it can use relative URLs as well.
  if (isDev) {
    return "";
  }

  return "";
}

export const API_URL = resolveApiUrl({
  runtimeUrl: window.__FILAOPS_CONFIG__?.API_URL,
  viteUrl: import.meta.env.VITE_API_URL,
  isDev: import.meta.env.DEV,
});

export const API_TARGET_LABEL =
  API_URL || `${window.location.origin.replace(/\/+$/, "")}/api`;
