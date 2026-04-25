# Landing Page Feature — Specification Index

## Structure

13 logical steps numbered 01-13. Each step is a directory containing a single `spec.md` file.

### Reading Order

1. **01-overview** — Start here. Scope, personas, user journey, constraints.
2. **02-routing-restructure** — Move uploader from `/` to `/app`; landing becomes new `/`.
3. **03-marketing-layout** — MarketingHeader + MarketingFooter + route group pattern.
4. **04-hero-section** — Hero area with title, subtitle, two CTAs.
5. **05-problem-section** — Three facts about AI-fabricated references.
6. **06-how-it-works** — Three-step visual explanation.
7. **07-demo-score** — Live demo reusing AuthenticityScore.
8. **08-use-cases** — Three personas with value propositions.
9. **09-sources-section** — List of verification sources.
10. **10-final-cta** — Repeated call-to-action at page bottom.
11. **11-sample-query-param** — `/app?sample=1` auto-loads sample document.
12. **12-i18n-catalog** — Complete key catalog for EN/ES/PT.
13. **13-acceptance-and-validation** — End-to-end criteria, test matrix.

### Dependency Graph

```
01 (Overview)
 ├── 02 (Routing Restructure) [Foundation]
 │    └── 03 (Marketing Layout)
 │         ├── 04 (Hero)
 │         ├── 05 (Problem)
 │         ├── 06 (How It Works)
 │         ├── 07 (Demo Score)
 │         ├── 08 (Use Cases)
 │         ├── 09 (Sources)
 │         └── 10 (Final CTA)
 ├── 11 (Sample Query Param) ──> consumed by Step 04
 ├── 12 (i18n Catalog) [Cross-cutting]
 │    └── 04, 05, 06, 07, 08, 09, 10
 └── 13 (Acceptance) [Depends on all]
```

### Quick Navigation

| Step | Title | Focus |
|------|-------|-------|
| 01 | Overview | Scope, personas, user journey |
| 02 | Routing Restructure | `/` → landing, `/app` → uploader |
| 03 | Marketing Layout | Header + footer + route group |
| 04 | Hero Section | Title, subtitle, two CTAs |
| 05 | Problem Section | Three facts about the problem |
| 06 | How It Works | Three-step explanation |
| 07 | Demo Score | Static AuthenticityScore showcase |
| 08 | Use Cases | Three personas |
| 09 | Sources Section | Verification sources list |
| 10 | Final CTA | Repeated CTA at bottom |
| 11 | Sample Query Param | `?sample=1` auto-load |
| 12 | i18n Catalog | EN/ES/PT keys |
| 13 | Acceptance | E2E criteria |

## Key Concepts

### Route Groups `(marketing)`

Next.js allows grouping routes with `(name)` folders that do NOT affect the URL path. This gives us a separate layout for marketing pages without a URL prefix.

### Content Reuse

The demo section (Step 07) reuses the existing `AuthenticityScore` component (from momento-wow) with hardcoded `countsByClassification` data. This demonstrates the actual product without requiring a live analysis.

### `?sample=1` Pattern

Step 11 adds a query parameter handler to `/app`. When the URL is `/app?sample=1`, the page automatically triggers the same "Try with example" flow as clicking the sample button in FileDropzone. This enables the hero CTA "See demo with example" to land directly in the analysis flow.

---

Generated: April 16, 2026
For: Biblio Checker — Landing Page Feature
