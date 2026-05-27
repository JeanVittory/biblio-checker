# Step 07 — Tabs and Recent Analyses Integration

## Scope

This step specifies the integration of the new input mode into the existing `/app` page and the Recent Analyses table. It covers:
- Refactor of `apps/frontend/app/app/AppClient.tsx` to host two tabs ("Subir documento" / "Pegar cita")
- Extension of the `StoredJob` type with `inputKind`
- Backwards-compatible reading of pre-existing `localStorage` entries
- A new badge in `RecentAnalyses` distinguishing input modes
- Wiring `addTrackedJob` to accept and persist `inputKind`

This step does NOT cover:
- The input component itself (Step 06)
- i18n keys (Step 08)
- The status polling logic (unchanged from `recent-analyses` suite)

## Context

The current `AppClient.tsx` renders a single uploader vertically:
- Header
- Title + subtitle
- `<FileDropzone>` + Submit/Cancel buttons + `<UploadStatus>`
- `<RecentAnalyses>` below

For this feature, the file uploader and the new `<SingleReferenceForm>` MUST be siblings under a tabs control. The `<RecentAnalyses>` table stays below, shared between modes, with a new badge distinguishing the input kind.

`StoredJob` (the type persisted in `localStorage` under key `biblio-checker:recent-analyses`, schema version 1) currently carries: `jobId`, `jobToken`, `fileName` (display name), `status`, `stage`, `result`, `error`, `submittedAt`, `completedAt`. It does NOT carry an `inputKind` field. Existing entries written by older clients lack this field; the reader MUST default it to `'file'` for backwards compatibility.

## Requirements

### 1) Tabs Control

`AppClient.tsx` MUST render a tabs control between the title block and the `<RecentAnalyses>` section. Two tabs:

| Tab key | Label (i18n key) | Content |
|---------|------------------|---------|
| `upload` | `app.tabs.upload` | Existing file flow (FileDropzone + buttons + UploadStatus) |
| `paste` | `app.tabs.paste` | `<SingleReferenceForm>` |

Implementation choice:
- Reuse an existing component if the project already includes a Tabs primitive (e.g., shadcn/Radix). Check `apps/frontend/components/` first.
- Otherwise, implement a minimal accessible Tabs (two `<button role="tab">` elements + a `role="tabpanel"`). The control MUST support keyboard navigation (Arrow keys to switch).
- The default tab is `upload` (the existing flow remains the primary CTA).
- The selected tab is component-local state (NOT persisted to URL or localStorage in v1).

### 2) Refactor `AppClient.tsx`

The current file flow logic (`handleUpload`, `handleFileSelect`, `handleError`, `handleReset`, `file` state, `uploadState` state) MAY be extracted into a sibling component `<UploadDocumentTab>` to keep `AppClient.tsx` readable. This refactor is NOT required by the spec — keeping everything in `AppClient.tsx` and using the tabs as a JSX-level switch is also acceptable. The implementer chooses based on resulting file length.

`AppClient.tsx` MUST:
- Continue calling `useRecentAnalysesPolling()` once at the top (shared between tabs)
- Pass `addTrackedJob` to BOTH tab contents (file flow already uses it; paste flow uses it via `onJobCreated`)
- Continue rendering `<RecentAnalyses>` below the tabs, OUTSIDE both tabpanels (shared)
- Continue handling the `?sample=1` auto-load flow (file mode only; sample param is ignored in paste mode)

### 3) `addTrackedJob` and `addJob` Signature Extensions

Two functions in two files MUST be updated together:

**(a) `addTrackedJob` in `apps/frontend/hooks/useRecentAnalysesPolling.ts`:**

Before:
```ts
addTrackedJob(jobId: string, jobToken: string, fileName: string): void
```

After:
```ts
addTrackedJob(
  jobId: string,
  jobToken: string,
  displayName: string,
  options?: { inputKind?: "file" | "text"; rawTextPreview?: string }
): void
```

The fourth parameter is an options object. Both keys default appropriately: `inputKind` defaults to `"file"` (backwards-compatible with the 3-arg call sites) and `rawTextPreview` defaults to `undefined` (only set for text-mode jobs).

**(b) `addJob` in `apps/frontend/lib/localStorage/recentAnalyses.ts`** (the storage-layer function that `addTrackedJob` wraps):

`addJob` MUST be extended with the same options object. It writes `inputKind` and (when present) `rawTextPreview` into the persisted `StoredJob`. **This file MUST appear in the Step 09 deliverables checklist.**

The third parameter is renamed conceptually from `fileName` to `displayName`. The underlying `StoredJob.fileName` field is renamed to `StoredJob.displayName` (see § 4); a transparent read-side alias preserves backwards compatibility for entries written by older clients.

### 4) `StoredJob` Type Extension

The `StoredJob` type (`apps/frontend/lib/localStorage/recentAnalyses.ts`) MUST gain TWO new fields:

```ts
type StoredJob = {
  // ...existing fields
  fileName: string;              // KEEP for backwards compatibility on read; new entries write displayName here too
  inputKind: "file" | "text";    // NEW — defaults to "file" on read for legacy entries
  rawTextPreview?: string;       // NEW — present only when inputKind === "text"; capped at 500 chars; used for the row tooltip
  // ...rest
};
```

The persisted schema version MUST remain `1`. Adding two non-required fields with documented defaults does NOT require a schema bump (the `readJobs` function reads each row defensively and fills missing fields).

**Storage budget:** `rawTextPreview` adds up to 500 bytes per text-mode entry. With the existing localStorage cap (current behavior) this is acceptable; `QuotaExceededError` is already handled.

### 5) Backwards-Compatible Read

