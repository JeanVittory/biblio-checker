import { describe, it, expect, vi } from "vitest";

// We test the locale injection logic in isolation rather than mounting the full route handler,
// since Next.js server internals (cookies(), supabase, crypto) are not available in vitest.

describe("Gateway locale injection logic", () => {
  it("normalizeLocale returns default locale for null", async () => {
    const { normalizeLocale } = await import("@/i18n/config");
    expect(normalizeLocale(null)).toBe("es");
  });

  it("normalizeLocale returns 'pt' for 'pt-BR'", async () => {
    const { normalizeLocale } = await import("@/i18n/config");
    expect(normalizeLocale("pt-BR")).toBe("pt");
  });

  it("normalizeLocale returns 'en' for 'en-US'", async () => {
    const { normalizeLocale } = await import("@/i18n/config");
    expect(normalizeLocale("en-US")).toBe("en");
  });

  it("normalizeLocale returns default locale for unknown value", async () => {
    const { normalizeLocale } = await import("@/i18n/config");
    expect(normalizeLocale("fr")).toBe("es");
  });

  it("LOCALE_COOKIE is NEXT_LOCALE", async () => {
    const { LOCALE_COOKIE } = await import("@/i18n/config");
    expect(LOCALE_COOKIE).toBe("NEXT_LOCALE");
  });
});

describe("startAnalysisService — Accept-Language forwarding", () => {
  it("forwards accept-language header when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    const { startAnalysisService } = await import("@/services/startAnalysis");

    const payload = {
      requestId: "00000000-0000-0000-0000-000000000001",
      extractMode: "backend_extract_references" as const,
      document: {
        sourceType: "pdf" as const,
        fileName: "test.pdf",
        mimeType: "application/pdf" as const,
      },
      storage: {
        provider: "supabase" as const,
        bucket: "uploads",
        path: "uploads/test.pdf",
      },
      integrity: { sha256: "a".repeat(64) },
      locale: "pt",
    };

    await startAnalysisService("http://backend", payload, "pt-BR,pt;q=0.9");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          "accept-language": "pt-BR,pt;q=0.9",
        }),
      })
    );

    vi.unstubAllGlobals();
  });

  it("does not set accept-language header when not provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    const { startAnalysisService } = await import("@/services/startAnalysis");

    const payload = {
      requestId: "00000000-0000-0000-0000-000000000002",
      extractMode: "backend_extract_references" as const,
      document: {
        sourceType: "pdf" as const,
        fileName: "test.pdf",
        mimeType: "application/pdf" as const,
      },
      storage: {
        provider: "supabase" as const,
        bucket: "uploads",
        path: "uploads/test.pdf",
      },
      integrity: { sha256: "b".repeat(64) },
    };

    await startAnalysisService("http://backend", payload);

    const callArgs = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = callArgs.headers as Record<string, string>;
    expect("accept-language" in headers).toBe(false);

    vi.unstubAllGlobals();
  });
});
