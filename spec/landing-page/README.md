# Landing Page Feature — Specification Suite

This directory contains a complete Spec-Driven Development (SDD) specification for the "Landing Page" feature of Biblio Checker.

## Quick Start

1. **Start here:** Read `INDEX.md` for an overview and navigation guide
2. **Full specs:** Open any numbered folder (01-13) to read the detailed functional specification
3. **For implementation:** Begin with steps in the order recommended in `INDEX.md`

## What's Included

13 numbered specification directories, each containing a single `spec.md`:

- `01-overview` — Feature overview, scope, user journey
- `02-routing-restructure` — Move uploader from `/` to `/app`; landing becomes new `/`
- `03-marketing-layout` — MarketingHeader + MarketingFooter + route group `(marketing)`
- `04-hero-section` — Title, subtitle, primary + secondary CTAs
- `05-problem-section` — Three facts about AI-fabricated references
- `06-how-it-works` — Three-step visual explanation (upload → analyze → score)
- `07-demo-score` — Live demo using existing AuthenticityScore component with static data
- `08-use-cases` — Three personas (professors, students, institutions)
- `09-sources-section` — Visual list of verification sources (OpenAlex, SciELO, arXiv, OpenLibrary)
- `10-final-cta` — Repeat CTA at bottom of page
- `11-sample-query-param` — `/app?sample=1` auto-loads the sample document
- `12-i18n-catalog` — Complete i18n key catalog for EN/ES/PT
- `13-acceptance-and-validation` — End-to-end acceptance criteria and test matrix

## Key Features Specified

- **Clear value proposition** — Visitors understand the product in under 30 seconds
- **Two CTAs** — Primary ("Try now") and secondary ("See demo with example")
- **Route restructure** — `/` = marketing, `/app` = product (industry standard pattern)
- **Reuses existing components** — `AuthenticityScore` displays a live demo score
- **Full i18n** — All strings translated to EN/ES/PT
- **Dark/light theme compatible** — Uses existing CSS variables
- **Mobile responsive** — Works on 375px viewports

## Important Notes

**These specs contain:**
- Functional requirements (what each section displays)
- User flows and interactions
- Acceptance criteria
- Layout specifications (conceptual, not exact pixels)
- i18n key catalog

**These specs do NOT contain:**
- Code (TypeScript, CSS, etc.)
- Exact color values (use existing CSS variables)
- Specific Tailwind classes
- Illustration/image assets

## Using These Specs

### For Frontend Engineers
- Priority: All steps (02-11)
- Start with Step 02 (routing restructure) and Step 12 (i18n) — these are prerequisites
- Section specs (04-10) can be implemented in parallel after Step 03

### For Product/Design
- Read Step 01 for scope and messaging
- Steps 04-10 describe each section's purpose and content

### For QA/Testing
- Reference Step 13 for end-to-end acceptance criteria
- Each spec's "Acceptance Criteria" section is a testable checklist

## Dependency Flow

```
01 (Overview)
├── 02 (Routing Restructure) [Foundation]
│   └── 03 (Marketing Layout)
│        └── 04-10 (Sections, parallel)
│             └── 11 (Sample Query Param)
├── 12 (i18n Catalog) [Cross-cutting]
│    └── 04-10 (Sections consume keys)
└── 13 (Acceptance) [All previous steps]
```

## Implementation Phases

| Phase | Steps | Deliverable | Can Parallelize |
|-------|-------|-------------|-----------------|
| 1A | 02 | Move `/` to `/app`, update share page CTA | Yes |
| 1B | 12 | Complete i18n catalog | Yes |
| 2 | 03 | Marketing layout + header + footer | After 1A |
| 3 | 04, 05, 06, 07, 08, 09, 10 | Landing page sections | After 2+1B (parallel) |
| 4 | 11 | Sample auto-load on `/app?sample=1` | After 3 |
| 5 | 13 | End-to-end validation | After all |

## Cross-Suite Dependencies

- **momento-wow** — Reuses `AuthenticityScore` component in the demo section
- **share-link** — Updates the "Try Biblio Checker" CTA from `/app` to `/` (landing)
- **recent-analyses** — The `/app` route preserves the existing uploader + table behavior
- **i18n-multilingual-support** — Extends existing message catalogs with `landing.*` namespace

---

**Status:** Complete and Ready for Implementation
**Last Updated:** April 16, 2026
**For:** Biblio Checker — Landing Page Feature
