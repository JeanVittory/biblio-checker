# Step 01 — Overview and Scope

## Overview

The **Share Link** feature enables users to generate a public URL for a completed analysis, allowing anyone with the link to view the results without authentication. This is the primary shareability mechanism for Biblio Checker: a professor validates a student's bibliography and shares the verdict via a simple link.

The user journey:

```
Analysis completes → User clicks "Share" → Token generated → URL copied to clipboard
→ Recipient opens URL → Sees branded results page with score, references, evidence
```

## Scope (In-Scope)

- On-demand share token generation (user must explicitly click "Share")
- A new `share_token` column on `analysis_jobs` with configurable TTL (default 7 days)
- Backend endpoint to generate share tokens (authenticated via `poll_status_token`)
- Backend endpoint to read shared results publicly (authenticated via `share_token` only)
- Frontend proxy route for the public read endpoint
- A standalone `/r/[shareToken]` page that renders full analysis results
- A "Share" button in the `ExpandedDetail` panel alongside export buttons
- Copy-to-clipboard with visual feedback ("Link copied!")
- Revoke sharing (optional: set `share_token` to null)
- i18n keys for all user-facing strings in EN, ES, PT

## Non-Scope (Out-of-Scope)

- Social media sharing (Open Graph meta tags, Twitter cards) — future enhancement
- QR code generation
- Password-protected share links
- Share analytics (view count, unique visitors)
- Editing or commenting on shared results
- Email delivery of share links
- Batch sharing (multiple jobs at once)
- Share link customization (custom slugs, vanity URLs)
- User accounts or authentication beyond the existing token model
- Changes to the worker pipeline or ResultsV1 contract

## Context

**Current State:**
When a job succeeds, the user can view results in `ExpandedDetail` and export as PDF/CSV. However, sharing requires sending the exported file via external channels (email, messaging). There is no way to share a live, interactive view of the results.

**Problem Addressed:**
A professor who validates 20 student bibliographies needs to share each verdict individually. Exporting and emailing PDFs is tedious. A shareable URL is faster, interactive, and always shows the latest data.

**Solution Design:**
An on-demand token system layered onto the existing `analysis_jobs` table. Share tokens are independent from `poll_status_token` (which expires after 1 hour) and have a longer TTL (7 days). The public read endpoint requires only the share token — no `jobId` or `jobToken` needed. The frontend `/r/[shareToken]` page is a new App Router route that fetches and renders results.

## User Personas

**Primary: Professor/Reviewer**
- Validates student bibliographies and needs to share verdicts
- Wants a simple URL to send via email, LMS, or messaging
- May share with multiple recipients (students, department, committee)

**Secondary: Student/Author**
- Receives a share link from professor or peer reviewer
- Views the analysis to understand which references were flagged
- May not have visited Biblio Checker before — the share page is their first contact

## Success Metrics

1. User clicks "Share" and gets a URL copied to clipboard in < 1 second
2. Recipient opens the URL and sees full results (score, references, evidence) without any login
3. The share page renders correctly on mobile and desktop
4. The share link works for 7 days after generation
5. After 7 days, the link returns a friendly "expired" message

## Constraints & Assumptions

- The existing dual-token model (`poll_status_token` + `job_token`) is unchanged
- Share tokens are stored on the existing `analysis_jobs` table (no new tables)
- The public read endpoint returns the same `ResultsV1` data as the authenticated endpoint
- Share tokens use `secrets.token_urlsafe(24)` producing 32-character URL-safe strings
- The frontend share page reuses existing components (`AuthenticityScore`, `ReferenceCard`)
- Supabase migrations are delivered as SQL files; user runs them manually
- The `cleanup_expired_data` RPC already handles data retention; share tokens expire with their parent job

## Dependencies

- None (this is the entry point for the suite)
