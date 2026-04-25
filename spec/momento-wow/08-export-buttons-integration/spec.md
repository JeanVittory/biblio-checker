# Step 08 — Export Buttons Integration

## Scope

This step specifies the UI component that provides CSV and PDF export buttons, and how it integrates into the existing result panel. It covers:
- Button component contract (props, behavior)
- Button placement in the UI
- Loading states during PDF generation
- Dynamic import strategy for PDF library

This step does NOT cover:
- CSV generation logic (see Step 06)
- PDF generation logic (see Step 07)
- The score component (see Step 03)

## Context

Export buttons are the user's entry point to shareability. They appear in the expanded result panel for succeeded jobs, alongside the existing completion timestamp. The CSV button triggers an instant download; the PDF button shows a brief loading state while the document is generated, then triggers the download.

The PDF generation library is heavy (~200-500 KB). To avoid impacting page load performance, it MUST be loaded via dynamic import only when the user clicks the PDF export button.

## Requirements

### 1) Component Contract

The export buttons component MUST accept the following inputs:
- `result` — the `ResultsV1` object from the succeeded job
- `fileName` — the original uploaded file name (e.g., `"thesis_final.pdf"`)

### 2) Button Set

The component MUST render exactly two buttons:
- **CSV button** — labeled with translated text from `results.export.csv`
- **PDF button** — labeled with translated text from `results.export.pdf`

Each button SHOULD include a download icon alongside the text label.

### 3) CSV Button Behavior

When the user clicks the CSV button:
1. The CSV generation function (Step 06) is called synchronously
2. The browser download is triggered immediately
3. No loading state is needed (generation is instant)

### 4) PDF Button Behavior

When the user clicks the PDF button:
1. The button enters a loading state:
   - Button text changes to the translated text from `results.export.generating`
   - A spinner or loading indicator is shown
   - The button is disabled to prevent duplicate clicks
2. The PDF generation library and PDF document component are loaded via dynamic import
3. The PDF document is generated and converted to a Blob
4. The browser download is triggered
5. The loading state is cleared and the button returns to its default state

### 5) PDF Error Handling

If PDF generation fails (library load error, rendering error, memory error):
- The loading state MUST be cleared
- The button MUST return to its default state
- An error indicator SHOULD be shown near the button (e.g., tooltip or brief inline message)
- The page MUST NOT crash or become unresponsive

### 6) Placement

The export buttons component MUST be rendered in the `ExpandedDetail` panel for succeeded jobs, positioned:
- In the footer area of the panel, near the existing completion timestamp
- In a horizontal flex row alongside the timestamp
- Visually secondary to the main result content (smaller buttons, muted style)

### 7) Conditional Rendering

The export buttons MUST only render when:
- The job status is `succeeded`
- The `result` field is not null

When the job is in any other status (queued, running, failed, expired), the export buttons MUST NOT be visible.

### 8) Button Styling

The buttons MUST:
- Be visually consistent with the existing UI (match the surface/border/muted color pattern)
- Be small/compact (text-xs or equivalent) to not dominate the panel
- Have clear hover and focus states
- Include an icon (download/arrow-down) alongside the text

### 9) Accessibility

- Both buttons MUST be keyboard accessible (Tab, Enter/Space)
- Both buttons MUST have descriptive `aria-label` values (e.g., "Export results as CSV", "Export results as PDF")
- The loading state on the PDF button MUST be announced to screen readers (`aria-busy="true"` or equivalent)
- The buttons MUST maintain sufficient color contrast in both light and dark modes

### 10) Dynamic Import Requirements

The PDF generation library MUST NOT be included in the initial JavaScript bundle. It MUST be loaded on demand when the user clicks the PDF button for the first time. Subsequent clicks SHOULD use the cached module (no re-fetch).

This is critical for the "under 60 seconds" first-use experience — the initial page load MUST NOT be impacted by the PDF library size.

## Acceptance Criteria

- Two buttons (CSV + PDF) are visible in the expanded panel of a succeeded job
- Buttons are NOT visible for queued, running, failed, or expired jobs
- Clicking CSV triggers an immediate file download
- Clicking PDF shows a loading state, generates the PDF, and triggers download
- PDF button returns to default state after download completes
- If PDF generation fails, button returns to default state and no crash occurs
- Buttons are positioned near the completion timestamp in the panel footer
- Buttons update their labels when language is changed (EN/ES/PT)
- Buttons are keyboard accessible
- The PDF library is not included in the initial bundle (verifiable via bundle analysis)
- Both buttons work in dark mode and light mode

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User clicks PDF while it's loading | Button is disabled; only one generation runs |
| User clicks CSV and PDF simultaneously | Both downloads trigger independently |
| PDF library fails to load (network error) | Loading state clears; error shown; CSV still works |
| User collapses the detail panel while PDF is generating | Generation continues; download triggers when complete |
| Job has 0 references | CSV downloads header-only file; PDF downloads report with empty references section |
| Very slow PDF generation (> 5 seconds) | Loading spinner remains visible; button stays disabled; generation continues |
| User navigates away during PDF generation | Generation is abandoned; no error; no download |

## Integration Points

- Step 06 (Export CSV) — called by the CSV button click handler
- Step 07 (Export PDF) — the PDF document component is dynamically imported and rendered
- Step 02 (Authenticity Score Formula) — the score computation function is reused for the PDF
- Integrated into `ExpandedDetail` component (from `spec/recent-analyses/10-frontend-ui`)
- Uses i18n keys from Step 09

## Dependencies

- Step 06 (Export CSV) — provides the CSV generation function
- Step 07 (Export PDF) — provides the PDF document component
- Step 09 (i18n Catalog) — provides translated button labels
