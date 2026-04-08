import { describe, expect, it } from "vitest";

import {
  buildRumExporterOptions,
  normalizeRoutePath,
  sanitizeRumAttributes,
} from "./browserTracing";

describe("normalizeRoutePath", () => {
  it("normalizes dynamic admin and token-bearing routes", () => {
    expect(normalizeRoutePath("/admin/orders/12345")).toBe(
      "/admin/orders/:orderId"
    );
    expect(normalizeRoutePath("/admin/production/PO-9")).toBe(
      "/admin/production/:orderId"
    );
    expect(normalizeRoutePath("/reset-password/abc123")).toBe(
      "/reset-password/:token"
    );
    expect(normalizeRoutePath("/admin/password-reset/approve/secrettoken")).toBe(
      "/admin/password-reset/:action/:token"
    );
  });

  it("leaves stable routes unchanged", () => {
    expect(normalizeRoutePath("/admin/orders/import")).toBe(
      "/admin/orders/import"
    );
    expect(normalizeRoutePath("/admin/dashboard")).toBe("/admin/dashboard");
  });
});

describe("sanitizeRumAttributes", () => {
  it("removes query strings and normalizes route-like attributes", () => {
    const attributes = {
      "http.url":
        "https://filaops.example.com/admin/orders/12345?token=secret#frag",
      "http.route": "/admin/password-reset/approve/secrettoken?debug=true",
      untouched: "keep-me",
    };

    sanitizeRumAttributes(attributes);

    expect(attributes["http.url"]).toBe(
      "https://filaops.example.com/admin/orders/:orderId"
    );
    expect(attributes["http.route"]).toBe(
      "/admin/password-reset/:action/:token"
    );
    expect(attributes.untouched).toBe("keep-me");
  });
});

describe("buildRumExporterOptions", () => {
  it("builds direct export without OTLP flags", () => {
    const exporter = buildRumExporterOptions("direct");

    expect(exporter.otlp).toBeUndefined();
    expect(exporter.beaconEndpoint).toBeUndefined();
    expect(typeof exporter.onAttributesSerializing).toBe("function");
  });

  it("builds OTLP export when explicitly requested", () => {
    const exporter = buildRumExporterOptions("otlp", "/otel/v1/traces");

    expect(exporter.otlp).toBe(true);
    expect(exporter.beaconEndpoint).toBe("/otel/v1/traces");
    expect(typeof exporter.onAttributesSerializing).toBe("function");
  });
});
