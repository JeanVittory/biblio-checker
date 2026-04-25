/**
 * Catalog shape invariant test.
 *
 * Asserts that es.json, pt.json, and en.json have:
 *   1. Identical nested key sets.
 *   2. Identical sets of placeholder tokens (e.g. {fileName}, {count}) per key.
 *
 * Run via: pnpm --filter frontend exec vitest run
 */

import { describe, it, expect } from "vitest";
import en from "./en.json";
import es from "./es.json";
import pt from "./pt.json";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Recursively collect all leaf key paths from a nested object. */
function collectKeys(obj: unknown, prefix = ""): string[] {
  if (obj !== null && typeof obj === "object" && !Array.isArray(obj)) {
    return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
      collectKeys(v, prefix ? `${prefix}.${k}` : k)
    );
  }
  return [prefix];
}

/** Extract placeholder tokens (e.g. {fileName}) from an ICU string. */
function extractPlaceholders(value: unknown): Set<string> {
  if (typeof value !== "string") return new Set();
  const matches = value.match(/\{[a-zA-Z_][a-zA-Z0-9_]*(?:,\s*[^}]*)?\}/g) ?? [];
  // Normalize: strip ICU plural body — keep only the bare variable name token.
  return new Set(
    matches
      .map((m) => {
        const inner = m.slice(1, -1).trim();
        const name = inner.split(/[,\s]/)[0].trim();
        return `{${name}}`;
      })
      .filter(Boolean)
  );
}

/** Walk a catalog and return a map of key path → placeholder set. */
function placeholderMap(
  obj: unknown,
  prefix = ""
): Map<string, Set<string>> {
  const result = new Map<string, Set<string>>();
  if (obj !== null && typeof obj === "object" && !Array.isArray(obj)) {
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      const path = prefix ? `${prefix}.${k}` : k;
      if (typeof v === "string") {
        result.set(path, extractPlaceholders(v));
      } else {
        for (const [subPath, placeholders] of placeholderMap(v, path)) {
          result.set(subPath, placeholders);
        }
      }
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

const catalogs: Record<string, unknown> = { en, es, pt };
const enKeys = new Set(collectKeys(en));
const enPlaceholders = placeholderMap(en);

describe("Message catalog shape invariant", () => {
  for (const [locale, catalog] of Object.entries(catalogs)) {
    if (locale === "en") continue;

    it(`${locale}.json has the same key set as en.json`, () => {
      const localeKeys = new Set(collectKeys(catalog));
      const missing = [...enKeys].filter((k) => !localeKeys.has(k));
      const extra = [...localeKeys].filter((k) => !enKeys.has(k));
      expect(missing, `Keys missing in ${locale}.json`).toEqual([]);
      expect(extra, `Extra keys in ${locale}.json not in en.json`).toEqual([]);
    });

    it(`${locale}.json has identical placeholder sets as en.json`, () => {
      const localePlaceholders = placeholderMap(catalog);
      const mismatches: string[] = [];
      for (const [key, enSet] of enPlaceholders) {
        const localeSet = localePlaceholders.get(key);
        if (!localeSet) continue; // key-missing is caught by the shape test above
        const enArr = [...enSet].sort();
        const localeArr = [...localeSet].sort();
        if (JSON.stringify(enArr) !== JSON.stringify(localeArr)) {
          mismatches.push(
            `Key "${key}": en has [${enArr.join(", ")}], ${locale} has [${localeArr.join(", ")}]`
          );
        }
      }
      expect(mismatches, `Placeholder mismatches in ${locale}.json`).toEqual([]);
    });
  }
});

describe("parseAcceptLanguage DoS caps (unit)", () => {
  /**
   * Inline the implementation here so we can test it directly without
   * importing from next/headers (which is server-only and not available
   * in the vitest environment).
   */
  const LOCALES = ["es", "pt", "en"] as const;
  type Locale = (typeof LOCALES)[number];

  function parseAcceptLanguage(header: string): Locale | null {
    const MAX_LEN = 256;
    const MAX_TAGS = 10;
    const safe = header.slice(0, MAX_LEN);
    const entries = safe
      .split(",")
      .slice(0, MAX_TAGS)
      .map((part) => {
        const [tag, ...params] = part.trim().split(";");
        const qParam = params.find((p) => p.trim().startsWith("q="));
        const q = qParam ? parseFloat(qParam.split("=")[1]) : 1.0;
        return { tag: tag.toLowerCase(), q: Number.isFinite(q) ? q : 1.0 };
      })
      .sort((a, b) => b.q - a.q);
    for (const { tag } of entries) {
      const base = tag.split("-")[0];
      if ((LOCALES as readonly string[]).includes(base)) return base as Locale;
    }
    return null;
  }

  it("resolves 'es' to es", () => {
    expect(parseAcceptLanguage("es")).toBe("es");
  });

  it("resolves 'es-MX' to es", () => {
    expect(parseAcceptLanguage("es-MX")).toBe("es");
  });

  it("resolves 'pt-BR' to pt", () => {
    expect(parseAcceptLanguage("pt-BR,pt;q=0.9,en;q=0.8")).toBe("pt");
  });

  it("resolves 'fr' to null (unsupported locale)", () => {
    expect(parseAcceptLanguage("fr")).toBeNull();
  });

  it("resolves empty string to null", () => {
    expect(parseAcceptLanguage("")).toBeNull();
  });

  it("handles a 10000-char header without hanging (resolves quickly)", () => {
    const huge = "fr,".repeat(3334) + "es";
    const start = Date.now();
    const result = parseAcceptLanguage(huge);
    const elapsed = Date.now() - start;
    // MAX_LEN=256 means the huge string is truncated; "es" may not be reached —
    // what matters is it completes almost instantly.
    expect(elapsed).toBeLessThan(100);
    // With a 10000-char header truncated to 256, only "fr" tags appear → null.
    expect(result).toBeNull();
  });

  it("only inspects the first 10 tags even if more are provided", () => {
    // 13 tags, all within MAX_LEN=256: first 10 are 'fr', then 'es' at position 11+.
    // MAX_TAGS=10 means only the first 10 (all fr) are inspected → null.
    const shortTags = "fr,fr,fr,fr,fr,fr,fr,fr,fr,fr,es,es,es";
    const result = parseAcceptLanguage(shortTags);
    expect(result).toBeNull();
  });
});
