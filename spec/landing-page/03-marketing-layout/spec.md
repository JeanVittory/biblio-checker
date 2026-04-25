# Step 03 — Marketing Layout

## Scope

This step specifies the Next.js route group and layout that wrap all marketing pages (currently just the landing page). It covers:
- Route group structure `(marketing)`
- `MarketingHeader` component
- `MarketingFooter` component
- Layout file composition

This step does NOT cover:
- The landing page content sections (Steps 04-10)
- Navigation between marketing pages (only one page exists for now)

## Context

Next.js 13+ supports route groups — folders named `(name)` that organize routes without affecting the URL. This lets us have a dedicated marketing layout (header + footer) separate from the app layout, without introducing a `/marketing/*` URL prefix.

The existing root layout (`apps/frontend/app/layout.tsx`) provides `LocaleProvider` and `ThemeProvider`. The marketing layout wraps its children with a header and footer specific to marketing pages.

## Requirements

### 1) Route Group Directory

Create directory: `apps/frontend/app/(marketing)/`

This is a Next.js route group. The parentheses tell Next.js to exclude this segment from the URL. Anything inside `(marketing)` is routed from the parent segment (`/`).

### 2) Layout File

Create: `apps/frontend/app/(marketing)/layout.tsx`

The layout MUST:
- Accept `children: React.ReactNode` as a prop
- Wrap children with the `MarketingHeader` above and `MarketingFooter` below
- Be a server component (no `"use client"` directive)
- Inherit `LocaleProvider` and `ThemeProvider` from the root layout (no re-wrapping needed)

Structure (conceptual):

```
<div min-h-screen flex flex-col>
  <MarketingHeader />
  <main className="flex-1">
    {children}
  </main>
  <MarketingFooter />
</div>
```

### 3) MarketingHeader Component

Create: `apps/frontend/components/landing/MarketingHeader.tsx`

MUST display:
- Biblio Checker logo/name (left) — MUST reuse the existing gradient style from `app/page.tsx` header (`linear-gradient(135deg, var(--accent), var(--accent-secondary))`)
- A secondary navigation area (right) containing:
  - A "Try now" link styled as a button, pointing to `/app`
  - The existing `LanguageToggle` component
  - The existing `ThemeToggle` component

Layout:
- Horizontal flex, items centered
- Logo on the left, nav items on the right
- Sticky or non-sticky — either is acceptable (not critical for v1)
- Padding consistent with the rest of the app (`px-6` or similar)
- Max width: full width, but inner content constrained to ~`max-w-6xl` centered

Mobile behavior:
- On viewports < 640px, the "Try now" button MAY be hidden in favor of a compact layout (logo + toggles only). The landing hero's CTA serves as the primary conversion path on mobile.

### 4) MarketingFooter Component

Create: `apps/frontend/components/landing/MarketingFooter.tsx`

MUST display:
- Three link groups (can be a simple grid on desktop, stacked on mobile):
  - **Product**: links to `/` (Home) and `/app` (App)
  - **Resources**: placeholder links for GitHub, Docs, About (can be `#` for v1)
  - **Language/Theme**: repeat of `LanguageToggle` and `ThemeToggle` for footer access
- Copyright line at the bottom: "© 2026 Biblio Checker" (translated via `landing.footer.copyright`)
- Tagline below copyright: reuse existing `home.footer_tagline` key OR use new `landing.footer.tagline`

Layout:
- Border-top separator from the main content
- Padding: generous vertical (e.g., `py-12`)
- Inner content constrained to `max-w-6xl` centered
- Dark/light theme compatible via CSS variables

### 5) Root Layout Compatibility

The existing `apps/frontend/app/layout.tsx` MUST continue to work without modification. The marketing layout is a child layout that receives already-wrapped children from the root layout.

### 6) Landing Page File (Required Artifact)

This step MUST create the landing page file at:
```
apps/frontend/app/(marketing)/page.tsx
```

The file MUST be a **server component** (no `"use client"` directive). It imports and composes the section components from Steps 04-10 in the order specified in Step 01. Client components (like `DemoScore`) are imported as leaf islands — the page itself remains server-rendered to preserve SEO and initial load performance.

A correct file shape (conceptual):
```
import { Hero } from "@/components/landing/Hero";
import { ProblemSection } from "@/components/landing/ProblemSection";
// ... other sections
import { DemoScore } from "@/components/landing/DemoScore"; // client component island

export default function LandingPage() {
  return (
    <>
      <Hero />
      <ProblemSection />
      <HowItWorks />
      <DemoScore />
      <UseCases />
      <Sources />
      <FinalCTA />
    </>
  );
}
```

### 7) Marketing Header — Client Component Composition

The `MarketingHeader` MUST be treated as a server component file (no `"use client"`) that IMPORTS client components (`LanguageToggle`, `ThemeToggle`) as leaf nodes. The header itself MUST NOT call any React hooks. This is the standard Next.js RSC pattern: a server component can render client components, but cannot call client-only hooks directly.

### 8) Tagline Key Resolution

The footer tagline MUST use the existing `home.footer_tagline` key from the current catalog. No new `landing.footer.tagline` key is introduced — Step 12 MUST NOT add this key. This avoids key duplication and preserves the existing tagline value.

### 9) External Link Security

Any footer link with `target="_blank"` MUST include `rel="noopener noreferrer"` to prevent tab-napping (CWE-1022). This applies when placeholder `#` links are eventually replaced with real external URLs.

### 10) `/app` Uses Root Layout Only

The `/app` route (moved in Step 02) MUST NOT use the marketing layout. The `/app/page.tsx` lives outside `(marketing)`, so Next.js applies only the root layout to it. This preserves the existing app UI (which has its own header inside `page.tsx`).

## Acceptance Criteria

- `apps/frontend/app/(marketing)/layout.tsx` exists and wraps children with header + footer
- `apps/frontend/components/landing/MarketingHeader.tsx` exists and displays logo + "Try now" button + toggles
- `apps/frontend/components/landing/MarketingFooter.tsx` exists and displays link groups + copyright
- Navigating to `/` shows a page with the marketing header and footer (content comes from Step 04+)
- Navigating to `/app` does NOT show the marketing header/footer (app's own header is used)
- `LocaleProvider` and `ThemeProvider` still work on marketing pages (toggles function correctly)
- Dark/light mode applies to header and footer
- Mobile (375px) shows a usable header without horizontal scroll

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User switches theme from marketing footer | Theme applies to entire site (same provider) |
| User switches language from marketing header | Locale changes across all pages |
| Page has very long content | Footer stays at the bottom of content (flex-col + flex-1 pattern) |
| User navigates from `/` to `/app` | Marketing layout unmounts; app UI shows |

## Integration Points

- Step 02 (Routing Restructure) — the `/app` route uses root layout only; `/` uses marketing layout
- Steps 04-10 (Content Sections) — all render inside `app/(marketing)/page.tsx` (Step 04 onwards)
- Reuses `LanguageToggle` from `apps/frontend/components/language-toggle.tsx`
- Reuses `ThemeToggle` from `apps/frontend/components/theme-toggle.tsx`

## Dependencies

- Step 02 (Routing Restructure) — `/app` must exist before `/` can safely change
- Step 12 (i18n Catalog) — header + footer strings must be translated
