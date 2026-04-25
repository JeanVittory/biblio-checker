# Step 04 — Hero Section

## Scope

The hero is the first section on the landing page. It MUST communicate the product's value proposition and provide two calls-to-action: a primary button to start using the product, and a secondary button to see a demo.

## Context

Visitors form an opinion about a product within 10 seconds. The hero MUST answer: "What does this do?" and "Why should I care?" immediately. Two CTAs accommodate different user states: visitors ready to try will click primary; visitors who need evidence first will click secondary.

## Requirements

### 1) Component File

Create: `apps/frontend/components/landing/Hero.tsx`

Server component (no `"use client"` directive required unless client-only logic is added).

### 2) Content Structure

The hero MUST contain, in vertical order:
1. **Eyebrow** (optional small text above title): "Academic integrity, verified" (or equivalent)
2. **Title** — large heading, highest visual weight: `landing.hero.title`
3. **Subtitle** — supporting paragraph: `landing.hero.subtitle`
4. **CTA group** — two buttons side by side (stack on mobile):
   - Primary: `landing.hero.cta_primary` linking to `/app`
   - Secondary: `landing.hero.cta_secondary` linking to `/app?sample=1`
5. **Social proof line** (optional): small text like "Verifies against OpenAlex, SciELO, arXiv"

### 3) Title Messaging

The title in EN, ES, PT MUST convey:
- The problem being solved (fabricated/hallucinated references)
- The AI connection (since this is the current concern)
- A confident, active tone

Exact translations are defined in Step 12. The title is NOT a list of features — it's the value proposition.

### 4) CTA Primary Button

- Label: `landing.hero.cta_primary` (e.g., "Try now")
- Destination: `/app`
- Visual style: large, high-contrast, uses the brand gradient (`linear-gradient(135deg, var(--accent), var(--accent-secondary))`)
- Icon (optional): arrow-right from lucide-react
- Minimum touch target: 44x44 px on mobile

### 5) CTA Secondary Button

- Label: `landing.hero.cta_secondary` (e.g., "See demo with example")
- Destination: `/app?sample=1` (see Step 11 for behavior)
- Visual style: secondary — outlined, muted, or ghost button
- NOT using the gradient (reserved for primary)

### 6) Visual Layout

- Text content centered horizontally (desktop and mobile)
- Max content width: `max-w-4xl` for the hero block
- Vertical padding: generous on desktop (~`py-24`), reduced on mobile (~`py-12`)
- Optional decorative background: subtle gradient or grid pattern using CSS (no images required)

### 7) Responsive Behavior

- Desktop (≥ 768px): title, subtitle, CTAs each on their own visual level
- Mobile (< 768px): CTAs stack vertically, full-width buttons
- All text remains readable without horizontal scroll

### 8) Theme Compatibility

Uses existing CSS variables. In dark mode:
- Background matches `--background` (dark tone)
- Text uses `--foreground` (high contrast)
- Accent gradient visible on primary CTA

In light mode:
- Background inherits from parent (light tone)
- Text uses `--foreground` (dark tone)
- Accent gradient visible on primary CTA

### 9) Accessibility

- Title MUST use semantic `<h1>` (this is the page's top heading)
- Subtitle MUST be a `<p>` (not a heading)
- Both CTAs MUST be keyboard accessible
- Color contrast for text on both themes meets WCAG AA

## Acceptance Criteria

- Hero renders at the top of `/` with title, subtitle, and two CTAs
- Title is an `<h1>` element
- Primary CTA links to `/app`
- Secondary CTA links to `/app?sample=1`
- Buttons are keyboard accessible (Tab to focus, Enter to activate)
- Content is readable on mobile (375px) without horizontal scroll
- Dark and light modes both render with adequate contrast
- All user-visible strings are translated (EN/ES/PT switch correctly)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User has JavaScript disabled | Links still work (plain `<a>` or Next.js `<Link>`) |
| Very long translated title (e.g., German localization hypothetically) | Text wraps; does not overflow container |
| Mobile narrow viewport (< 320px) | Title may reduce in size; no horizontal scroll |

## Integration Points

- Step 11 (Sample Query Param) — the secondary CTA destination requires `?sample=1` handling
- Step 12 (i18n Catalog) — provides `landing.hero.*` keys

## Dependencies

- Step 03 (Marketing Layout) — hero is rendered inside the marketing layout
- Step 12 (i18n Catalog) — required for translations
