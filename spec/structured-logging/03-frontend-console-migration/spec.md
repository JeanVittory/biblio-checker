# Step 03 — Frontend Console Migration

## Scope

**In scope:**

- Replace all 5 existing `console.*` calls with Pino logger calls
- Apply the child logger convention from Step 02

**Out of scope:**

- Adding new logging points beyond the existing 5 calls
- Modifying error handling logic
- Adding HTTP request logging

## Context

There are exactly 5 `console.*` calls across 4 files in the frontend. Each currently uses a manual `[prefix]` string for context. The migration replaces these with structured Pino logger calls using child loggers with a `module` field.

## Requirements

### R1 — `apps/frontend/lib/schemas/resultsV1.ts` (line 187)

**Current:**
```typescript
console.error("[resultsV1] Validation failed:", parsed.error.issues);
```

**New — add at top of file:**
```typescript
import logger from "@/lib/logger";
const log = logger.child({ module: "resultsV1" });
```

**New — replace line 187:**
```typescript
log.error({ issues: parsed.error.issues }, "Validation failed");
```

**Notes:**
- The `issues` array is passed as a structured field, not concatenated into the message string
- This file is imported by both server and client code — the logger handles both transparently

### R2 — `apps/frontend/lib/localStorage/recentAnalyses.ts` (line 91)

**Current:**
```typescript
console.warn(
  "[recentAnalyses] localStorage data is corrupted or has an unsupported schema version. Returning empty list."
);
```

**New — add at top of file:**
```typescript
import logger from "@/lib/logger";
const log = logger.child({ module: "recentAnalyses" });
```

**New — replace line 91:**
```typescript
log.warn("localStorage data is corrupted or has an unsupported schema version; returning empty list");
```

**Notes:**
- This file is browser-only (guarded by `typeof window` checks)
- The browser logger emits this via `console.warn` under the hood

### R3 — `apps/frontend/app/page.tsx` (lines 255, 267)

**Current (line 255):**
```typescript
console.warn("Upload succeeded but job tracking failed: missing jobId or jobToken");
```

**Current (line 267):**
```typescript
console.warn("Upload succeeded but job tracking failed:", trackingError);
```

**New — add at top of file (after existing imports):**
```typescript
import logger from "@/lib/logger";
const log = logger.child({ module: "home" });
```

**New — replace line 255:**
```typescript
log.warn("Upload succeeded but job tracking failed: missing jobId or jobToken");
```

**New — replace line 267:**
```typescript
log.warn({ err: trackingError }, "Upload succeeded but job tracking failed");
```

**Notes:**
- `err` is a Pino convention key — Pino's default serializer automatically extracts `message`, `stack`, and `type` from Error objects
- Both calls share the same `log` child logger instance

### R4 — `apps/frontend/app/api/jobs/status/route.ts` (line 51)

**Current:**
```typescript
console.error("[jobs/status] BIBLIO_BACKEND_CHECK_URL is not configured.");
```

**New — add at top of file:**
```typescript
import logger from "@/lib/logger";
const log = logger.child({ module: "api/jobs/status" });
```

**New — replace line 51:**
```typescript
log.error("BIBLIO_BACKEND_CHECK_URL is not configured");
```

**Notes:**
- This file is server-only (API route). The server logger writes JSON to stdout in production.

## Acceptance Criteria

- [ ] Zero `console.log`, `console.warn`, or `console.error` calls remain in the frontend codebase
- [ ] All 4 modified files import from `@/lib/logger`
- [ ] All 4 modified files create a child logger with appropriate `module` name
- [ ] Structured data (like `issues`, `err`) is passed as first-arg object, not concatenated
- [ ] `pnpm --filter frontend exec tsc --noEmit` passes
- [ ] `pnpm lint:frontend` passes
- [ ] `pnpm --filter frontend exec vitest run` passes
- [ ] No error handling logic is changed — only the logging mechanism

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `trackingError` is not an Error instance (e.g., string) | Pino serializes it as-is in the `err` field |
| `parsed.error.issues` is a large array | Pino serializes the full array — no truncation (JSON is machine-consumed) |
| Test mocks `console.warn` | Tests may need updating if they assert on `console.warn` calls |

## Dependencies

- **Step 02** must be implemented first (logger module must exist)
- **No dependency on** Python steps
