# Step 10 — Frontend UI Component

## Scope

This step specifies the user interface for the Recent Analyses table and its interactive elements. It covers:
- Table layout and positioning on the page
- Row structure (columns, badges, buttons)
- Expandable detail panels
- Status badges and visual indicators
- User interactions (expand, collapse, remove)
- Responsive and accessibility considerations

This step does NOT cover:
- React component code or implementation
- CSS styling details (colors, fonts, exact spacing)
- Animation timings or transition properties
- Accessibility API implementation (only requirements)
- Performance optimization techniques
- Integration with the upload form (see Step 11)

## Context

The Recent Analyses table is displayed below the upload form on the same page. It provides a concise summary of all submitted jobs with the ability to drill down into details. The table must be visually distinct from the upload form and should support progressive disclosure (expanding rows to see more information).

## Requirements

1. The table must be positioned below the upload form on the same page (no new routes or navigation).

2. The table must be hidden when there are no jobs (empty state). No placeholder text or "no jobs" message is required (simplicity preferred).

3. When jobs are present, the table must display:
   - One row per job
   - Jobs ordered newest first (most recent submission at the top)
   - A maximum of ~ 50 rows (assume small viewport, no pagination)

4. Each row must display the following information in columns:
   - **File Name:** The original file name (truncated if very long, e.g., "thesis_final_final.pdf" → "thesis_final...")
   - **Submitted:** Relative time (e.g., "Just now", "5m ago", "2h ago", "3d ago")
   - **Status:** A badge showing current job state (queued, running, succeeded, failed, expired)
   - **Actions:** A remove button (trash icon or "Remove" text)
   - **Expand Toggle:** A chevron or arrow icon to expand/collapse the row

5. Status badges must be visually distinct by status:
   - **Queued (Yellow/Gray):** Clock icon, label "Queued"
   - **Running (Blue):** Spinner/loading icon, label "Running"
   - **Succeeded (Green):** Checkmark icon, label "Succeeded"
   - **Failed (Red):** X or warning icon, label "Failed"
   - **Expired (Gray):** Warning icon, label "Expired"

6. When a user clicks the expand toggle (chevron), the row expands to show an additional detail panel below that row.

7. The expanded detail panel must display different content depending on the job status:

   **Status: Queued**
   - "Waiting to be processed..."
   - No additional details

   **Status: Running**
   - Current stage (e.g., "Parsing document", "Validating references", "Analyzing format")
   - Elapsed time since submission (e.g., "Processing for 2 minutes")
   - No result data (job not complete)

   **Status: Succeeded**
   - Result summary or key findings from the analysis (exact format depends on backend; assume JSON with readable fields)
   - "Completed Xm ago" or timestamp
   - Sample result fields: errors found, warnings, citation count, etc. (backend determines)

   **Status: Failed**
   - Error message returned by the backend (e.g., "Unable to parse PDF: corrupted file")
   - "Failed Xm ago" or timestamp
   - No actionable recovery steps required (user can remove and re-upload)

   **Status: Expired**
   - Message: "Token invalid or expired" or "Job no longer accessible"
   - Reason: "This job cannot be accessed anymore (token expired or not found)"
   - Suggestion: "You can remove this entry and re-upload the document if needed"

8. The remove button must be present in every row and must delete that row from the table immediately upon click.

9. Clicking remove must:
   - Remove the job from localStorage via `removeJob()` (Step 07)
   - Stop polling for that job (Step 08)
   - Immediately remove the row from the UI (no confirmation dialog required)

10. Relative time display must follow these rules:
    - < 1 minute: "Just now"
    - 1-59 minutes: "Xm ago" (e.g., "5m ago")
    - 1-23 hours: "Xh ago" (e.g., "2h ago")
    - >= 24 hours: "Xd ago" (e.g., "3d ago")
    - If submission time is in the future (client clock skew): "Just now"

11. The table layout should be responsive:
    - On mobile (< 768px width): Stack columns vertically or simplify to file name + status + remove
    - On desktop (>= 768px width): Display all columns horizontally
    - Truncate file names to fit available space

12. The table should support keyboard navigation (Tab to move between rows, Enter to expand/collapse, Delete to remove — optional but recommended).

13. All interactive elements (status badge, expand toggle, remove button) must have clear hover/focus states.

14. The table header (if visible) should clearly label each column: "File", "Submitted", "Status", "Actions".

15. Page layout: The upload form occupies a narrow central column (e.g., max-width 600px, centered). The Recent Analyses table is displayed below the form in a wider container (e.g., 100% width or max-width 900px, left-aligned or centered).

## User Interactions

