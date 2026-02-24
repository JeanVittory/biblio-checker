# Step 11 — Upload Flow Integration

## Scope

This step specifies how the upload form integrates with the Recent Analyses feature. It covers:
- Changes to the upload success handler
- Capturing jobId and jobToken from the response
- Adding a new job to the Recent Analyses table
- Error handling (missing jobId or jobToken)
- Extracting and storing the file name

This step does NOT cover:
- Upload form UI or styling (existing)
- File validation (existing)
- Error handling for upload failures (existing; only success case is modified)
- Request construction or backend communication (existing)
- Form submission mechanics (existing)

## Context

Currently, when a user uploads a document, the backend returns a success response, and the frontend displays a generic "Upload successful" message. The jobId and jobToken from the response are discarded.

With the Recent Analyses feature, the upload success handler must now:
1. Extract the jobId and jobToken from the backend response
2. Extract the file name from the submitted file
3. Add a new row to the Recent Analyses table
4. Handle cases where jobId or jobToken are missing (skip silently)

## Requirements

1. After a successful file upload (HTTP 200/201), the upload handler must attempt to extract:
   - `jobId` from the response body
   - `jobToken` from the response body
   - File name from the submitted File object (native browser API)

2. If both `jobId` and `jobToken` are present and non-empty, the handler must:
   - Call `addJob(jobId, jobToken, fileName)` (Step 07 — Frontend Data Model)
   - The new job is immediately added to localStorage with status `queued`
   - Polling starts for the new job (Step 08 — Frontend Polling)
   - The Recent Analyses table appears (or updates) with the new row

