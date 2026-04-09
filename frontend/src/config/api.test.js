import { describe, expect, it } from "vitest";
import { resolveApiUrl } from "./api";

describe("resolveApiUrl", () => {
  it("prefers runtime config when provided", () => {
    expect(
      resolveApiUrl({
        runtimeUrl: " http://api.example.com/ ",
        viteUrl: "http://fallback.example.com",
      })
    ).toBe("http://api.example.com");
  });

  it("falls back to the Vite env URL when runtime config is empty", () => {
    expect(
      resolveApiUrl({
        runtimeUrl: "",
        viteUrl: "http://localhost:8000/",
      })
    ).toBe("http://localhost:8000");
  });

  it("defaults to same-origin in development", () => {
    expect(resolveApiUrl({ isDev: true })).toBe("");
  });

  it("defaults to same-origin in production when no explicit URL is set", () => {
    expect(resolveApiUrl()).toBe("");
  });
});
