# Step 06 — Extract Stage

## Scope

- Define the extract stage: download file from Supabase Storage and verify its SHA-256 hash
- Populate the `file_bytes` field in `JobContext`
- Advance the job stage to `extract_done`

**Out of scope:** Text extraction from PDF/DOCX (future work). LangGraph invocation (see Step 07).

## Context

When a user uploads a document, the backend stores it in Supabase Storage and records the `bucket`, `path`, `sha256`, and `source_type` in the `analysis_jobs` row. The extract stage is the first processing step: it downloads the file and verifies its integrity before any analysis begins.

The backend already has SHA-256 verification logic in `apps/backend/app/services/integrity.py`. The worker duplicates this logic locally (per the design decision to keep apps independent).

## Requirements

### 1. Module Location

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/extract.py`

**Public function:** `extract_stage(*, supabase: Client, ctx: JobContext) -> None`

### 2. Processing Steps

The stage executes these steps in order:

**Step 2.1 — Download file from Storage**

Download the file bytes using the Supabase Storage client:
```
file_bytes = supabase.storage.from_(ctx.job.bucket).download(ctx.job.path)
```

If the download fails (any exception from the storage client), raise:
`StageError(code="storage_download_failed", detail=<exception message>, transient=True)`

A storage failure is transient because it could be a temporary network issue or Supabase outage.

**Step 2.2 — Verify SHA-256**

Compute the SHA-256 hash of the downloaded bytes and compare against `ctx.job.sha256`:
1. Compute: `hashlib.sha256(file_bytes).hexdigest()`
2. Compare (case-insensitive) against `ctx.job.sha256`
3. If mismatch, raise: `TerminalJobError(code="integrity_sha_mismatch", detail="expected=<expected> actual=<actual>")`

A SHA mismatch is a terminal error because:
- The file in storage does not match what was recorded at upload time
- Retrying will download the same corrupted/mismatched file
- This indicates data corruption or a storage inconsistency that requires manual investigation

**Step 2.3 — Populate context**

Set `ctx.file_bytes = file_bytes`

**Step 2.4 — Advance stage**

Call `repo.update_stage(supabase, job_id=ctx.job.id, stage=JobStage.EXTRACT_DONE, token=ctx.job.job_token)`

If `update_stage` raises `JobRepoError`, let it propagate (the pipeline runner will handle it as an unexpected exception).

### 3. Stage Ordering

This stage runs FIRST in the pipeline. It expects `ctx.file_bytes` to be empty (`b""`) at entry. After successful execution, `ctx.file_bytes` contains the raw document bytes.

### 4. Error Classification Summary

| Error condition | Error type | Code | Transient |
|----------------|------------|------|-----------|
| Storage download exception | `StageError` | `storage_download_failed` | Yes |
| SHA-256 mismatch | `TerminalJobError` | `integrity_sha_mismatch` | N/A (always terminal) |
| `update_stage` DB error | `JobRepoError` | (from repo) | N/A (handled by runner) |

## Acceptance Criteria

- The stage downloads the file using `supabase.storage.from_(bucket).download(path)`
- The stage computes SHA-256 of downloaded bytes and compares against `ctx.job.sha256`
- SHA mismatch raises `TerminalJobError` with code `integrity_sha_mismatch`
- Storage download failure raises `StageError` with `transient=True`
- On success, `ctx.file_bytes` contains the downloaded bytes
- On success, the job stage is advanced to `extract_done` via `repo.update_stage`
- The token guard is passed to `update_stage` via `token=ctx.job.job_token`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| File does not exist in Storage (404) | Storage client raises exception -> `StageError(transient=True)`. Will be retried, but likely to fail again. After `max_attempts`, permanently failed. |
| File exists but is empty (0 bytes) | SHA-256 of empty bytes is compared against stored hash. If stored hash matches empty-file hash, it proceeds (the LangGraph stage will handle empty content). If mismatch, `TerminalJobError`. |
| Storage returns different bytes on retry (race with deletion) | SHA verification catches this as a mismatch -> `TerminalJobError`. This is correct: the file changed after job creation. |
| Network timeout during download | Storage client raises exception -> `StageError(transient=True)`. Next attempt may succeed. |

## Integration Points

- **Step 04:** Calls `repo.update_stage` to advance to `extract_done`
- **Step 05:** Follows the stage function contract defined in the pipeline framework
- **Step 07:** The next stage (langgraph) reads `ctx.file_bytes`

## Dependencies

- **Depends on:** Step 04 (repo.update_stage), Step 05 (stage contract, JobContext)
- **Informs:** Step 07 (provides file_bytes for LangGraph processing)
