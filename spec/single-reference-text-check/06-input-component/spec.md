# Step 06 — Input Component

## Scope

This step specifies the React component that lets the user paste a single reference and submit it. It covers:
- Component contract (props, internal state)
- Visual elements (textarea, counter, submit, status feedback)
- Validation (client-side, mirrored from the schema)
- Integration with `useRecentAnalysesPolling` for tracking

This step does NOT cover:
- The tabs that host this component (Step 07)
- The Recent Analyses badge (Step 07)
- i18n keys (Step 08)
- The gateway route (Step 05)

## Context

The file flow in `apps/frontend/app/app/AppClient.tsx` uses `<FileDropzone>`, `<UploadStatus>`, and a complex `handleUpload` callback that orchestrates `signedUploadService → uploadFileService → startAnalysisGatewayService → addTrackedJob`. The text flow is dramatically simpler: there is no upload, no signed URL, no SHA-256, no cleanup. A single service call (`startTextAnalysisGatewayService`) and a tracking call (`addTrackedJob`) cover the full happy path.

## Requirements

### 1) Component Location and Name

- File: `apps/frontend/components/single-reference-form.tsx`
- Default export: `SingleReferenceForm` (named export also acceptable per project convention)
- The component MUST be a Client Component (`"use client"`)

### 2) Props

```ts
interface SingleReferenceFormProps {
  onJobCreated: (
    jobId: string,
    jobToken: string,
    displayName: string,
    rawTextPreview: string
  ) => void;
  disabled?: boolean;     // upload-locked / feature-flag locked
}
```

`displayName` is the truncated 60-char label shown as the row title in `<RecentAnalyses>`. `rawTextPreview` is the trimmed full text capped at 500 chars (without ellipsis appended) and is used by the parent to populate `StoredJob.rawTextPreview` so the row can display a tooltip with the full citation. The 500-char cap is a UX/storage-cost compromise — long enough for almost any single citation, short enough to keep `localStorage` writes cheap.

The parent (Step 07) passes `addTrackedJob` (or a wrapper around it) via `onJobCreated`. This keeps the component agnostic of the storage layer and easy to test in isolation.

### 3) Internal State

```ts
type SubmitStatus =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success" }
  | { kind: "error"; message: string };

const [text, setText] = useState<string>("");
const [status, setStatus] = useState<SubmitStatus>({ kind: "idle" });
```

After a successful submission, the form MUST clear `text` to empty string and reset `status` to `idle` (so the user can submit another reference without page reload). The success toast / banner MAY remain briefly (e.g., 2 seconds) before disappearing.

### 4) Visual Elements

The component MUST render, in this order:

1. **Label** — i18n key `paste.label` (e.g., "Pega tu cita bibliográfica")
2. **Textarea** — multi-line input
   - Min height: enough for ~4 lines (responsive)
   - `placeholder`: i18n key `paste.placeholder` (a short example reference)
   - `value`: bound to `text` state
   - `onChange`: updates `text`
   - `disabled` when `props.disabled === true` OR `status.kind === "submitting"`
   - `maxLength={2000}` (browser hard cap, matches schema)
   - Visible character counter rendered below: `{trimmedLength} / 2000`
3. **Inline validation hint** (only shown after first submit attempt with invalid input):
   - If trimmed length < 20 → i18n key `paste.too_short`
   - If trimmed length > 2000 → unreachable (textarea maxLength prevents it) but defense-in-depth: `paste.too_long`
   - If empty after trim → i18n key `paste.empty`
4. **Submit button** — i18n key `paste.submit`
   - `disabled` when `props.disabled` OR `status.kind === "submitting"` OR trimmed text length < 20
   - On click: triggers submission flow (§ 5)
5. **Status banner** — same style as `UploadStatus` (reuse design tokens):
   - `submitting`: spinner + i18n key `paste.submitting`
   - `success`: checkmark + i18n key `paste.success`
   - `error`: error icon + `status.message`

### 5) Submission Flow

When the user clicks Submit:

1. Trim `text`. If trimmed length < 20 or > 2000, set `status` to error with the appropriate i18n message and return (no network call)
2. Set `status` to `submitting`
3. Generate `requestId = crypto.randomUUID()`
4. Build payload:
   ```
   { requestId, reference: { rawText: <trimmed text> } }
   ```
