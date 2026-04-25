# Step 06 — How It Works Section

## Scope

This section explains the product workflow in three visual steps: upload, analyze, get score.

## Context

After understanding the problem, visitors want to know HOW the product solves it. A three-step visual explanation removes uncertainty about effort and outcome.

## Requirements

### 1) Component File

Create: `apps/frontend/components/landing/HowItWorks.tsx`

Server component.

### 2) Content Structure

The section MUST contain:
1. **Section title** — `landing.howItWorks.title` (e.g., "How it works")
2. **Three numbered steps** — each with number, icon, title, and description

### 3) Three Steps

Each step MUST display:
- A visible step number (1, 2, 3) — can be a large numeral or badge
- An icon from lucide-react (`Upload`, `Search`, `BarChart3` or similar)
- A short title
- A 1-2 sentence description

Step content (exact strings in Step 12):

**Step 1 — Upload:**
- Title: `landing.howItWorks.step1.title` — e.g., "Upload your document"
- Description: `landing.howItWorks.step1.desc` — supports PDF and DOCX, documents with references

**Step 2 — Verify:**
- Title: `landing.howItWorks.step2.title` — e.g., "We verify each reference"
- Description: `landing.howItWorks.step2.desc` — cross-checks against OpenAlex, SciELO, arXiv

**Step 3 — Get Score:**
- Title: `landing.howItWorks.step3.title` — e.g., "See authenticity score + evidence"
- Description: `landing.howItWorks.step3.desc` — clear verdict with per-reference evidence

### 4) Visual Layout

- Section title centered above steps
- Three steps in a horizontal row on desktop with connecting line/arrow between them (optional, CSS-based)
- Steps stack vertically on mobile
- Each step contains number + icon + title + description in a single card or flat layout

### 5) Step Number Styling

The step number MUST be visually distinct:
- Could be a circle with the number inside
- Could be the number styled with the brand gradient
- Size: prominent but not dominant (e.g., `text-4xl` for the number)

### 6) Optional Connecting Visual

On desktop, a horizontal line or chevron between steps MAY be added via CSS for visual flow. Not required for functionality.

### 7) Max Width

Section content constrained to `max-w-6xl` centered.

### 8) Vertical Padding

`py-16` to `py-24` on desktop.

### 9) Accessibility

- Section title uses `<h2>`
- Step titles use `<h3>`
- Step numbers are visual only; screen readers read the step title
- Icons have `aria-hidden="true"`

## Acceptance Criteria

- Section renders with title + 3 numbered steps
- Steps arranged horizontally on desktop, vertically on mobile
- Each step shows number, icon, title, description
- Translations apply in EN/ES/PT
- Dark/light mode renders correctly

## Integration Points

- Step 12 (i18n Catalog) — provides `landing.howItWorks.*` keys

## Dependencies

- Step 03 (Marketing Layout)
- Step 12 (i18n Catalog)
