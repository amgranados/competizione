import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { usePolling } from "../../src/hooks/usePolling.js";

describe("usePolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("invokes fetcher immediately on mount", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    const { result } = renderHook(() => usePolling(fetcher, 10000));

    expect(fetcher).toHaveBeenCalledTimes(1);
    await vi.runOnlyPendingTimersAsync();
    expect(result.current.data).toEqual({ ok: true });
  });

  it("calls fetcher again every intervalMs", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    renderHook(() => usePolling(fetcher, 10000));

    expect(fetcher).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(fetcher).toHaveBeenCalledTimes(2);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  it("clears the interval on unmount", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    const { unmount } = renderHook(() => usePolling(fetcher, 10000));
    expect(fetcher).toHaveBeenCalledTimes(1);
    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("exposes refresh() to force an immediate fetch", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });
    const { result } = renderHook(() => usePolling(fetcher, 10000));
    expect(fetcher).toHaveBeenCalledTimes(1);
    await act(async () => {
      await result.current.refresh();
    });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("captures fetcher errors without throwing", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => usePolling(fetcher, 10000));
    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error.message).toBe("boom");
  });
});
