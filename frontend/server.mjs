import http from "node:http";
import https from "node:https";
import { createReadStream, existsSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildProxyHeaders } from "./server-proxy.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.resolve(__dirname, "dist");

function resolveListenPort() {
  for (const candidate of [process.env.FRONTEND_PORT, process.env.PORT, "8080"]) {
    const parsedPort = Number.parseInt(candidate || "", 10);
    if (Number.isInteger(parsedPort) && parsedPort >= 0 && parsedPort < 65536) {
      return parsedPort;
    }
  }

  return 8080;
}

const port = resolveListenPort();
const apiUpstream = process.env.FRONTEND_API_UPSTREAM || "http://backend:8000";
const portalUpstream =
  process.env.FRONTEND_PORTAL_UPSTREAM ||
  process.env.FRONTEND_API_UPSTREAM ||
  apiUpstream;
const staticUpstream =
  process.env.FRONTEND_STATIC_UPSTREAM ||
  process.env.FRONTEND_API_UPSTREAM ||
  apiUpstream;
const otlpTracesUpstream = process.env.FRONTEND_OTLP_TRACES_UPSTREAM || "";

const longCacheExtensions = /\.(?:css|gif|ico|jpe?g|js|mjs|png|svg|woff2?)$/iu;
const hopByHopHeaders = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

const mimeTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".gif", "image/gif"],
  [".html", "text/html; charset=utf-8"],
  [".ico", "image/x-icon"],
  [".jpeg", "image/jpeg"],
  [".jpg", "image/jpeg"],
  [".js", "application/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".map", "application/json; charset=utf-8"],
  [".mjs", "application/javascript; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".txt", "text/plain; charset=utf-8"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
]);

const securityHeaders = {
  "X-Frame-Options": "SAMEORIGIN",
  "X-Content-Type-Options": "nosniff",
  "X-XSS-Protection": "1; mode=block",
  "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' https://rum-ingest.us1.signalfx.com; frame-ancestors 'self'; form-action 'self'; base-uri 'self'; object-src 'none'",
};

function applySecurityHeaders(headers) {
  const mergedHeaders = { ...headers };
  for (const [key, value] of Object.entries(securityHeaders)) {
    if (!(key in mergedHeaders)) {
      mergedHeaders[key] = value;
    }
  }
  return mergedHeaders;
}

function getContentType(filePath) {
  return (
    mimeTypes.get(path.extname(filePath).toLowerCase()) ||
    "application/octet-stream"
  );
}

function filterResponseHeaders(headers) {
  const filteredHeaders = {};

  for (const [key, value] of Object.entries(headers)) {
    if (value === undefined) {
      continue;
    }

    if (hopByHopHeaders.has(key.toLowerCase())) {
      continue;
    }

    filteredHeaders[key] = value;
  }

  return filteredHeaders;
}

function sendJson(response, statusCode, payload) {
  const body = JSON.stringify(payload);
  const headers = applySecurityHeaders({
    "Cache-Control": "no-store",
    "Content-Length": Buffer.byteLength(body),
    "Content-Type": "application/json; charset=utf-8",
  });

  response.writeHead(statusCode, headers);
  response.end(body);
}

function sendRedirect(response, location) {
  response.writeHead(
    301,
    applySecurityHeaders({
      Location: location,
      "Cache-Control": "no-store",
    })
  );
  response.end();
}

function safeResolveStaticPath(requestPathname) {
  let decodedPath;

  try {
    decodedPath = decodeURIComponent(requestPathname);
  } catch {
    return null;
  }

  const normalizedPath = path.normalize(decodedPath).replace(/^(\.\.[/\\])+/, "");
  const candidatePath = path.join(distDir, normalizedPath);

  if (!candidatePath.startsWith(distDir)) {
    return null;
  }

  return candidatePath;
}

function serveFile(response, filePath, extraHeaders = {}) {
  const stats = statSync(filePath);
  const headers = applySecurityHeaders({
    "Content-Length": stats.size,
    "Content-Type": getContentType(filePath),
    ...extraHeaders,
  });

  response.writeHead(200, headers);
  createReadStream(filePath).pipe(response);
}

function serveStatic(response, requestPathname) {
  const targetPath = requestPathname === "/" ? "/index.html" : requestPathname;
  const resolvedPath = safeResolveStaticPath(targetPath);

  if (!resolvedPath) {
    sendJson(response, 400, { detail: "invalid path" });
    return;
  }

  if (existsSync(resolvedPath) && statSync(resolvedPath).isFile()) {
    const isConfig = path.basename(resolvedPath) === "config.js";
    const isIndex = path.basename(resolvedPath) === "index.html";
    const cacheControl =
      isConfig || isIndex
        ? "no-store"
        : longCacheExtensions.test(resolvedPath)
          ? "public, immutable, max-age=31536000"
          : "public, max-age=3600";

    serveFile(response, resolvedPath, { "Cache-Control": cacheControl });
    return;
  }

  if (path.extname(targetPath)) {
    sendJson(response, 404, { detail: "not found" });
    return;
  }

  serveFile(response, path.join(distDir, "index.html"), {
    "Cache-Control": "no-store",
  });
}

function proxyRequest(request, response, upstreamBase, options = {}) {
  const incomingUrl = new URL(request.url, "http://frontend.local");
  const targetUrl = options.absoluteTarget
    ? new URL(upstreamBase)
    : new URL(incomingUrl.pathname + incomingUrl.search, upstreamBase);

  const client = targetUrl.protocol === "https:" ? https : http;
  const upstreamRequest = client.request(
    targetUrl,
    {
      method: request.method,
      headers: buildProxyHeaders(request, targetUrl, {
        upstreamHostHeader: options.upstreamHostHeader === true,
      }),
    },
    (upstreamResponse) => {
      const headers = applySecurityHeaders(
        filterResponseHeaders(upstreamResponse.headers)
      );
      response.writeHead(upstreamResponse.statusCode || 502, headers);
      upstreamResponse.pipe(response);
    }
  );

  upstreamRequest.on("error", (error) => {
    const statusCode = error.code === "ECONNREFUSED" ? 502 : 504;
    sendJson(response, statusCode, {
      detail: `upstream request failed: ${error.message}`,
    });
  });

  request.pipe(upstreamRequest);
}

const server = http.createServer((request, response) => {
  if (!request.url) {
    sendJson(response, 400, { detail: "missing request URL" });
    return;
  }

  const url = new URL(request.url, "http://frontend.local");

  if (request.method === "GET" && url.pathname === "/health") {
    sendJson(response, 200, { status: "ok" });
    return;
  }

  if (url.pathname === "/portal") {
    sendRedirect(response, "/portal/");
    return;
  }

  if (url.pathname.startsWith("/api")) {
    proxyRequest(request, response, apiUpstream);
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    proxyRequest(request, response, staticUpstream);
    return;
  }

  if (url.pathname.startsWith("/portal/")) {
    proxyRequest(request, response, portalUpstream);
    return;
  }

  if (url.pathname === "/otel/v1/traces") {
    if (!otlpTracesUpstream) {
      sendJson(response, 404, { detail: "trace export is not configured" });
      return;
    }

    proxyRequest(request, response, otlpTracesUpstream, {
      absoluteTarget: true,
      upstreamHostHeader: true,
    });
    return;
  }

  serveStatic(response, url.pathname);
});

server.listen(port, "0.0.0.0", () => {
  console.info(
    `FilaOps frontend service listening on port ${port} with API upstream ${apiUpstream}`
  );
});
