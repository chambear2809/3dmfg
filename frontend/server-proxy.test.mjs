import test from "node:test";
import assert from "node:assert/strict";
import { buildProxyHeaders, normalizeForwardedFor } from "./server-proxy.mjs";

test("normalizeForwardedFor appends the remote address", () => {
  const request = {
    headers: { "x-forwarded-for": "203.0.113.10" },
    socket: { remoteAddress: "::ffff:192.0.2.25" },
  };

  assert.equal(
    normalizeForwardedFor(request),
    "203.0.113.10, 192.0.2.25"
  );
});

test("buildProxyHeaders preserves the original host by default", () => {
  const request = {
    headers: {
      host: "erp.example.com",
      connection: "keep-alive",
      "proxy-connection": "keep-alive",
    },
    socket: { remoteAddress: "192.0.2.25", encrypted: false },
  };
  const target = new URL("http://backend:8000");

  const headers = buildProxyHeaders(request, target);

  assert.equal(headers.host, "erp.example.com");
  assert.equal(headers["x-forwarded-host"], "erp.example.com");
  assert.equal(headers["x-forwarded-proto"], "http");
  assert.equal(headers["x-forwarded-for"], "192.0.2.25");
  assert.ok(!("connection" in headers));
  assert.ok(!("proxy-connection" in headers));
});

test("buildProxyHeaders can target the upstream host when explicitly requested", () => {
  const request = {
    headers: { host: "erp.example.com" },
    socket: { remoteAddress: "192.0.2.25", encrypted: true },
  };
  const target = new URL("https://otel-collector.internal");

  const headers = buildProxyHeaders(request, target, {
    upstreamHostHeader: true,
  });

  assert.equal(headers.host, "otel-collector.internal");
  assert.equal(headers["x-forwarded-host"], "erp.example.com");
  assert.equal(headers["x-forwarded-proto"], "https");
});
