# Step 13 — Acceptance and Validation

## Scope

This step specifies end-to-end acceptance criteria, user journeys, and a verification plan for the complete landing page feature.

## Requirements

### 1) End-to-End User Journeys

#### Journey 1: First-time Visitor
1. Visitor navigates to `/`
2. Sees the hero with title, subtitle, and two CTAs
3. Scrolls through problem, how it works, demo, use cases, sources sections
4. Sees the final CTA
5. Clicks "Try now" primary CTA
6. Lands on `/app` with empty dropzone
7. Uploads their own document
8. Sees analysis results

#### Journey 2: Quick Demo via Sample
1. Visitor navigates to `/`
2. Clicks "See demo with example" secondary CTA
3. Lands on `/app?sample=1`
4. Sample PDF is automatically loaded into the dropzone
5. Analysis starts automatically (if auto-submit is implemented)
6. Visitor sees real results with Authenticity Score, reference details, and evidence

#### Journey 3: Returning User via Bookmark
1. Returning user has `/app` bookmarked
2. Navigates directly to `/app`
3. Sees the uploader with all previous localStorage jobs
4. NOT affected by the landing page change

#### Journey 4: Share Link Recipient
1. User receives a share link: `/r/<token>`
2. Opens the link, views shared results
3. Clicks "Try Biblio Checker" CTA at the bottom of the share page
4. Lands on `/` (new landing), sees full marketing pitch
5. Clicks "Try now" to start their own analysis

#### Journey 5: Language Switch
1. User on `/` in English clicks the language toggle in the header
2. Switches to Spanish
3. ALL landing sections update to Spanish text
4. Navigates to `/app`, language persists as Spanish
5. Switches to Portuguese
6. Navigates back to `/`, all sections render in Portuguese

#### Journey 6: Theme Switch
1. User on `/` in light mode clicks the theme toggle
2. Switches to dark mode
3. ALL landing sections render with dark theme colors
4. Demo score section shows correct colors (red for low band)
5. Theme persists across navigation to `/app` and `/r/<token>`

### 2) Regression Checklist

The following existing behaviors MUST NOT be regressed:

- [ ] `/app` uploader accepts file drop and file picker
- [ ] `/app` submit button starts analysis
- [ ] `/app` Recent Analyses table shows localStorage jobs
- [ ] Polling updates job status in real-time on `/app`
- [ ] Expand/collapse reference cards works on `/app`
- [ ] Export PDF/CSV buttons work on `/app`
- [ ] Share button works on `/app` for recent jobs
- [ ] Share page `/r/<token>` renders shared results correctly
- [ ] Share page "Try Biblio Checker" CTA points to `/` (not `/app`)
- [ ] Remove button deletes job from localStorage
- [ ] Page refresh preserves localStorage on `/app`
- [ ] Dark/light mode works across all routes
- [ ] Language toggle works across all routes
- [ ] No TypeScript errors (`tsc --noEmit` passes)
- [ ] Existing tests pass (`vitest run`)
- [ ] i18n shape test passes (all 3 catalogs synchronized)

### 3) Cross-Feature Integration

| Feature A | Feature B | Verification |
|-----------|-----------|--------------|
| Landing demo | AuthenticityScore component | Same visual output as real analysis |
| Landing hero secondary CTA | `?sample=1` auto-load | Works end-to-end |
| Landing footer | Theme toggle | Switches theme site-wide |
| Landing footer | Language toggle | Switches language site-wide |
| Share page CTA | Landing page | Points to `/` and lands on marketing |
| `/app` | Uploader behavior | Unchanged from previous `/` |

### 4) Accessibility Checklist

- [ ] `/` has exactly one `<h1>` (in the Hero)
- [ ] Section titles use `<h2>`, card titles use `<h3>`
- [ ] All CTAs are keyboard accessible (Tab, Enter)
- [ ] All icons are decorative (`aria-hidden="true"`)
- [ ] Color contrast meets WCAG AA on both themes
- [ ] No layout shifts when toggling theme
- [ ] Screen reader reads hero content in logical order

### 5) Performance Criteria

| Metric | Threshold |
|--------|-----------|
| Landing page initial HTML size | < 80 KB (gzipped) |
| Landing page First Contentful Paint | < 1.5 seconds on 3G |
| Landing page Largest Contentful Paint | < 2.5 seconds on 3G |
| Navigation to `/app` | < 500 ms |
| Sample auto-load on `/app?sample=1` | < 3 seconds to first visible file |

### 6) Responsive Testing

| Viewport | Expected |
|----------|----------|
| 375px (mobile) | All content readable, no horizontal scroll, CTAs tap-friendly |
| 768px (tablet) | Grid sections start transitioning to rows |
| 1024px (desktop) | Full horizontal layouts, max-width constraints apply |
| 1440px (wide) | Content centered, no stretching |

### 7) Manual Testing Plan

| Test | Steps | Expected |
|------|-------|----------|
| Landing renders | Navigate to `/` | All 8 sections visible |
| Primary CTA | Click "Try now" | Lands on `/app` |
| Secondary CTA | Click "See demo" | Lands on `/app?sample=1`, sample loads |
| Demo score | View demo section | Authenticity Score shows 38 (red) |
| Mobile view | View on 375px | No horizontal scroll, content readable |
| Dark mode | Toggle theme | All sections render correctly |
| Language EN → ES | Toggle language | All sections translate |
| Language ES → PT | Toggle language | All sections translate |
| Bookmark `/app` | Open bookmark | Uploader shows directly |
| Share page CTA | On `/r/<token>`, click "Try Biblio Checker" | Lands on `/` (landing) |
| Keyboard nav | Tab through landing | All CTAs and toggles focus correctly |

## Acceptance Criteria

- All 6 user journeys pass end-to-end
- All regression checklist items pass
- All cross-feature integrations verified
- Accessibility checklist passes
- Performance criteria met
- Responsive testing passes at all viewports
- All manual tests produce expected results

## Dependencies

- All previous steps (01-12) MUST be implemented before end-to-end validation
