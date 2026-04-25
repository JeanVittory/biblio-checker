# Step 11 — Sample Query Parameter

## Scope

This step specifies the `?sample=1` URL parameter on the `/app` route. When present, the page automatically triggers the "Try with example" flow from FileDropzone, fetching the sample PDF and starting an analysis without user interaction.

## Context

The landing page's secondary CTA "See demo with example" points to `/app?sample=1`. Without this step, visitors who click that CTA would land on `/app` and still need to click "Try with example" inside the FileDropzone. The query parameter eliminates that extra click, delivering the "60-second demo" promise.

## Requirements

### 1) Handler Location

Modify: `apps/frontend/app/app/page.tsx` (the moved file from Step 02)

Add a client-side effect that runs once on mount, checks for the `sample=1` query parameter, and triggers the sample flow.

### 2) Behavior

On page mount:
1. Read the current URL's query parameters (via `useSearchParams()`)
2. If `sample` parameter equals `"1"`:
   - Call the shared utility `fetchSampleDocument()` (defined in Step 11 §4)
   - This utility fetches the hardcoded path `/samples/sample-references.pdf`, validates Content-Type and PDF magic bytes, and returns a `File` object
   - Pass the resulting `File` to the page's existing state setter. In `app/app/page.tsx` this is the `handleFileSelect` handler (which internally calls `setFile`). NOT a `onFileSelect` prop — that's the FileDropzone's prop name, not available in page scope.
3. If the sample parameter is absent or not `"1"`:
   - No action; page behaves normally

### 2.1) Hardcoded Fetch Target (Security)

The fetch target MUST be the compile-time literal string `/samples/sample-references.pdf`. It MUST NOT be derived from any query parameter value. A constant in `apps/frontend/lib/constants.ts` like:
```
export const SAMPLE_DOCUMENT_PATH = "/samples/sample-references.pdf" as const;
```
SHOULD be referenced by both `FileDropzone` and the page effect. This prevents future scope creep where `?sample=<url>` could be misinterpreted as a URL parameter, opening SSRF risk.

### 3) URL Cleanup

The page MUST use `history.replaceState` to remove the `sample=1` parameter from the URL. The cleanup MUST run **synchronously on param detection** (before the async fetch begins), so:
- Back-navigation restores the clean URL regardless of fetch outcome
- A mid-flight failure does not leave the `?sample=1` parameter visible while the user sees an error
- Browser session restoration does not re-trigger the flow

### 4) Re-use of Sample Logic

The fetch + validation logic (Content-Type check + PDF magic bytes) MUST match the existing implementation in `FileDropzone.tsx`. Consider extracting the fetch logic into a shared utility (`apps/frontend/lib/sampleDocument.ts`) to avoid duplication:
- `fetchSampleDocument(): Promise<File>`
- Throws on validation failure
- Used by both FileDropzone and the page.tsx effect

### 5) Error Handling

If the sample fetch fails (network, validation, etc.):
- Show the same error feedback that FileDropzone uses (`onError` callback with localized message)
- URL cleanup: if implemented, still remove the `?sample=1` parameter so subsequent user actions don't get blocked

### 6) Auto-submit (Required)

After the sample file is loaded, the page MUST auto-submit to start the analysis immediately. This delivers the "60-second demo" promise of the secondary CTA.

**Race condition resolution:** `setState` is asynchronous in React. Calling `setFile(file)` then `handleUpload()` in sequence will read stale state (`file === null`). The implementation MUST use one of these patterns:

**Pattern A (preferred)** — Use a `useEffect` that watches the `file` state and a trigger flag:
```
const [shouldAutoSubmit, setShouldAutoSubmit] = useState(false);

// On mount, if ?sample=1:
//   fetch sample → setFile(file) + setShouldAutoSubmit(true)

useEffect(() => {
  if (shouldAutoSubmit && file !== null) {
    handleUpload();
    setShouldAutoSubmit(false);
  }
}, [shouldAutoSubmit, file]);
```

**Pattern B** — Pass the file directly to a refactored upload function that accepts the file as a parameter (avoiding state read entirely).

Either pattern resolves the race; direct sequential `setFile(file)` + `handleUpload()` is INCORRECT and MUST NOT be used.

### 7) No Effect on `/app` Without Query Param

The existing `/app` page behavior MUST NOT be affected when `?sample=1` is absent. Normal upload flow works as before.

### 8) Re-entry Protection

Use `useRef` (NOT `useState`) to ensure the sample loading triggers only once per mount. `useRef` is required specifically because:
- React Strict Mode in development intentionally double-mounts components; `useState` boolean flags reset on the second mount, re-triggering the fetch. `useRef` survives this cycle within the same mount.
- The guard resets on genuine route remount (navigate away + back) — this is acceptable because URL cleanup from §3 prevents the re-trigger in that case.

## Acceptance Criteria

- Navigating to `/app?sample=1` automatically loads the sample PDF into the dropzone
- If auto-submit is implemented, the analysis starts automatically
- Navigating to `/app` (no query param) shows the empty dropzone as before
- Manually clicking "Try with example" still works
- Error during sample fetch shows the same error UI as the manual flow
- Sample is loaded only once per page mount (no duplicate fetches)
- TypeScript compiles without errors

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User refreshes `/app?sample=1` | Re-triggers sample load (or cleaned URL prevents re-trigger, depending on implementation) |
| User clicks "Try with example" AFTER arriving via `?sample=1` | Replaces the current sample file with a new fetch (or is a no-op since file is already selected) |
| User is mid-upload and navigates back to `/app?sample=1` | Current upload continues; sample does not disrupt |
| Sample PDF returns 404 | Error displayed; user can upload their own file |

## Integration Points

- Step 04 (Hero Section) — hero's secondary CTA uses `/app?sample=1`
- Step 10 (Final CTA) — final CTA's secondary button uses `/app?sample=1`
- Reuses sample fetch logic from `apps/frontend/components/file-dropzone.tsx`
- Modifies `apps/frontend/app/app/page.tsx` (moved in Step 02)

## Dependencies

- Step 02 (Routing Restructure) — `/app/page.tsx` must exist
- Existing sample PDF at `apps/frontend/public/samples/sample-references.pdf`
