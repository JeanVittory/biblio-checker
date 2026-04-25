# Step 07 — Demo Score Section

## Scope

This section showcases the product output using the real `AuthenticityScore` component with hardcoded data. It demonstrates what users see after an analysis, without requiring them to run one.

## Context

"Show, don't tell" applies to landing pages. Instead of screenshots or illustrations, we render the actual product component to establish credibility and demonstrate the output quality. Visitors see the real score UI, real colors, and real semaphore logic.

## Requirements

### 1) Component File

Create: `apps/frontend/components/landing/DemoScore.tsx`

Client component (`"use client"` required because `AuthenticityScore` uses hooks).

**Critical architectural constraint:** `DemoScore` is a **client component island** imported by the otherwise server-rendered landing page (`app/(marketing)/page.tsx`). The page file MUST remain a server component — `"use client"` MUST NOT be added at the page level. This preserves SSR and SEO performance per Step 01. Only this single island (and other explicitly client components like the toggles) runs in the client bundle.

### 2) Content Structure

The section MUST contain:
1. **Section title** — `landing.demo.title` (e.g., "This is what you get")
2. **Section subtitle** — `landing.demo.subtitle` explaining the demo
3. **Demo card** containing:
   - The `AuthenticityScore` component with static data
   - A classification breakdown list showing the counts
   - A small caption: `landing.demo.caption` — e.g., "Example analysis of a document with mixed references"

### 3) Static Demo Data

The section MUST use hardcoded `countsByClassification` data designed to produce a **medium-low score** that demonstrates the product catches issues:

```
{
  verified: 2,
  likely_verified: 1,
  ambiguous: 1,
  not_found: 3,
  suspicious: 1,
  processing_error: 0
}
```

Using the formula from `spec/momento-wow/02-authenticity-score-formula`:
- eligible = 8, weightedSum = 2 + 0.75 + 0.25 = 3.0
- score = round(3.0/8 * 100) = 38 (red/low band)

A low score is intentional — it demonstrates the product surfaces problems. Using a high score would not show the product's value.

### 4) AuthenticityScore Reuse

The section MUST import and render `AuthenticityScore` from `apps/frontend/components/recent-analyses/AuthenticityScore.tsx` directly. No fork or duplicate.

Props: `countsByClassification` (the static object above).

### 5) Classification Breakdown

Below (or alongside) the score, show the classification breakdown with counts:
- Verified: 2
- Likely verified: 1
- Ambiguous: 1
- Not found: 3
- Suspicious: 1

Use the existing translated labels (`results.classification.*` keys already exist from momento-wow).

### 6) Visual Layout

- Section title centered above the demo
- Demo card centered, max width ~`max-w-md`
- Card uses surface style: `rounded-lg bg-surface border border-border p-6`
- Breakdown list below the score, right-aligned or left-aligned count column

### 7) Optional: Sample Reference Preview

The section MAY include a small preview of one "not_found" reference card with its classification badge to demonstrate per-reference detail. This is a nice-to-have, not required for v1.

### 8) Accessibility

- Section title uses `<h2>`
- The score component already includes aria-label
- Breakdown list is semantic HTML (`<dl>` or `<ul>`)

### 9) i18n Label for Demo

The caption MUST make clear this is a demo, not a real analysis: `landing.demo.caption` — "Example analysis" or equivalent in each language.

## Acceptance Criteria

- Section renders with title + demo card
- Demo card shows `AuthenticityScore` component with score of 38 (low/red)
- Classification breakdown shows correct counts
- Component matches the exact appearance in the real app (since it's the same component)
- Translations apply in EN/ES/PT
- Dark/light mode renders correctly

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| If formula changes in future, score changes | Acceptable — the demo shows whatever the current formula produces from the static data |
| User inspects DOM and sees it's a real component | Intentional — authenticity of demo is the point |

## Integration Points

- Reuses `AuthenticityScore` from `apps/frontend/components/recent-analyses/AuthenticityScore.tsx`
- Reuses translated classification labels from `results.classification.*`
- Step 12 (i18n Catalog) — provides `landing.demo.*` keys

## Dependencies

- Step 03 (Marketing Layout)
- Step 12 (i18n Catalog)
- Existing `AuthenticityScore` component (from momento-wow suite)