3. If either `jobId` or `jobToken` is missing or falsy:
   - Silently skip adding the job to the Recent Analyses table
   - Do not show an error message to the user
   - The upload is still considered successful (from the user's perspective)
   - No exception is thrown; execution continues normally

4. The file name is extracted from the File object's `name` property (e.g., "thesis.pdf", "bibliography.docx").

5. If the file name is missing or empty (unlikely), use a default name (e.g., "Document").

6. The upload success message is displayed to the user regardless of whether the job was added to the table.

7. The upload form should be reset (cleared) after a successful upload, as it currently is (no change).

8. If `addJob()` throws an error (e.g., localStorage quota exceeded), the error is caught and reported to the user (Step 06 — Error Definitions), but the upload is still considered successful.

## Upload Success Flow (Detailed Steps)

1. **Submission:** User selects a file and clicks "Upload"
2. **Backend Request:** Form is submitted to the backend
3. **Backend Response:** Server returns HTTP 200/201 with response body containing `jobId`, `jobToken`, and optional success message
4. **Response Parsing:** Frontend parses the JSON response
5. **Job Capture:** Frontend attempts to extract `jobId` and `jobToken`
6. **File Name Extraction:** Frontend extracts the file name from the File object
7. **Add to Table:** If both `jobId` and `jobToken` are present, call `addJob()` to add the job to localStorage
8. **Polling Start:** Polling mechanism (Step 08) automatically starts polling for the new job (next 4-second interval)
9. **Success Message:** Success message is displayed to the user (existing behavior)
10. **Form Reset:** Upload form is cleared (existing behavior)
11. **UI Update:** Recent Analyses table becomes visible (or updates) with the new row

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Response includes `jobId` but not `jobToken` | Job is not added to the table (both are required); upload is still considered successful |
| Response includes `jobToken` but not `jobId` | Job is not added to the table (both are required); upload is still considered successful |
| Response includes empty strings for `jobId` or `jobToken` | Job is not added to the table; upload is still considered successful |
| Response includes `jobId` and `jobToken` but they are non-string types (e.g., numbers) | Job is not added (or coerced to strings if safe); upload is still considered successful |
| File object has no `name` property | Default name (e.g., "Document") is used |
| File name includes special characters (e.g., "résumé.pdf", "document (1).docx") | File name is stored and displayed as-is |
| File name is very long (e.g., 500 characters) | File name is stored fully; UI truncates it for display (Step 10) |
| localStorage quota is exceeded when adding the job | Error is caught; user is shown a quota warning (Step 06); upload is still successful |
| Upload succeeds, but job is not added due to an error (not quota-related) | Warning is logged; user is shown a message to refresh the page if they want to track the job |
| User closes the browser tab immediately after upload | Job is stored in localStorage before the tab closes (assuming no JavaScript errors) |
| User uploads multiple files in rapid succession | Each job is added to the table independently; table shows multiple rows, newest first |

## Error Handling

**Successful Upload, Job Added to Table:**
- Success message displayed
- Row appears in Recent Analyses table
- Polling starts automatically

**Successful Upload, Job Not Added (Missing jobId/jobToken):**
- Success message displayed
- No row in the table
- User does not need to know; upload is still successful
- If user cares about the job, they can refresh the page or check manually

**Successful Upload, localStorage Quota Exceeded:**
- Success message displayed
- Job is not added to localStorage
- Warning message is shown: "Unable to save job to table. Storage is full. Please clear browser data or remove old jobs."
- User can free space and re-upload if needed

**Response Parsing Error (Malformed JSON):**
- Upload succeeds (file is stored in backend)
- Job is not added to the table (unable to extract jobId/jobToken)
- No error message is shown (graceful degradation)
- User can refresh the page to see the job if they want to wait for status

## Integration Points

- **Upload Form:** Existing form handler is extended to capture and store jobId/jobToken
- **Backend Response:** Must include jobId and jobToken (Step 04 — Job Creation Endpoint)
- **File Object:** Browser File API (`File.name` property)
- **localStorage Helpers:** Calls `addJob()` (Step 07 — Frontend Data Model)
- **Polling:** New job is automatically polled (Step 08 — Frontend Polling)
- **Recent Analyses Table:** New row appears in the table (Step 10 — Frontend UI)

## Acceptance Criteria

- After a successful upload with jobId and jobToken in the response, a new row appears in the Recent Analyses table
- The new row displays the file name, current time (relative), and "Queued" status
- The new row is added at the top of the table (newest first)
- Polling starts for the new job within ~4 seconds
- If jobId is missing from the response, no row is added and no error is shown
- If jobToken is missing from the response, no row is added and no error is shown
- If the file name cannot be extracted, a default name is used
- If localStorage quota is exceeded, a warning is shown but the upload is still successful
- Multiple rapid uploads result in multiple rows in the table, with the latest first
- The upload form is cleared after successful submission (existing behavior preserved)
- The upload success message is displayed regardless of whether the job was added to the table

## Performance Considerations

- Extracting jobId and jobToken is a simple object property access (negligible performance impact)
- Calling `addJob()` is a synchronous localStorage write (fast, but blocks the main thread briefly)
- For the typical case (< 50 jobs), performance is not a concern
- If localStorage operations become a bottleneck, they can be moved to a Web Worker in a future iteration

## Testing Scenarios

1. **Happy Path:** Upload a document; response includes jobId and jobToken; new row appears in the table; polling starts
2. **Missing jobId:** Upload a document; response includes jobToken but not jobId; no row is added; upload is successful
3. **Missing jobToken:** Upload a document; response includes jobId but not jobToken; no row is added; upload is successful
4. **Storage Quota Exceeded:** Add many jobs until localStorage quota is reached; attempt another upload; warning is shown; user can free space
5. **Rapid Uploads:** Upload 3 documents in quick succession; all 3 rows appear in the table (newest first); each is polled independently
6. **Special Characters in File Name:** Upload a file with special characters (e.g., "my-résumé (v3).pdf"); file name is displayed correctly

## Dependencies

- Depends on Step 04 (Job Creation Endpoint) for jobId and jobToken in the response
- Depends on Step 07 (Frontend Data Model) for `addJob()` helper and localStorage structure
- Depends on Step 08 (Frontend Polling) for automatic polling of new jobs
- Depends on Step 10 (Frontend UI) for rendering the Recent Analyses table
