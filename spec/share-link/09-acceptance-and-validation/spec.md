# Step 09 — Acceptance and Validation

## Scope

This step specifies end-to-end acceptance criteria and a verification plan for the Share Link feature.

## Requirements

### 1) End-to-End User Journeys

#### Journey 1: Professor Shares Results
1. Professor uploads a document and waits for analysis to complete
2. Professor expands the succeeded job in Recent Analyses
3. Professor clicks the "Share" button
4. A loading spinner appears briefly
5. The button changes to "Link copied!" with a checkmark
6. Professor pastes the URL in an email to a student
7. The URL format is `https://<domain>/r/<token>`

#### Journey 2: Student Opens Shared Link
1. Student receives the URL and opens it in a browser
2. The page shows Biblio Checker branding and "Shared Analysis Report"
3. The Authenticity Score is visible with color semaphore
4. The classification breakdown is visible
5. Reference cards are collapsed; student can expand any to see details
6. Footer shows "Powered by Biblio Checker" and "Try Biblio Checker" link
7. Share expiry date is visible

#### Journey 3: Expired Link
1. A recipient opens a share link that is more than 7 days old
2. The page shows Biblio Checker branding
3. A friendly message: "This shared analysis was not found or has expired"
4. A "Try Biblio Checker" link points to the home page
5. No technical error details are shown

#### Journey 4: Re-share (Idempotent)
1. Professor clicks "Share" on a job that was already shared
2. No API call is made (cached token is reused)
3. URL is copied to clipboard immediately
4. "Link copied!" feedback appears

#### Journey 5: Language
1. Professor shares a link while using the app in Spanish
2. Student opens the link with a browser set to Portuguese
3. Page chrome (header, footer, labels) is in Portuguese
4. Result content (decisionReason, etc.) is in the original analysis language

### 2) Regression Checklist

The following existing behaviors MUST NOT be regressed:

- [ ] File upload via drag-and-drop still works
- [ ] Job appears in Recent Analyses after submission
- [ ] Polling updates status in real-time
- [ ] Expanding a succeeded job shows reference details
- [ ] AuthenticityScore is visible for succeeded jobs
- [ ] Export CSV/PDF buttons work
- [ ] Remove button deletes job from list
- [ ] Page refresh preserves job history in localStorage
- [ ] Dark mode / light mode toggle works
- [ ] Language toggle (EN/ES/PT) works
- [ ] No TypeScript errors (`tsc --noEmit` passes)
- [ ] Existing tests pass (`vitest run` passes)
- [ ] Backend tests pass (`pnpm test:backend`)

### 3) Security Checklist

- [ ] Share token is generated using `secrets.token_urlsafe(24)` (cryptographically secure)
- [ ] Public read endpoint returns identical 404 for non-existent, expired, and non-shared tokens
- [ ] No `poll_status_token` or `job_token` is exposed in the public endpoint response
- [ ] No `bucket`, `path`, `sha256`, or storage details are exposed
- [ ] Share page does not allow any write operations
- [ ] UNIQUE constraint on `share_token` prevents collisions

### 4) Performance Criteria

| Metric | Threshold |
|--------|-----------|
| Share token generation (API) | < 500 ms |
| Public read endpoint | < 500 ms |
| Share page initial load (SSR) | < 2 seconds |
| Clipboard copy | < 100 ms |

### 5) Manual Testing Plan

| Test | Steps | Expected Result |
|------|-------|-----------------|
| Share happy path | Upload → succeed → expand → click Share | URL copied; paste shows valid URL |
| Open share link | Paste URL in new browser | Full results page with score |
| Open share link (mobile) | Paste URL on phone | Responsive layout; no horizontal scroll |
| Open expired link | Wait 30+ days (or manually expire in DB) | Friendly "not found" page |
| Open invalid link | Navigate to `/r/invalid_token_123` | Friendly "not found" page |
| Re-share same job | Click Share twice | Second click is instant (no loading) |
| Share while offline | Disconnect → click Share | Error message; retry works when reconnected |
| Dark mode share page | Open share link with dark mode | Correct theming |

## Acceptance Criteria

- All 5 user journeys pass end-to-end
- All regression checklist items pass
- All security checklist items pass
- Performance criteria are met
- All manual tests produce expected results

## Dependencies

- All previous steps (01-08) MUST be implemented before end-to-end validation
