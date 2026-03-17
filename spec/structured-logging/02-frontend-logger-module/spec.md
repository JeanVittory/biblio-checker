# Step 02 — Frontend Logger Module

## Scope

**In scope:**

- Install `pino` and `pino-pretty` packages
- Create a centralized logger module at `apps/frontend/lib/logger.ts`
- Handle server-side vs browser-side environments
- Define the child logger convention

**Out of scope:**

- Migrating existing `console.*` calls (Step 03)
- HTTP request logging middleware (not needed for Next.js App Router)
- Log shipping/aggregation configuration

## Context

Next.js bundles code differently for server and browser. The `typeof window === "undefined"` check is replaced at compile time by webpack, enabling tree-shaking of server-only code from client bundles. This means a single logger module can serve both environments safely.

Pino has built-in browser support via the `browser` option, which delegates to native `console.*` methods. On the server side, Pino writes to stdout — JSON by default, or piped through `pino-pretty` in development via the `transport` option.

`pino-http` is **not needed** because Next.js App Router uses plain functions for API routes, not Express middleware.

## Requirements

### R1 — Package installation

Add to `apps/frontend/`:
- `pino` as a production dependency
- `pino-pretty` as a dev dependency

```bash
pnpm --filter frontend add pino
pnpm --filter frontend add -D pino-pretty
```

### R2 — Logger module

**File:** `apps/frontend/lib/logger.ts`

```typescript
import pino from "pino";

const isServer = typeof window === "undefined";
const isDev = process.env.NODE_ENV === "development";

const logger = pino({
  level: isDev ? "debug" : "info",
  ...(isServer
    ? {
        ...(isDev && {
          transport: {
            target: "pino-pretty",
            options: { colorize: true },
          },
        }),
      }
    : {
        browser: {
          asObject: false,
        },
      }),
});

export default logger;
```

**Design decisions:**

| Decision | Rationale |
|---|---|
| Single module, not separate server/browser files | webpack tree-shakes `typeof window` branches at compile time |
| `asObject: false` for browser | Preserves DevTools native formatting (clickable objects, expandable arrays) |
| `transport` for pino-pretty (not `destination`) | `transport` runs in a worker thread, non-blocking; only used in dev |
| No explicit `timestamp` config | Pino includes epoch timestamps by default; pino-pretty formats them |
| `level: "debug"` in dev | Enables debug-level output during development |
| `level: "info"` in prod | Suppresses debug noise in production |

### R3 — Child logger convention

Each consuming module creates a child logger with a `module` field:

```typescript
import logger from "@/lib/logger";
const log = logger.child({ module: "resultsV1" });
```

This produces structured output:
```json
{"level":30,"time":1710000000000,"module":"resultsV1","msg":"Validation failed"}
```

The `module` field replaces the manual `[prefix]` string convention currently used in `console.*` calls.

**Naming convention for `module` values:**

| File Location | Module Name |
|---|---|
| `lib/schemas/resultsV1.ts` | `"resultsV1"` |
| `lib/localStorage/recentAnalyses.ts` | `"recentAnalyses"` |
| `app/page.tsx` | `"home"` |
| `app/api/jobs/status/route.ts` | `"api/jobs/status"` |

## Acceptance Criteria

- [ ] `pino` is listed in `apps/frontend/package.json` dependencies
- [ ] `pino-pretty` is listed in `apps/frontend/package.json` devDependencies
- [ ] `apps/frontend/lib/logger.ts` exists and exports a default Pino logger instance
- [ ] Server-side: produces JSON output in production (no `transport`)
- [ ] Server-side: produces pretty output in development (via `pino-pretty` transport)
- [ ] Browser-side: delegates to `console.*` methods
- [ ] `pnpm --filter frontend exec tsc --noEmit` passes
- [ ] `pnpm lint:frontend` passes

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `pino-pretty` not installed (production) | `transport` block is not included when `isDev` is false, so no error |
| `process.env.NODE_ENV` is undefined | `isDev` is false, logger uses production config (safe default) |
| Module imported in both server and client contexts | Works — webpack tree-shakes the unused branch |
| Multiple `logger.child()` calls in same file | Each gets independent bindings; shared parent level/config |

## Dependencies

- **Step 01** defines the log format and level strategy
- **No dependency on** Python steps (04-08)
