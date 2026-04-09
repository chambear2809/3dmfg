import { render, screen, act } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import ApiErrorToaster from "../ApiErrorToaster";
import { ToastProvider } from "../Toast";
import { emit } from "../../lib/events";

describe("ApiErrorToaster", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    window.history.pushState({}, "", "/admin");
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a toast for network errors without redirecting to login", async () => {
    render(
      <ToastProvider>
        <ApiErrorToaster />
      </ToastProvider>
    );

    act(() => {
      emit("api:error", {
        status: 502,
        message: "upstream request failed: getaddrinfo ENOTFOUND backend",
      });
    });

    expect(
      screen.getByText("Unable to connect to server. Please check your connection.")
    ).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(6000);
    });

    expect(window.location.pathname).toBe("/admin");
  });
});
