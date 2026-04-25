# Step 02 — Routing Restructure

## Scope

This step specifies the file moves and route changes needed to free up `/` for the landing page and establish `/app` as the new home for the uploader.

This step does NOT cover:
- The landing page content (see Steps 03-10)
- The marketing layout (see Step 03)
- Query parameter behavior (see Step 11)

## Context

The current home page (`/`, file: `apps/frontend/app/page.tsx`) contains the complete uploader UI: FileDropzone, submit button, UploadStatus, and RecentAnalyses table. This must move to `/app` without losing any functionality. After the move, `/` is available for the new landing page.

## Requirements

### 1) Move Existing Page

The existing file `apps/frontend/app/page.tsx` MUST be moved to `apps/frontend/app/app/page.tsx`. All contents MUST be preserved verbatim — no logic changes.

### 2) Preserve All Behavior

The `/app` route MUST behave identically to the previous `/`:
- File upload flow (drag-and-drop + file picker)
- Submit/cancel buttons
- Upload progress (`UploadStatus`)
- Recent Analyses table with polling
- localStorage persistence
- Language and theme toggles in the header

### 3) Existing `/app` Route Check

The current URL structure has no `/app` route. A new directory `apps/frontend/app/app/` MUST be created with the moved `page.tsx`.

### 4) Update Share Page CTA

The share page at `apps/frontend/app/r/[shareToken]/page.tsx` currently has a "Try Biblio Checker" CTA that points to `/`. This MUST be updated to continue pointing to `/` (no change in destination), because `/` now shows the landing page — which is the correct destination for new users.

No changes are required to the share page code if the CTA already uses `/`. If it uses `/app` explicitly, change it to `/`.

### 5) Backward Compatibility

Users who have bookmarked `/` and expect the uploader to be there MUST be able to reach the uploader with minimal friction. The landing page's primary CTA ("Try now") links directly to `/app`, making this a one-click redirection.

No HTTP redirects from `/` to `/app` are specified. Breaking the bookmark is acceptable because:
- Visitors who bookmark `/` expecting the uploader will see the landing page with a prominent "Try now" button
- The one-click cost is lower than the conversion benefit of the landing page

### 6) Route Inventory After Change

| Path | Purpose | File |
|------|---------|------|
| `/` | Marketing landing page (new) | `app/(marketing)/page.tsx` (Step 03) |
| `/app` | Uploader + Recent Analyses | `app/app/page.tsx` (moved) |
| `/r/[shareToken]` | Public share page | `app/r/[shareToken]/page.tsx` (unchanged) |

## Acceptance Criteria

- `apps/frontend/app/app/page.tsx` exists and contains the previous home page content
- `apps/frontend/app/page.tsx` no longer exists (or is replaced by the marketing page from Step 03)
- Navigating to `/app` shows the uploader and Recent Analyses table
- File upload still works end-to-end
- Polling still works for active jobs
- localStorage jobs still display
- Language toggle still works on `/app`
- Theme toggle still works on `/app`
- Share page CTA points to `/` (which will show the new landing)
- No TypeScript errors after the move
- Existing tests still pass (ExpandedDetail test, file-dropzone test, etc.)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User has `/` bookmarked from before the change | Sees landing page; one click to `/app` to resume uploading |
| User is mid-upload when the deployment happens | No impact — upload already uses absolute API URLs, not path-dependent |
| Automated tests import from `app/page.tsx` | Tests must be updated to import from `app/app/page.tsx` if they reference it directly |
| Test that navigates to `/` expects uploader | Test must be updated to navigate to `/app` |

## Integration Points

- Step 03 (Marketing Layout) places the new landing page at `/`
- Step 11 (Sample Query Param) adds query parameter handling to the moved `/app/page.tsx`
- The share page's CTA destination is confirmed by this step

## Dependencies

- None (foundational step)
