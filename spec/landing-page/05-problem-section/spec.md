# Step 05 — Problem Section

## Scope

This section educates visitors about the problem Biblio Checker solves: AI-generated academic content contains fabricated references that are difficult to detect manually.

## Context

After the hero, visitors who are still scrolling want context. Why does this product exist? What specifically is broken? This section provides three concrete facts that justify the product's existence.

## Requirements

### 1) Component File

Create: `apps/frontend/components/landing/ProblemSection.tsx`

Server component.

### 2) Content Structure

The section MUST contain:
1. **Section title** — `landing.problem.title` (e.g., "The bibliographic deep fake problem")
2. **Section subtitle** (optional) — `landing.problem.subtitle` explaining the context briefly
3. **Three fact cards** — each with an icon, title, and short description

### 3) Three Fact Cards

Each fact card MUST display:
- An icon from lucide-react (e.g., `AlertTriangle`, `Bot`, `BookX`)
- A title (short, bold)
- A description (2-3 sentences max)

Suggested content (exact strings in Step 12):

**Fact 1 — AI hallucinates references:**
- Title: `landing.problem.fact1.title` — e.g., "AI fabricates plausible citations"
- Description: `landing.problem.fact1.desc` — explains that LLMs generate realistic-looking but non-existent references

**Fact 2 — Manual verification doesn't scale:**
- Title: `landing.problem.fact2.title` — e.g., "Manual verification takes hours"
- Description: `landing.problem.fact2.desc` — explains the time cost and scale issue for professors/reviewers

**Fact 3 — Academic integrity risk:**
- Title: `landing.problem.fact3.title` — e.g., "Fake citations slip through review"
- Description: `landing.problem.fact3.desc` — explains the risk when fabricated references pass review

### 4) Visual Layout

- Section title centered above the cards
- Three cards in a horizontal grid on desktop (≥ 768px)
- Cards stack vertically on mobile (< 768px)
- Cards use the existing surface style: `rounded-lg bg-surface border border-border p-6`
- Icon above title in each card, colored with a subtle accent (red/amber for emphasis)

### 5) Max Width

Section content constrained to `max-w-6xl` centered. Cards evenly distributed within.

### 6) Vertical Padding

Generous section padding: `py-16` to `py-24` on desktop, reduced on mobile.

### 7) Theme Compatibility

Uses CSS variables. Cards respect dark/light mode automatically via `bg-surface` and `border-border`.

### 8) Accessibility

- Section title uses `<h2>` (below hero's `<h1>`)
- Card titles use `<h3>`
- Icons have `aria-hidden="true"` (decorative)
- Text contrast meets WCAG AA

## Acceptance Criteria

- Section renders below the hero with title + 3 cards
- Cards display icon + title + description
- Cards arranged horizontally on desktop, vertically on mobile
- Translations apply in EN/ES/PT
- Dark/light mode renders correctly
- Semantic HTML: `<h2>` for section title, `<h3>` for card titles

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Very long description text | Card height adjusts; no text truncation |
| User resizes from desktop to mobile | Grid collapses to single column smoothly |
| Icons fail to load | Cards still render with title + description |

## Integration Points

- Step 12 (i18n Catalog) — provides `landing.problem.*` keys

## Dependencies

- Step 03 (Marketing Layout)
- Step 12 (i18n Catalog)
