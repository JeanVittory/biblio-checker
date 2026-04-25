# Step 05 — Sample Document Integration

## Scope

This step specifies the "Try with example" button in the file upload dropzone and how it triggers the sample document flow. It covers:
- Button placement and appearance
- Fetch and file construction logic
- Integration with existing upload flow
- Loading and error states

This step does NOT cover:
- The sample PDF content (see Step 04)
- The upload, analysis, or polling flow (unchanged)
- Changes to the backend or worker

## Context

The `FileDropzone` component (`apps/frontend/components/file-dropzone.tsx`) currently shows an upload icon and prompt text in its empty state. When the user drops a file or clicks the zone, the native file picker opens. The "Try with example" button adds a secondary action that bypasses the file picker and instead fetches a pre-built sample PDF from static assets.

The button MUST trigger the exact same flow as a manually selected file: `onFileSelect(file)` is called with a `File` object, and the existing upload machinery handles the rest.

## Requirements

### 1) Button Placement

The "Try with example" button MUST appear in the dropzone's empty state (when no file is selected). It MUST be placed:
- Below the existing upload prompt text
- Separated by a visual divider or "or" text
- Inside the dropzone container but visually distinct from the drag-and-drop area

### 2) Button Appearance

The button MUST:
- Use the translated label from `dropzone.trySample`
- Display a secondary description from `dropzone.sampleDescription` below or alongside the label
- Be styled as a secondary/link-style action (not a primary button) to avoid competing with the drag-and-drop prompt
- Be visually recognizable as clickable

### 3) Click Behavior

When the user clicks the button:

1. The click event MUST NOT propagate to the dropzone's click handler (which would open the native file picker). The handler MUST call `stopPropagation()` on the event.

2. The button MUST enter a loading state (disabled + visual indicator).

3. The browser MUST fetch the sample PDF from `/samples/sample-references.pdf` via `fetch()`.

4. On successful fetch, the implementation MUST validate the response before constructing the File object:
   - The HTTP response `Content-Type` header MUST be checked. If it is not `application/pdf`, the fetch MUST be treated as a failure.
   - The first 5 bytes of the response Blob MUST be read and verified against the PDF magic bytes (`%PDF-` = `0x25 0x50 0x44 0x46 0x2D`). If they do not match, the fetch MUST be treated as a failure.

5. After validation, the Blob MUST be converted to a `File` object with:
   - Name: `"sample-references.pdf"`
   - MIME type: `"application/pdf"`

6. The `File` object MUST be passed to the `onFileSelect` callback (the same callback used when a user drops or picks a file).

7. The loading state MUST be cleared after `onFileSelect` is called.

### 4) Error Handling

If the fetch fails (network error, 404, etc.):
- The loading state MUST be cleared
- An error MUST be reported via the `onError` callback with a localized message
- The dropzone MUST remain in the empty state (not stuck in loading)
- The user MUST be able to try again or upload their own file

### 5) Disabled State

The button MUST be disabled when:
- The `disabled` prop on `FileDropzone` is `true` (upload already in progress)
- The button is in its loading state (fetch in progress)

### 6) Visibility

The button MUST only appear in the empty state (no file selected). Once a file is selected (either via sample or manual upload), the dropzone transitions to the file-selected state and the button is no longer visible.

### 7) Accessibility

- The button MUST be keyboard accessible (focusable via Tab, activatable via Enter/Space)
- The button MUST have an `aria-label` or visible label that clearly communicates its purpose
- The loading state MUST be announced to screen readers (e.g., via `aria-busy` or a visually hidden status message)

## Acceptance Criteria

- A "Try with example" button is visible in the empty dropzone state
- Clicking the button does NOT open the native file picker
- Clicking the button fetches the sample PDF and passes it to `onFileSelect`
- After the file is selected, the dropzone shows the file name "sample-references.pdf"
- The user can then click Submit to start the analysis (standard flow)
- If fetch fails, an error message is shown and the dropzone returns to empty state
- The button is disabled while the dropzone is disabled (upload in progress)
- The button label updates when the language is changed (EN/ES/PT)
- The button is reachable and activatable via keyboard

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User clicks "Try with example" while offline | Fetch fails; error message shown; dropzone stays in empty state |
| User clicks "Try with example" and then removes the file before submitting | File is removed; dropzone returns to empty state with button visible again |
| User clicks "Try with example" multiple times rapidly | Only the first fetch executes (button is disabled during loading) |
| Sample PDF is missing from static assets (404) | Fetch fails; error message shown; no crash |
| User drops their own file while sample is loading | Behavior is undefined; the `onFileSelect` from the drop may override the sample. This is acceptable. |
| Dropzone is disabled (upload in progress) | Button is disabled; click has no effect |

## Integration Points

- Consumes the sample PDF from Step 04
- Uses `onFileSelect` and `onError` callbacks from the `FileDropzone` component contract (from `spec/recent-analyses/11-upload-flow-integration`)
- Uses i18n keys from Step 09
- After `onFileSelect`, the standard upload flow handles everything (no changes needed)

## Dependencies

- Step 04 (Sample Document) — the PDF file must exist
- Step 09 (i18n Catalog) — provides `dropzone.trySample` and `dropzone.sampleDescription` keys