The localStorage reader (`readJobs`) MUST:
- Treat `inputKind` and `rawTextPreview` as optional in raw data
- Default `inputKind` to `'file'` when missing
- Leave `rawTextPreview` `undefined` when missing
- NOT discard rows that lack either field

The existing `RECENT_ANALYSES_STORAGE_KEY` corruption-detection logic (`AppClient.tsx`) MUST continue to flag truly corrupted rows but MUST NOT flag rows that simply lack the new fields.

### 6) Recent Analyses Badge

`apps/frontend/components/recent-analyses.tsx` MUST display an input-kind badge next to (or above) the `displayName` for each row:

| `inputKind` | Badge | Tooltip / aria-label |
|-------------|-------|----------------------|
| `file` (with `fileName` ending in `.pdf`) | `PDF` | `Documento PDF` |
| `file` (with `fileName` ending in `.docx`) | `DOCX` | `Documento DOCX` |
| `file` (other or undetermined extension) | `Documento` | (generic) |
| `text` | `Texto` | `Cita pegada como texto` |

Visual treatment:
- Small pill, low contrast, secondary color
- MUST NOT obscure the displayName
- MUST be visible on both light and dark themes

The badge text comes from i18n (Step 08). The PDF/DOCX inference is heuristic, derived from the displayName extension; if the heuristic is brittle, the implementer MAY choose to use a single `Documento` label for all `file` jobs and reserve `Texto` for text jobs. Either approach is acceptable for v1.

### 7) Display Name and Tooltip Behavior

For `inputKind='text'` rows:
- `displayName` is the truncated paste (60 chars + ellipsis) supplied by the input component (Step 06)
- The Recent Analyses table MUST render `displayName` as a single-line element with overflow ellipsis
- The hover tooltip MUST show `rawTextPreview` (up to 500 chars). Implementation: set the `title` attribute on the row title element to `rawTextPreview` (when present); falling back to `displayName` when absent
- The tooltip text MUST be rendered exclusively via the native `title` attribute or a React-rendered text node (no `dangerouslySetInnerHTML`)

For `inputKind='file'` rows:
- `displayName` is the original file name, exactly as before
- The hover tooltip MUST show the same `displayName` (no separate preview field exists for file rows)

### 8) Sample Document Flow Compatibility

The `?sample=1` query param flow (auto-load a sample PDF and submit it) MUST continue to work. It is exclusive to the `upload` tab. If the user lands on `/app?sample=1` and the active tab is `paste` (default is `upload`, so this is unlikely), the sample loader MUST switch the active tab to `upload` before triggering the auto-submit.

### 9) Storage Quota Errors

The existing `storageFullError` handling in `AppClient.tsx` (`setStorageFullError(true)` on `QuotaExceededError`) MUST cover both modes. The text mode's `onJobCreated` callback (passed from `AppClient.tsx`) wraps the original `addTrackedJob` so a quota error sets the same `storageFullError` state that the file flow uses. The result: a single banner is shown in `<RecentAnalyses>` regardless of which mode triggered it.

### 10) URL / Routing

No new routes. `/app` continues to be the only entry point; the tabs are component-local UI. Deep-linking to a specific tab is NOT supported in v1 and MAY be added later (e.g., `/app?tab=paste`).

## Acceptance Criteria

- `/app` renders two tabs labeled "Subir documento" and "Pegar cita" (i18n applied)
- Switching tabs preserves the unselected tab's transient state (file selected stays selected; pasted text stays in textarea) UNTIL a successful submission, which clears the active tab's state
- The selected tab visually communicates which is active (style consistent with existing UI)
- Tab navigation via keyboard (Arrow keys, Tab, Enter) works
- Default tab on first load is "Subir documento"
- `<RecentAnalyses>` is visible below the tabs at all times, with rows from both modes intermixed (sorted by `submittedAt` desc, current behavior)
- Each row in `<RecentAnalyses>` displays an input-kind badge (`PDF`, `DOCX`, `Documento`, or `Texto`)
- Existing localStorage entries (without `inputKind`) are read as `inputKind='file'` and rendered with the `Documento` (or `PDF`/`DOCX`) badge
- New text submissions appear with the `Texto` badge
- `addTrackedJob(jobId, jobToken, displayName)` (3-arg call) continues to work and defaults `inputKind` to `'file'`
- Storage quota errors from text submissions surface in the same banner as file submissions
- `/app?sample=1` continues to auto-load and submit the sample PDF in the upload tab

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User has 50 historical jobs in localStorage from before this feature | All render as `file` with the appropriate badge; no migration step required |
| localStorage is corrupted (`storageCorruptedError`) | Existing banner shown; tabs still work |
| User switches tab mid-submission | Active tab's submission continues; unmount safety prevents stale `setState` |
| Tab control library not available | Implement minimal accessible Tabs; document the choice |
| Mobile viewport | Tabs MUST be horizontally aligned and not overflow; if both labels exceed width, abbreviate or stack |
| User submits in upload tab, then submits in paste tab | Both jobs appear in `<RecentAnalyses>`; polling tracks both independently |

## Integration Points

- Step 06 (Input Component) — provides `<SingleReferenceForm>`
- Step 08 (i18n Catalog) — provides all tab labels and badge labels
- `apps/frontend/hooks/useRecentAnalysesPolling.ts` — extend `addTrackedJob` signature and `StoredJob` type
- `apps/frontend/components/recent-analyses.tsx` — add badge rendering
- `apps/frontend/lib/recentAnalyses.ts` (or wherever `readJobs` / `writeJobs` live) — backwards-compatible read of `inputKind`

## Dependencies

- Step 05 (Frontend Gateway) — for the input component to function
- Step 06 (Input Component) — embedded inside the paste tab
- Step 08 (i18n Catalog) — for visible strings
