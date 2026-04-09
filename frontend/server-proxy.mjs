export function normalizeForwardedFor(request) {
  const remoteAddress =
    request.socket.remoteAddress?.replace(/^::ffff:/u, "") || "unknown";
  const existing = request.headers["x-forwarded-for"];
  return existing ? `${existing}, ${remoteAddress}` : remoteAddress;
}

export function buildProxyHeaders(
  request,
  target,
  { upstreamHostHeader = false } = {}
) {
  const forwardedHeaders = { ...request.headers };
  delete forwardedHeaders.connection;
  delete forwardedHeaders["proxy-connection"];

  const originalHost = request.headers.host || target.host;
  forwardedHeaders.host = upstreamHostHeader ? target.host : originalHost;
  forwardedHeaders["x-forwarded-for"] = normalizeForwardedFor(request);
  forwardedHeaders["x-forwarded-host"] = originalHost;
  forwardedHeaders["x-forwarded-proto"] =
    request.headers["x-forwarded-proto"] ||
    (request.socket.encrypted ? "https" : "http");

  return forwardedHeaders;
}
