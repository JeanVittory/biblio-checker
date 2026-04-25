# Step 01 — Overview and Scope

## Overview

The **Landing Page** is the new public-facing entry point for Biblio Checker at `/`. It converts visitors into users by explaining the problem Biblio Checker solves (AI-fabricated academic references), demonstrating the product value, and providing clear calls-to-action. The existing uploader interface moves to `/app`.

The user journey:

```
Visitor arrives at / → Hero explains problem + solution
→ Clicks "Try now" → /app (uploader)
→ OR clicks "See demo with example" → /app?sample=1 (auto-loads sample)
```

## Scope (In-Scope)

- New marketing landing page at `/` with 8 sections (hero, problem, how it works, demo, use cases, sources, final CTA, footer)
- Route restructure: move existing home (`/`) to `/app`
- Separate marketing layout (`MarketingHeader` + `MarketingFooter`) using Next.js route groups
- Reuse of existing `AuthenticityScore` component for live demo with static data
- `?sample=1` query parameter on `/app` that auto-loads the sample document
- Update to share page CTA: "Try Biblio Checker" now points to `/` (landing), not `/app`
- Full i18n in EN/ES/PT (38 new keys under `landing.*`, see Step 12)
- Dark/light theme support using existing CSS variables
- Mobile responsive (375px minimum)

## Non-Scope (Out-of-Scope)

- Videos or complex animations (CSS + lucide-react icons only)
- Real testimonials (placeholder slots until real users exist)
- Blog or docs pages (placeholder links only)
- A/B testing infrastructure
- Analytics integration (Plausible, GA) — separate decision
- Advanced SEO (Open Graph, Twitter cards) — v1 includes basic metadata only
- Pricing page
- Contact form or newsletter signup
- Login or authentication UI
- Custom illustrations or professional photography

## Context

**Current State:**
The home page (`/`) shows the file uploader directly. A first-time visitor sees a dropzone but no explanation of what the tool does or why they should use it. The share-link feature's "Try Biblio Checker" CTA lands visitors on this bare uploader.

**Problem Addressed:**
- Low conversion: visitors without a PDF ready leave immediately
- No education: the problem of AI-fabricated references is not communicated
- No product demo: visitors can't see results without uploading
- Unclear positioning: the page doesn't differentiate from competitors or explain value

**Solution Design:**
A dedicated marketing page at `/` that educates, demonstrates, and converts. The uploader moves to `/app`, following the industry-standard pattern (Vercel, Linear, Cal.com). Route groups in Next.js provide a separate layout for marketing pages without URL prefixes. The demo section reuses the existing `AuthenticityScore` component with static data to show real results without requiring an analysis.

## User Personas

**Primary: Academic Professional (First Visit)**
- Arrives via search, referral, or share link
- Has heard about AI-generated citation issues but hasn't validated their concern
- Wants to understand: what does this tool do? Is it trustworthy? Can I try it?
- Decision time: under 60 seconds

**Secondary: Returning User**
- Already knows the product, uses it regularly
- Types `/app` directly or has it bookmarked
- Does NOT need the landing page

**Tertiary: Share Link Recipient**
- Received a `/r/<token>` link
- After viewing shared results, clicks "Try Biblio Checker"
- Lands on `/` (landing) — sees full product pitch

## Success Metrics

1. Visitor arrives at `/` and understands what Biblio Checker does within 10 seconds of reading the hero
2. Visitor can try the product with a sample document in under 3 clicks (landing → "See demo" → results)
3. Visitor understands the three verification sources (OpenAlex, SciELO, arXiv)
4. Mobile visitors have the same experience quality as desktop
5. All strings translate correctly in EN/ES/PT

## Constraints & Assumptions

- The existing `/app` uploader remains fully functional after the move
- The share-link feature CTA is updated to point to `/` (not `/app`)
- No new backend endpoints are needed
- No new database changes
- The demo section shows a deliberately "bad" score (low authenticity) to demonstrate the product catches issues
- The sample document from `public/samples/sample-references.pdf` is reused for the `?sample=1` flow
- The landing page is server-rendered (Next.js RSC) for SEO and initial load speed
- Existing theme system (CSS variables + next-themes) applies to landing

## Dependencies

- None (this is the entry point for the suite)
