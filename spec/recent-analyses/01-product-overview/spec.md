# Step 01 — Product Overview and Scope

## Overview

The **Recent Analyses** feature allows users to track and monitor bibliography validation jobs submitted during their current browser session. After uploading a document for analysis, users will see a persistent table below the upload form that displays:
- All submitted jobs with real-time status updates
- Results and details when jobs complete
- The ability to expand rows for additional information and remove entries

This feature solves the core problem of job discoverability and progress tracking in a stateless, authentication-free environment by leveraging secure tokens and browser-based persistence.

## Scope (In-Scope)

This feature encompasses:
- A table component displayed on the same upload page (no new routes)
- Real-time job status polling (every 4 seconds) via a secure backend endpoint
- Browser localStorage persistence across page refreshes (per-device, per-browser only)
- Job access control via a short-lived token (1 hour TTL) returned at job creation
- Expandable rows showing job details: submission time, current status/stage, results, or errors
- Status badges indicating job state: queued, running, succeeded, failed, expired
- Row removal (deletion from the user's local list, not the database)
- Relative time display (e.g., "Just now", "5m ago", "2h ago")
- Error handling for invalid tokens, expired jobs, network failures

## Non-Scope (Out-of-Scope)

Explicitly excluded from this feature:
- Cross-device or cross-browser job synchronization
- User authentication or account creation
- Server-side job history or archival
- Email notifications or webhook callbacks
- Advanced analytics or job filtering/search
- Pagination (assume < 50 jobs per session)
- Export or bulk download of results
- Job re-submission or retry logic
- Multi-tab synchronization (localStorage is per-tab in many browsers)
- Admin or operator job management views
- Changes to the job creation process itself (only extending the response)

## Context

**Current State:**
The backend already has the ability to create analysis jobs and assign them unique `jobId` values. However, the frontend does not capture or persist this `jobId`, so users cannot track job progress.

**Problem Addressed:**
Users refresh the page and lose all context about submitted jobs. There is no way to know if a job is queued, running, or completed without re-submitting.

**Solution Design:**
A token-based access model ensures job privacy without requiring user authentication. Each job receives a unique token at creation; the frontend stores both `jobId` and `jobToken` in localStorage. The frontend polls a status endpoint at regular intervals; the endpoint validates the token and returns the current state. Tokens expire after 1 hour to limit exposure of old job IDs.

## User Personas

**Primary User: Academic Researcher**
- Uploads a PDF or DOCX containing a bibliography
- Wants to see if the validation job succeeded and what errors were found
- May leave the page and return later; expects the job to still be tracked
- Uses the same device/browser consistently

## Success Metrics

A user can:
1. Submit a document and immediately see it appear in the Recent Analyses table as "queued"
2. Watch the status update in real-time without manual refresh
3. Expand a completed job to view results
4. Return to the page hours later and still see the job in the table
5. Clear old jobs from their list by removing rows they no longer need

## Constraints & Assumptions

- No user login or cross-device state
- Token expiry is server-enforced; expired tokens return a specific HTTP status (401)
- Tokens are not refreshed during a job's lifetime
- Job IDs cannot be enumerated; same error response for "not found" and "wrong token"
- localStorage is the only persistence mechanism; cleared when browser data is wiped