5. Call `startTextAnalysisGatewayService(payload)` (defined in Step 05)
6. On non-OK HTTP response or `ok: false`: set `status` to error with i18n message `paste.submit_failed` (network) or `paste.backend_error` (4xx/5xx with backend's safe message)
7. On OK response:
   - Extract `backend.jobId` and `backend.jobToken`; if either is missing, treat as backend error
   - Let `trimmed = text.trim()` (single source of truth for downstream values; never use the raw `text` state)
   - Compute `displayName`: `trimmed.length > 60 ? trimmed.slice(0, 60) + "…" : trimmed`
   - Compute `rawTextPreview`: `trimmed.slice(0, 500)` (no ellipsis; cap is a hard slice)
   - Call `props.onJobCreated(jobId, jobToken, displayName, rawTextPreview)` inside a `try/catch`:
     - On `QuotaExceededError` (DOMException): set `status` to error with i18n `paste.storage_full`
     - On other errors: set `status` to success anyway (the submission succeeded; tracking is non-fatal). Log via the project Pino child logger
   - Set `status` to `success`
   - Clear `text` to empty string immediately after `onJobCreated` succeeds. The success banner remains visible for at least 2 seconds (managed by the banner's own animation/timeout), independent of `text` clearing. This deterministic ordering avoids the "did my paste actually go through?" perception bug.

### 6) Accessibility

- Textarea MUST have an associated `<label>` (or `aria-labelledby`) referencing `paste.label`
- Submit button MUST have an accessible name (the visible text suffices)
- Status banner MUST use `role="status"` and `aria-live="polite"`
- Validation hints MUST be linked to the textarea via `aria-describedby`
- The form MUST be navigable via keyboard alone (Tab to textarea, Tab to submit)
- Disabled states MUST set `aria-disabled` correctly

### 7) Styling

- Reuse existing design tokens (`--accent`, `--accent-secondary`, `--border`, `--surface`, etc.) from the file flow
- Match the visual language of `<FileDropzone>` and `<UploadStatus>` so both tabs feel consistent
- Submit button uses the same gradient style as the existing "Subir" button (`linear-gradient(135deg, var(--accent), var(--accent-secondary))`)
- No new CSS files; use Tailwind utility classes (project standard)

### 7a) XSS / Render Safety (MANDATORY)

`displayName` and `rawTextPreview` are derived from untrusted user input. Every render site for these values — in this component AND in `<RecentAnalyses>`, `<ExpandedDetail>`, and the share-link view — MUST render them exclusively as React text nodes (e.g., `<span>{displayName}</span>`, `title={rawTextPreview}`). The implementation MUST NOT pass either value to `dangerouslySetInnerHTML`, `innerHTML`, or any equivalent escape-bypass primitive. A code comment at each render site SHOULD note: `// User-supplied; React text-node escaping is the only XSS defense.`

### 8) Service: `startTextAnalysisGatewayService`

This step also specifies the client-side service consumed by the component:

- File: `apps/frontend/services/startTextAnalysisGateway.ts`
- Signature:
  ```ts
  export async function startTextAnalysisGatewayService(
    payload: TextReferenceCheckPayload
  ): Promise<Response>
  ```
- Behavior: `fetch("/api/analysis-text-gateway", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload) })`
- Returns the raw `Response` object (mirroring `startAnalysisGatewayService`); the component is responsible for parsing JSON and inspecting `ok`

### 9) No localStorage Drafts

The component MUST NOT persist the typed text to `localStorage`. If the user reloads, the textarea is empty. This matches the file flow (the user re-selects the file). Drafts are out of scope.

### 10) Form Reset on Tab Switch

The component's state lives inside the component instance. When the parent (Step 07) hides this tab, React unmounts it (or keeps it mounted, depending on the tabs implementation). Either is acceptable as long as switching back does NOT submit a stale request. The `submitting` status MUST be torn down on unmount (use a `mounted` ref / abort controller pattern).

## Acceptance Criteria

- The component renders a textarea, character counter, submit button, and status banner
- Submit button is disabled when trimmed text length < 20
- Submit button is disabled while `status === "submitting"`
- Submitting valid text calls `startTextAnalysisGatewayService` once with `requestId`, trimmed `rawText`
- On success, `onJobCreated(jobId, jobToken, displayName)` is called with `displayName` derived from the first 60 chars of the input
- After success, the textarea is cleared and the form is ready for another submission
- On validation failure, no network call is made and an i18n hint is shown
- On `QuotaExceededError` from `onJobCreated`, the form shows the storage-full error i18n message
- The component is fully keyboard-accessible
- Switching tabs while submitting does not crash or fire stale `setState` calls

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User pastes 5000 chars | Textarea hard-caps at 2000 via `maxLength`; counter shows `2000 / 2000`; no client-side error |
| User submits then immediately switches tab | If the component unmounts, the in-flight fetch is allowed to complete but state updates are skipped (mounted-ref pattern). If the component stays mounted (tab persistence), it shows success on return |
| Network is offline | Fetch rejects; form shows `paste.submit_failed` |
| Backend returns 400 with a safe message | Form shows that message verbatim (the gateway already sanitized it) |
| User pastes text containing newlines | Newlines counted toward the 2000 limit; preserved exactly when sent to backend |
| User rapidly clicks Submit twice | Second click is a no-op because the button is disabled while `submitting`; the form MUST NOT issue duplicate requests |
| `crypto.randomUUID()` is unavailable (very old browsers) | Fall back to a polyfill or a small inline UUID v4 generator. Project supports modern browsers per `apps/frontend/AGENTS.md`; document any fallback in the code |

## Integration Points

- Step 05 (Frontend Gateway) — backend recipient via fetch
- Step 07 (Tabs & Recent Analyses) — parent that wires `onJobCreated` to `addTrackedJob`
- Step 08 (i18n Catalog) — provides all visible strings
- `apps/frontend/components/upload-status.tsx` — visual reference for the status banner
- `apps/frontend/lib/schemas/bibliographyCheck.ts` — provides `TextReferenceCheckPayload` type

## Dependencies

- Step 05 (Frontend Gateway)
- Step 08 (i18n Catalog) for visible strings
