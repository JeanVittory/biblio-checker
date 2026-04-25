# Step 10 — Final CTA Section

## Scope

This section repeats the primary call-to-action at the bottom of the page. Visitors who scrolled through all content may have forgotten the initial CTA; this section recaptures them at the decision moment.

## Context

Users who read the full page have invested attention and are warm leads. The final CTA is placed where they naturally reach after consuming all content. It repeats the hero's CTAs to close the conversion.

## Requirements

### 1) Component File

Create: `apps/frontend/components/landing/FinalCTA.tsx`

Server component.

### 2) Content Structure

The section MUST contain:
1. **Title** — `landing.cta.title` (e.g., "Ready to verify your bibliography?")
2. **Subtitle** (optional) — `landing.cta.subtitle` reinforcing the value
3. **CTA group** — two buttons:
   - Primary: `landing.hero.cta_primary` (reuse hero key) linking to `/app`
   - Secondary: `landing.hero.cta_secondary` linking to `/app?sample=1`

### 3) CTA Buttons

MUST be visually identical to the hero CTAs (same styles, same destinations):
- Primary: brand gradient, bold
- Secondary: outlined/ghost

### 4) Visual Layout

- Centered content
- Background MAY have a subtle accent (e.g., a gradient or elevated surface) to differentiate from the neutral sections above
- Max content width: `max-w-4xl` centered
- Vertical padding: generous (`py-24` on desktop)

### 5) Visual Differentiation

The final CTA SHOULD feel like a "moment." Options:
- A full-width accent background (using `--accent` with low opacity)
- A bordered box
- Slightly larger typography than other sections

This is visual preference; pick one approach that fits the overall design.

### 6) Accessibility

- Title uses `<h2>`
- Both CTAs keyboard accessible
- Color contrast meets WCAG AA

## Acceptance Criteria

- Section renders at the bottom of the landing (before the footer)
- Title + two CTA buttons visible
- Primary CTA links to `/app`
- Secondary CTA links to `/app?sample=1`
- Translations apply in EN/ES/PT
- Dark/light mode renders correctly

## Integration Points

- Reuses `landing.hero.cta_primary` and `landing.hero.cta_secondary` keys
- Step 12 (i18n Catalog) — provides `landing.cta.*` keys
- Step 11 (Sample Query Param) — secondary CTA destination

## Dependencies

- Step 03 (Marketing Layout)
- Step 04 (Hero Section) — defines the CTA key structure this section reuses
- Step 12 (i18n Catalog)
