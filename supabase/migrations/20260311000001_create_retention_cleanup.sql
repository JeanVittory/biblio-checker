-- =============================================================================
-- Migration: 20260311000001_create_retention_cleanup
-- Purpose:   Retention cleanup function that purges audit rows and completed
--            jobs older than a configurable number of days, while protecting
--            any job that is still active (queued or running).
--
-- Spec:      spec/audit-logging/04-retention-policy/spec.md
-- =============================================================================

-- Drop any pre-existing version of this function (idempotent).
DROP FUNCTION IF EXISTS public.cleanup_expired_data(int);

-- -----------------------------------------------------------------------------
-- Function: public.cleanup_expired_data
--
-- Deletes audit rows and completed analysis jobs that are older than
-- p_retention_days. Deletion is performed in two ordered phases to avoid
-- FK violations and to protect jobs that are still being processed.
--
-- Phase 1 — Orphan audit rows:
--   Deletes job_events and reference_audit_log rows whose created_at precedes
--   the cutoff, skipping any row whose parent job is still queued or running.
--
-- Phase 2 — Completed jobs:
--   Deletes analysis_jobs rows whose created_at precedes the cutoff and whose
--   status is 'succeeded' or 'failed'. ON DELETE CASCADE handles any remaining
--   child rows in both audit tables.
--
-- Parameters:
--   p_retention_days  int DEFAULT 7
--                     Number of days to retain data. Data older than this
--                     threshold (relative to now()) is eligible for deletion.
--
-- Returns:
--   jsonb  Summary object with keys:
--            cutoff           — the computed cutoff timestamp
--            deleted_events   — rows removed from job_events
--            deleted_references — rows removed from reference_audit_log
--            deleted_jobs     — rows removed from analysis_jobs
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.cleanup_expired_data(
    p_retention_days int DEFAULT 7
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_cutoff           timestamptz;
    v_deleted_events   int;
    v_deleted_references int;
    v_deleted_jobs     int;
BEGIN
    -- -------------------------------------------------------------------------
    -- Compute the retention cutoff timestamp.
    -- -------------------------------------------------------------------------
    v_cutoff := now() - make_interval(days => p_retention_days);

    -- -------------------------------------------------------------------------
    -- Phase 1 — Delete orphan audit rows, protecting active jobs.
    --
    -- A row is eligible only if its created_at is before the cutoff AND its
    -- parent job is not currently queued or running. The NOT EXISTS subquery
    -- acts as the active-job guard: any job in ('queued', 'running') is
    -- excluded regardless of its own age.
    -- -------------------------------------------------------------------------
    DELETE FROM public.job_events je
    WHERE je.created_at < v_cutoff
      AND NOT EXISTS (
          SELECT 1 FROM public.analysis_jobs aj
          WHERE aj.id = je.job_id
            AND aj.status IN ('queued', 'running')
      );
    GET DIAGNOSTICS v_deleted_events = ROW_COUNT;

    DELETE FROM public.reference_audit_log ral
    WHERE ral.created_at < v_cutoff
      AND NOT EXISTS (
          SELECT 1 FROM public.analysis_jobs aj
          WHERE aj.id = ral.job_id
            AND aj.status IN ('queued', 'running')
      );
    GET DIAGNOSTICS v_deleted_references = ROW_COUNT;

    -- -------------------------------------------------------------------------
    -- Phase 2 — Delete completed jobs.
    --
    -- Only terminal-status jobs (succeeded/failed) are removed. ON DELETE
    -- CASCADE propagates to any audit rows that were not already deleted in
    -- Phase 1 (e.g. rows that became eligible only because the job itself is
    -- being deleted now).
    -- -------------------------------------------------------------------------
    DELETE FROM public.analysis_jobs
    WHERE created_at < v_cutoff
      AND status IN ('succeeded', 'failed');
    GET DIAGNOSTICS v_deleted_jobs = ROW_COUNT;

    -- -------------------------------------------------------------------------
    -- Return a structured summary for the caller (e.g. a scheduled cron job
    -- or a monitoring script) to observe what was cleaned up.
    -- -------------------------------------------------------------------------
    RETURN jsonb_build_object(
        'cutoff',             v_cutoff,
        'deleted_events',     v_deleted_events,
        'deleted_references', v_deleted_references,
        'deleted_jobs',       v_deleted_jobs
    );
END;
$$;

-- -----------------------------------------------------------------------------
-- Permission model (spec section 4):
--   - Revoke EXECUTE from PUBLIC (deny-by-default after SECURITY DEFINER).
--   - Grant EXECUTE only to service_role (the scheduled maintenance connection).
-- -----------------------------------------------------------------------------
REVOKE EXECUTE ON FUNCTION public.cleanup_expired_data(int) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION public.cleanup_expired_data(int) TO service_role;
