# Step 07 — Share Button

## Scope

This step specifies the UI button that generates a share link and copies it to the user's clipboard. It covers:
- Button placement and appearance
- Click behavior (generate + copy)
- Visual feedback states
- Error handling

This step does NOT cover:
- Token generation backend logic (see Step 03)
- The share page (see Step 06)

## Context

The share button is placed alongside the existing export buttons (CSV, PDF) in the `ExpandedDetail` panel footer for succeeded jobs. When clicked, it calls the backend to generate a share token, constructs the full URL, and copies it to the clipboard.

## Requirements

### 1) Placement

The share button MUST appear in the `ExpandedDetail` panel for succeeded jobs, in the footer area alongside the existing `ExportButtons` component and the completion timestamp.

### 2) Button Appearance

- Icon: link/chain icon (e.g., `Link2` or `Share2` from lucide-react)
- Label: translated via `results.share.button` (default: "Share")
- Style: consistent with the export buttons (same size, colors, hover states)

### 3) Click Behavior — First Share

When the user clicks the button and the job has NOT been shared yet:

1. Button enters loading state (spinner, disabled)
2. Frontend calls `POST /api/analysis/share` (the Next.js proxy from Step 05) with `jobId` and `jobToken` in the JSON body
3. Backend returns `shareToken` and `expiresAt`
4. Frontend constructs the full URL: `{window.location.origin}/r/{shareToken}`
5. Frontend copies the URL to the clipboard via `navigator.clipboard.writeText()`
6. Button shows success state: icon changes to checkmark, label changes to "Link copied!" (translated)
7. Success state reverts to default after 3 seconds

### 4) Click Behavior — Already Shared

If the job already has a share token (cached from a previous click):

1. Frontend uses the cached token (no API call needed)
2. Constructs URL and copies to clipboard immediately
3. Shows success state

### 5) Click Behavior — Share Token Expired

If the cached token has expired (compare `expiresAt` with `Date.now()`):

1. Frontend calls the backend to generate a new token
2. Follows the "First Share" flow

### 6) Error Handling

If the share token generation fails:
- Button returns to default state
- A brief error message appears near the button (e.g., "Could not generate link")
- Error clears after 4 seconds
- User can retry

If clipboard copy fails (e.g., permissions denied):
- Show the URL in a tooltip or inline text so the user can manually copy
- Label changes to "Link ready" instead of "Link copied!"

### 7) Conditional Rendering

The share button MUST only render when:
- Job status is `succeeded`
- `result` is not null
- `jobToken` is available (needed for the API call)

### 8) State Management

The component MUST track:
- `shareToken: string | null` — cached token from API response
- `expiresAt: string | null` — cached expiry
- `loading: boolean` — API call in progress
- `copied: boolean` — clipboard copy succeeded (auto-resets after 3s)
- `error: boolean` — API call or clipboard failed (auto-resets after 4s)

### 9) Accessibility

- Button MUST be keyboard accessible (Tab, Enter/Space)
- Button MUST have `aria-label` describing the action (e.g., "Generate shareable link")
- Loading state MUST use `aria-busy="true"`
- Success state MUST announce "Link copied to clipboard" to screen readers

## Acceptance Criteria

- Share button is visible in ExpandedDetail for succeeded jobs
- First click generates token, copies URL, shows "Link copied!"
- Second click reuses cached token, copies URL immediately (no API call)
- URL format is `{origin}/r/{shareToken}`
- Loading spinner shown during API call
- Error state shown when API fails; user can retry
- Clipboard failure shows URL inline for manual copy
- Button not visible for queued/running/failed jobs
- Button label translates correctly in EN/ES/PT

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User clicks Share, then removes the job | Share button disappears with the job row |
| User clicks Share while offline | Error state; retry available when back online |
| Clipboard API not available (older browser) | URL shown inline as text |
| User clicks Share multiple times rapidly | Button disabled during loading; only one API call |
| `poll_status_token` expired (> 1 hour after creation) | API returns 401; error state shown |

## Integration Points

- Step 03 (Share Token Generation) — the backend endpoint called via proxy
- Step 05 (Frontend Proxy) — calls `POST /api/analysis/share` proxy route (MUST use proxy, never call backend directly)
- Integrated into `ExpandedDetail` component alongside `ExportButtons`
- Uses i18n keys from Step 08

## Dependencies

- Step 03 (Share Token Generation) — backend endpoint must exist
- Step 08 (i18n Catalog) — provides translated labels
