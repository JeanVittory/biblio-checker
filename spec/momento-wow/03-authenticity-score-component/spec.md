# Step 03 — Authenticity Score Component

## Scope

This step specifies the frontend component that visually renders the Authenticity Score. It covers:
- Visual design and layout
- Color semaphore mapping
- Placement within the existing result panel
- Accessibility requirements
- Responsive behavior

This step does NOT cover:
- The score computation algorithm (see Step 02)
- The score's appearance in the PDF export (see Step 07)
- Modifications to the ExpandedDetail layout beyond inserting the score

## Context

The Authenticity Score component is the centerpiece of the "Momento Wow" experience. It provides the instant visual verdict that answers "is this bibliography trustworthy?" at a glance. The component is inserted into the existing `ExpandedDetail` panel for succeeded jobs, between the summary counts and the classification breakdown.

## Requirements

### 1) Component Contract

The component MUST accept the following input:
- `countsByClassification` — the object from `ResultsV1.summary.countsByClassification`

The component MUST internally call the score computation function (Step 02) and render the result.

### 2) Visual Layout

The component MUST display:
- A prominent score number (0-100) as the primary visual element
- A band label translated via i18n: `results.score.high`, `results.score.medium`, or `results.score.low`
- A section title translated via i18n: `results.score.title`
- A visual container (card) that matches the existing surface/border pattern used in `ExpandedDetail`

The score number MUST be the largest text element within the component, visually dominating the card.

### 3) Color Semaphore

The component MUST apply a color to the score number and/or card border based on the band:

| Band | Color Intent | Description |
|------|-------------|-------------|
| `high` | Green | Positive, trustworthy — most references verified |
| `medium` | Amber/Yellow | Caution, needs review — mixed results |
| `low` | Red | Warning, low authenticity — many unverified or suspicious |

Color MUST NOT be the only indicator. The band label text ("High authenticity", "Needs review", "Low authenticity") MUST also be visible.

### 4) Placement

The component MUST be rendered in the `ExpandedDetail` panel for succeeded jobs, positioned:
- AFTER the 2-column summary grid (detected/analyzed counts)
- BEFORE the classification breakdown box

### 5) Conditional Rendering

The component MUST only render when:
- The job status is `succeeded`
- The `result` field is not null
- The component is inside the `ExpandedDetail` panel

When `eligible` references is 0, the component MUST still render showing score 0 with the `low` band. It MUST NOT hide or display an error.

### 6) Accessibility

- The score number MUST have an `aria-label` that includes both the number and the band (e.g., "Authenticity Score: 87, High authenticity")
- The color semaphore MUST be accompanied by the text label (color alone is insufficient)
- The component MUST be readable by screen readers as a single coherent element
- The component MUST maintain sufficient color contrast in both light and dark modes

### 7) Responsiveness

- On desktop and mobile, the component MUST be fully visible within the expanded panel width
- The score number size MAY reduce on very narrow viewports (< 320px)
- The component MUST NOT cause horizontal scrolling

## Acceptance Criteria

- Score of 92 renders with green color and "High authenticity" label (or translated equivalent)
- Score of 65 renders with amber color and "Needs review" label (or translated equivalent)
- Score of 30 renders with red color and "Low authenticity" label (or translated equivalent)
- Score of 0 renders correctly (not hidden, shows red with "Low authenticity")
- Component is visible between the summary grid and classification breakdown in ExpandedDetail
- Switching language (EN/ES/PT) updates the score title and band label
- Dark mode and light mode both render with adequate contrast
- Screen reader announces "Authenticity Score: [number], [band label]"

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Score is exactly 100 | Renders "100" with green/high band |
| Score is exactly 0 | Renders "0" with red/low band |
| Score is exactly 80 (boundary) | Renders with green/high band |
| Score is exactly 50 (boundary) | Renders with amber/medium band |
| All references are processing_error | Renders "0" with red/low band (still visible) |
| Language changes while panel is expanded | Labels update; score number stays the same |
| Component re-renders with new data (job updated) | Score recalculates; display updates |

## Integration Points

- Consumes score computation from Step 02
- Integrated into `ExpandedDetail` component (from `spec/recent-analyses/10-frontend-ui`)
- Uses i18n keys defined in Step 09
- The same score value is reused in Step 07 (Export PDF)

## Dependencies

- Step 02 (Authenticity Score Formula) — provides the computation function
- Step 09 (i18n Catalog) — provides translated labels
