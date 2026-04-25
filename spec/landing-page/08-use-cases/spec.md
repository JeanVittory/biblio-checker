# Step 08 — Use Cases Section

## Scope

This section presents three user personas and the value Biblio Checker delivers to each.

## Context

Visitors self-identify with personas. Showing "this is for you if..." accelerates the decision to try the product. Three personas cover the primary market segments.

## Requirements

### 1) Component File

Create: `apps/frontend/components/landing/UseCases.tsx`

Server component.

### 2) Content Structure

The section MUST contain:
1. **Section title** — `landing.useCases.title` (e.g., "Built for your workflow")
2. **Three persona cards** — each with icon, title, and value statement

### 3) Three Personas

Each persona card MUST display:
- An icon from lucide-react representing the persona (e.g., `GraduationCap`, `BookOpen`, `Building2`)
- A persona title
- A 2-3 sentence value statement tailored to that persona

Persona content (exact strings in Step 12):

**Persona 1 — Professors / Reviewers:**
- Icon: `GraduationCap` or `Users`
- Title: `landing.useCases.professor.title` — e.g., "Professors and reviewers"
- Description: `landing.useCases.professor.desc` — quickly validate student work or peer submissions

**Persona 2 — Students / Authors:**
- Icon: `BookOpen` or `FileText`
- Title: `landing.useCases.student.title` — e.g., "Students and researchers"
- Description: `landing.useCases.student.desc` — self-check before submission

**Persona 3 — Institutions:**
- Icon: `Building2` or `Landmark`
- Title: `landing.useCases.institution.title` — e.g., "Institutions" (with "coming soon" badge or similar)
- Description: `landing.useCases.institution.desc` — integrations for LMS, batch processing

### 4) "Coming Soon" Badge

The institution persona MAY include a small "Coming soon" badge: `landing.useCases.comingSoon` — indicating this persona is in the roadmap but not yet fully served. This sets expectations correctly.

### 5) Visual Layout

- Section title centered above cards
- Three cards in a horizontal grid on desktop (≥ 768px)
- Cards stack vertically on mobile
- Cards use surface style: `rounded-lg bg-surface border border-border p-6`
- Icon above title inside each card

### 6) Max Width

Section content constrained to `max-w-6xl` centered.

### 7) Vertical Padding

`py-16` to `py-24` on desktop.

### 8) Accessibility

- Section title uses `<h2>`
- Persona titles use `<h3>`
- Icons have `aria-hidden="true"`
- "Coming soon" badge has clear visible text (not color-only)

## Acceptance Criteria

- Section renders with title + 3 persona cards
- Each card shows icon + title + value statement
- Institution card shows "Coming soon" indicator
- Cards arranged horizontally on desktop, vertically on mobile
- Translations apply in EN/ES/PT
- Dark/light mode renders correctly

## Integration Points

- Step 12 (i18n Catalog) — provides `landing.useCases.*` keys

## Dependencies

- Step 03 (Marketing Layout)
- Step 12 (i18n Catalog)
