# Step 06 — Share Page

## Scope

This step specifies the frontend page that renders shared analysis results at `/r/[shareToken]`. It covers:
- Page layout and structure
- Data fetching
- Result rendering (reusing existing components)
- Error and loading states
- Branding and call-to-action

This step does NOT cover:
- The proxy route (see Step 05)
- The backend endpoint (see Step 04)
- Social meta tags (out of scope for v1)

## Context

The share page is the first contact many recipients will have with Biblio Checker. A professor shares a link; the student opens it. The page must render the analysis results in a clear, branded way that also introduces the product.

The page reuses existing components from the `ExpandedDetail` panel (AuthenticityScore, classification breakdown, reference cards) but in a standalone full-page layout rather than inside an expandable table row.

## Requirements

### 1) Route

- **Path:** `/r/[shareToken]`
- **File:** `apps/frontend/app/r/[shareToken]/page.tsx`
- **Dynamic segment:** `shareToken` is the URL parameter

### 2) Data Fetching

The page MUST:
1. Extract `shareToken` from the URL parameters
2. Call `GET /api/shared/{shareToken}` (the frontend proxy from Step 05)
3. Handle loading, success, and error states

Data fetching MAY use server-side rendering (RSC) or client-side fetching. Server-side is PREFERRED for SEO and initial load performance.

### 3) Success State — Layout

When results are available, the page MUST display:

#### Header
- Biblio Checker logo/name (matching the main app header style)
- Subtitle: "Shared Analysis Report" (translated)
- File name of the analyzed document (if available)

#### Authenticity Score
- Reuse the `AuthenticityScore` component from `momento-wow`
- Same color semaphore (green/amber/red)
- Prominent placement at the top of results

#### Summary
- References detected / analyzed counts
- Classification breakdown (same layout as ExpandedDetail)

#### Reference Details
- Expandable reference cards (same as ExpandedDetail)
- Classification badge, confidence score, raw text, evidence
- All reference cards collapsed by default (user can expand individually)

#### Footer
- "Powered by Biblio Checker" branding
- Call-to-action: "Try Biblio Checker" link pointing to the home page (`/`)
- Share expiry notice: "This link expires on [date]" (translated)

### 4) Error State — Not Found / Expired

When the API returns 404, the page MUST display:
- Biblio Checker branding (header)
- A friendly message: "This shared analysis was not found or has expired" (translated)
- A call-to-action: "Try Biblio Checker" link pointing to the home page
- No technical error details

### 5) Loading State

While data is being fetched:
- Show Biblio Checker branding (header)
- Show a loading indicator (spinner or skeleton)
- Do not show empty result panels

### 6) Responsiveness

The page MUST be fully responsive:
- Desktop: centered content with comfortable max-width (e.g., `max-w-4xl`)
- Mobile: full-width with appropriate padding
- Reference cards stack vertically on all viewports

### 7) Theme

The page MUST respect the system's dark/light theme preference. It MUST use the same CSS variables and Tailwind classes as the main app.

### 8) Language

The page MUST use the browser's preferred language (from `Accept-Language` header or existing locale cookie) to determine which translations to use. The analysis results themselves are in the language set by the worker (`result.reportLanguage`).

### 9) No Authentication

The page MUST NOT require any authentication. The share token in the URL is the sole access credential.

### 10) Content Security

All `ResultsV1` string fields (`rawText`, `decisionReason`, `matchedRecord.title`, `matchedRecord.url`, `warnings[].message`) MUST be rendered as plain text only. No `dangerouslySetInnerHTML` or equivalent HTML injection method may be used on any user-controlled data. React's default JSX text escaping is sufficient.

URLs from evidence items (`matchedRecord.url`) MUST only be rendered as clickable links if they start with `https://` or `http://`. Other schemes MUST be rendered as plain text.

### 11) No Edit Actions

The page MUST be read-only. It MUST NOT display:
- Remove/delete buttons
- Re-analyze buttons
- Share button (the page itself IS the shared view)
- Export buttons (recipient sees results but cannot export in v1)

## Acceptance Criteria

- Navigating to `/r/<valid_token>` renders full analysis results
- The page shows AuthenticityScore with correct color semaphore
- Classification breakdown is visible
- Reference cards are expandable (collapsed by default)
- Navigating to `/r/<invalid_token>` shows a friendly "not found" page
- Navigating to `/r/<expired_token>` shows the same "not found" page
- The page works without any cookies, localStorage, or prior session
- The page is responsive on mobile (375px) and desktop (1440px)
- Dark/light theme is applied based on system preference
- "Try Biblio Checker" link navigates to the home page
- Share expiry date is displayed

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Share token is valid but `result` is null (validation failed) | Show branded page with "Results could not be loaded" message |
| Very slow backend response (> 5 seconds) | Loading state stays visible; no timeout on client side |
| User bookmarks the share page and opens it 31 days later | 404 — friendly "expired" message |
| User opens share page on a device with no JavaScript | SSR renders the page; interactive elements (expand cards) don't work |
| Language is PT but results are in ES | Page chrome is PT; result content (decisionReason, etc.) is ES |

## Integration Points

- Step 05 (Frontend Proxy) — fetches data from this proxy
- Reuses `AuthenticityScore` from `apps/frontend/components/recent-analyses/AuthenticityScore.tsx`
- Reuses reference card pattern from `apps/frontend/components/recent-analyses/ExpandedDetail.tsx`
- Uses i18n keys from Step 08

## Dependencies

- Step 05 (Frontend Proxy) — proxy must exist
- Step 08 (i18n Catalog) — provides translated strings
