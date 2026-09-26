/**
 * Public platform info accessors (Phase 13.6) — the anonymous subset of
 * PlatformSettings the storefront chrome renders (PROJECT_CONTEXT §6
 * v1.13). Covers the mapping, the default fallback, and the endpoint it
 * calls; no CSRF is needed on a GET.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchPlatformInfo, mapPlatformInfo } from "./platform";

function mockFetch(payload, { ok = true, status = ok ? 200 : 500 } = {}) {
  const fetchMock = vi.fn(async () => ({
    ok,
    status,
    json: async () => payload,
  }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("public platform info accessors (13.6)", () => {
  it("maps the public subset", () => {
    expect(
      mapPlatformInfo({
        platform_name: "Jeyvro PH",
        support_email: "help@jeyvro.ph",
      })
    ).toEqual({
      platformName: "Jeyvro PH",
      supportEmail: "help@jeyvro.ph",
    });
  });

  it("falls back to the built-in default when fields are missing", () => {
    expect(mapPlatformInfo({})).toEqual({
      platformName: "Jeyvro",
      supportEmail: "",
    });
  });

  it("fetches the anonymous endpoint", async () => {
    const fetchMock = mockFetch({
      platform_name: "Jeyvro",
      support_email: "support@jeyvro.com",
    });
    const info = await fetchPlatformInfo();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/platform/public/");
    expect(info.platformName).toBe("Jeyvro");
    expect(info.supportEmail).toBe("support@jeyvro.com");
  });
});
