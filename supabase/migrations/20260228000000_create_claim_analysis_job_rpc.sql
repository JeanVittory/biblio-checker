-- =============================================================================
-- Migration: 20260228000000_create_claim_analysis_job_rpc
-- Purpose:   Atomic job-claiming RPC for the background worker.
--
-- Spec:      spec/worker-framework/02-atomic-job-claiming/spec.md
-- Corrections applied (tech lead + security reviews):
--   #1  Crash-recovery filter: also reclaim status='running' jobs whose
--       token_expires_at has expired (worker crashed without clearing lease).
--   #2  SET search_path = public to prevent schema injection with SECURITY DEFINER.
--   #3  Input validation for p_token (NOT NULL, length 32-64, charset) and
--       p_lease_secs (range 1-3600).
--   #4  Interval syntax: make_interval(secs => p_lease_secs) instead of the
--       invalid arithmetic expression now() + p_lease_secs.
--
-- Pre-flight checks (performed before writing this migration):
--   - analysis_jobs.stage CHECK constraint already contains 'extract_done'
--     and 'done' — no ALTER needed.
--   - analysis_jobs has no 'completed_at' column — to be handled separately.
-- =============================================================================

-- Drop any pre-existing version of this function (idempotent).
DROP FUNCTION IF EXISTS public.claim_analysis_job(text, int);

-- -----------------------------------------------------------------------------
-- Function: public.claim_analysis_job
--
-- Atomically selects one eligible job from analysis_jobs, transitions it to
-- status='running', and returns the updated row. Returns an empty set when no
-- eligible job exists. At most one row is ever returned.
--
-- Parameters:
--   p_token      text        Worker-generated lease token. Must be 32-64
--                            characters, matching ^[A-Za-z0-9_\-]+$.
--   p_lease_secs int DEFAULT 300
--                            Lease duration in seconds (1 to 3600).
--
-- Returns: SETOF analysis_jobs (0 rows = nothing to do; 1 row = job claimed)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.claim_analysis_job(
    p_token      text,
    p_lease_secs int DEFAULT 300
)
RETURNS SETOF analysis_jobs
LANGUAGE plpgsql
SECURITY DEFINER
-- Correction #2: fix search_path to prevent schema injection when the
-- function runs under the owner's privileges.
SET search_path = public
AS $$
BEGIN
    -- -------------------------------------------------------------------------
    -- Correction #3: Input validation.
    -- -------------------------------------------------------------------------

    -- p_token: explicit NULL check (PL/pgSQL does not enforce NOT NULL on params)
    IF p_token IS NULL THEN
        RAISE EXCEPTION 'claim_analysis_job: p_token must not be NULL'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- p_token: length 32-64
    IF length(p_token) < 32 OR length(p_token) > 64 THEN
        RAISE EXCEPTION 'claim_analysis_job: p_token length must be between 32 and 64 characters (got %)',
            length(p_token)
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- p_token: restricted character class
    IF p_token !~ '^[A-Za-z0-9_\-]+$' THEN
        RAISE EXCEPTION 'claim_analysis_job: p_token contains disallowed characters; must match ^[A-Za-z0-9_-]+'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- p_lease_secs: range 1-3600 (max 1 hour)
    -- Note: the base spec edge-case table mentions p_lease_secs=0 as "valid but
    -- not recommended". The security review overrides this — minimum is 1.
    IF p_lease_secs < 1 OR p_lease_secs > 3600 THEN
        RAISE EXCEPTION 'claim_analysis_job: p_lease_secs must be between 1 and 3600 (got %)',
            p_lease_secs
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- -------------------------------------------------------------------------
    -- Core logic: atomic SELECT ... FOR UPDATE SKIP LOCKED + UPDATE RETURNING.
    --
    -- Eligible jobs — two cases (Correction #1, crash-recovery fix):
    --
    --   Case A (queued, no active lease):
    --     status = 'queued'
    --     AND (token_expires_at IS NULL OR token_expires_at < now())
    --     Covers the initial NULL written by the backend and any queued row
    --     whose lease was never set or has expired.
    --
    --   Case B (running, crashed worker):
    --     status = 'running'
    --     AND token_expires_at IS NOT NULL
    --     AND token_expires_at < now()
    --     The worker died without clearing its lease; re-claim is safe once
    --     the TTL has elapsed. NULL is excluded here: a running row with no
    --     token_expires_at is an inconsistent state that must not be blindly
    --     reclaimed.
    --
    --   Both cases require: attempts < max_attempts
    --
    -- Order by created_at ASC (FIFO). LIMIT 1 ensures single-row claim.
    -- FOR UPDATE SKIP LOCKED prevents double-claiming under concurrency.
    --
    -- Correction #4: make_interval(secs => p_lease_secs) is the correct way
    -- to build an interval from an integer in PL/pgSQL.
    -- -------------------------------------------------------------------------
    RETURN QUERY
    UPDATE analysis_jobs
    SET
        status           = 'running',
        stage            = 'created',
        job_token        = p_token,
        token_expires_at = now() + make_interval(secs => p_lease_secs),
        attempts         = attempts + 1,
        updated_at       = now()
    WHERE id = (
        SELECT id
        FROM   analysis_jobs
        WHERE  attempts < max_attempts
          AND  (
                   -- Case A: queued job, no live lease
                   (
                       status = 'queued'
                       AND (token_expires_at IS NULL OR token_expires_at < now())
                   )
                   OR
                   -- Case B: running job with a provably expired lease (crashed worker)
                   (
                       status = 'running'
                       AND token_expires_at IS NOT NULL
                       AND token_expires_at < now()
                   )
               )
        ORDER BY created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING *;
END;
$$;

-- -----------------------------------------------------------------------------
-- Permission model (spec section 6):
--   - Revoke EXECUTE from PUBLIC (deny-by-default after SECURITY DEFINER).
--   - Grant EXECUTE only to service_role (the worker's Supabase connection role).
-- -----------------------------------------------------------------------------
REVOKE EXECUTE ON FUNCTION public.claim_analysis_job(text, int) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION public.claim_analysis_job(text, int) TO   service_role;