### Expand Row
1. User clicks the chevron/arrow icon at the left of a row
2. Row expands to reveal the detail panel
3. Chevron rotates or changes direction to indicate expanded state
4. Clicking again collapses the row

### Remove Row
1. User clicks the remove/trash button on a row
2. Row disappears immediately from the table
3. Job is removed from localStorage
4. If all rows are removed, the table disappears (empty state)

### Monitor Status
1. Every 4 seconds, polling updates the job status (Step 08)
2. If status changes, the badge is updated in the UI
3. If expanded, the detail panel is refreshed with new information
4. User can watch progress in real-time without manual refresh

## Empty State

When there are no jobs in the table:
- The entire Recent Analyses section is hidden (or not rendered)
- The upload form is visible and ready for a new upload
- After upload succeeds, the table reappears with the new job

## Accessibility Requirements

- All interactive elements must be keyboard accessible (Tab, Enter, Space)
- Status badges must have appropriate ARIA labels (e.g., `aria-label="Queued"`)
- Expand/collapse toggle must indicate expanded state (e.g., `aria-expanded="true"`)
- Remove button must have accessible label (e.g., "Remove this job")
- Relative time text should be readable by screen readers (e.g., "5 minutes ago")
- Color should not be the only indicator of status; icons or text labels should also convey meaning
- Table should be marked as a data table with appropriate semantic HTML (`<table>`, `<th>`, `<tr>`, `<td>`)

## Acceptance Criteria

- Table is hidden when no jobs are present
- When jobs are present, table displays rows in newest-first order
- Each row shows file name, submitted time, status badge, and remove button
- Status badges are visually distinct (different colors/icons for each status)
- Expand toggle reveals a detail panel with status-appropriate information
- Remove button deletes the row immediately and updates localStorage
- Relative time is calculated correctly for all ranges (< 1m to days)
- File names longer than ~50 characters are truncated with ellipsis
- Table is responsive on mobile and desktop
- Keyboard navigation is supported (Tab, Enter for expand, keyboard access to remove)
- Polling updates are reflected in the UI (status badge changes, detail panel refreshes)
- Expired or failed jobs remain visible until removed by the user

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User uploads a job and immediately removes the row | Row is removed; polling stops; localStorage is updated |
| Job status changes from running to succeeded while row is expanded | Detail panel updates to show results; badge changes to green |
| Very long file name (e.g., 500 characters) | File name is truncated to fit available space (e.g., "very_long_file_name_2025_final_FINAL_v3_...pdf") |
| User opens two tabs with the Recent Analyses feature | Each tab has its own table with the same localStorage data (localStorage is per-browser, shared across tabs) |
| Job completes while user is viewing the table | Status badge and detail panel update automatically on next polling cycle |
| User removes a job that is still polling | Row is removed immediately; polling stops; no further requests are issued |
| Result payload contains HTML or special characters | Result is escaped/sanitized before rendering (backend should do this, but frontend should not assume) |
| Submitted time is in the future (client clock skew) | Relative time shows "Just now" to avoid negative times or confusion |
| Screen is very narrow (< 320px) | File name is heavily truncated; columns may stack; table remains readable |

## Layout Specification

**Conceptual Layout:**

```
[Upload Form (narrow, centered)]
  - Input field
  - Submit button

[Recent Analyses Table (full width or wider than form)]
  - Row 1: File A, Just now, Running, [Expand], [Remove]
    - Expanded: Processing for 30s...
  - Row 2: File B, 5m ago, Succeeded, [Expand], [Remove]
    - Expanded: Results shown here
  - Row 3: File C, 2h ago, Failed, [Expand], [Remove]
    - Expanded: Error message shown here
```

## Visual Hierarchy

- File name: Primary text (large, bold)
- Status badge: Prominent (color-coded, icon + text)
- Submitted time: Secondary text (smaller, lighter color)
- Detail panel: Expanded content with clear hierarchy (stage, results, errors, timestamps)

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| < 768px | Mobile: Stack columns, simplify detail panel, larger touch targets |
| >= 768px | Desktop: Horizontal columns, full detail panel, standard spacing |
| >= 1200px | Wide: Increased padding/margins, improved readability |

## Dependencies

- Depends on Step 07 (Frontend Data Model) for `StoredJob` structure
- Depends on Step 08 (Frontend Polling) for real-time status updates
- Renders data from localStorage (Step 07)
- Calls `removeJob()` helper (Step 07) when user removes a row
- Triggers polling updates via polling mechanism (Step 08)
- Calls the status endpoint via proxy route (Step 09)
- Integrates with upload flow (Step 11) to add new rows
