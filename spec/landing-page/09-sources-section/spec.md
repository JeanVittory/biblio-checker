# Step 09 — Sources Section

## Scope

This section displays the academic databases Biblio Checker verifies against. It establishes credibility by naming well-known sources.

## Context

When a product claims "we verify references," visitors want to know against what. Listing OpenAlex, SciELO, arXiv, and OpenLibrary establishes technical credibility and transparency. This is especially important for academic audiences who know these sources.

## Requirements

### 1) Component File

Create: `apps/frontend/components/landing/Sources.tsx`

Server component.

### 2) Content Structure

The section MUST contain:
1. **Section title** — `landing.sources.title` (e.g., "Verified against trusted sources")
2. **Section subtitle** — `landing.sources.subtitle` explaining the sources
3. **List of sources** — visual cards or chips showing each source name

### 3) Sources to Display

Four sources:
1. **OpenAlex** — global academic index
2. **SciELO** — Latin American journal collection
3. **arXiv** — preprints (physics, math, CS, etc.)
4. **OpenLibrary** — books

Each source MUST display:
- The source name (plain text, no logo required for v1)
- A short one-line description: `landing.sources.{source}.desc`
- Optional: an icon representing its category (e.g., `Globe` for OpenAlex, `BookOpen` for OpenLibrary)

### 4) Visual Layout

- Section title + subtitle centered
- Sources arranged in a horizontal row on desktop, grid on tablet, stack on mobile
- Each source in a simple card or chip:
  - Surface style: `rounded-lg bg-surface border border-border p-4`
  - Name bold, description small and muted

### 5) No External Logos

For v1, logos of the sources are NOT included. Logos introduce licensing considerations and asset management. Plain text names are sufficient and respectful of the sources.

### 6) Max Width

Section content constrained to `max-w-6xl` centered.

### 7) Vertical Padding

`py-16` to `py-24` on desktop.

### 8) Accessibility

- Section title uses `<h2>`
- Source names use `<h3>` or strong emphasis
- Icons have `aria-hidden="true"`

## Acceptance Criteria

- Section renders with title + subtitle + 4 source cards
- Each card shows source name + description
- Cards arranged horizontally on desktop, stacked on mobile
- Translations apply in EN/ES/PT
- Dark/light mode renders correctly

## Integration Points

- Step 12 (i18n Catalog) — provides `landing.sources.*` keys

## Dependencies

- Step 03 (Marketing Layout)
- Step 12 (i18n Catalog)
