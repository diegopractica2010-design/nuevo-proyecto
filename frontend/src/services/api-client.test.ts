import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Import AFTER stubbing global fetch
const { apiClient } = await import("./api-client");

describe("apiClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("fetch", mockFetch);
    // stub localStorage
    vi.stubGlobal("localStorage", { getItem: () => null });
    vi.stubGlobal("window", { localStorage: { getItem: () => null } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("searchProducts builds correct URL params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ count: 0, results: [] }),
    });

    await apiClient.searchProducts({ query: "arroz", store: "lider", limit: 10 }).catch(() => {});

    const url = (mockFetch.mock.calls[0]?.[0] as string) ?? "";
    expect(url).toContain("q=arroz");
    expect(url).toContain("store=lider");
    expect(url).toContain("limit=10");
  });

  it("throws on non-ok response with detail message", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Validation error" }),
    });

    await expect(
      apiClient.searchProducts({ query: "test", store: "lider" })
    ).rejects.toThrow("Validation error");
  });
});
