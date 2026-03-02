-- =============================================================================
-- Migration: 20260301000001_fix_claim_rpc_for_split_tokens
-- Purpose:   Update claim_analysis_job RPC to use renamed column
--            (job_token_expires_at instead of token_expires_at) and simplify
--            Case A WHERE clause since backend no longer writes job_token_expires_at.
-- =============================================================================

DROP FUNCTION IF EXISTS public.claim_analysis_job(text, int);

CREATE OR REPLACE FUNCTION public.claim_analysis_job(
    p_token      text,
    p_lease_secs int DEFAULT 300
)
RETURNS SETOF analysis_jobs
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Input validation (unchanged from original)

    IF p_token IS NULL THEN
        RAISE EXCEPTION 'claim_analysis_job: p_token must not be NULL'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    IF length(p_token) < 32 OR length(p_token) > 64 THEN
        RAISE EXCEPTION 'claim_analysis_job: p_token length must be between 32 and 64 characters (got %)',
            length(p_token)
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    IF p_token !~ '^[A-Za-z0-9_\-]+$' THEN
        RAISE EXCEPTION 'claim_analysis_job: p_token contains disallowed characters; must match ^[A-Za-z0-9_-]+'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    IF p_lease_secs < 1 OR p_lease_secs > 3600 THEN
        RAISE EXCEPTION 'claim_analysis_job: p_lease_secs must be between 1 and 3600 (got %)',
            p_lease_secs
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- Core logic: atomic SELECT ... FOR UPDATE SKIP LOCKED + UPDATE RETURNING.
    --
    -- Eligible jobs — two cases:
    --
    --   Case A (queued):
    --     status = 'queued'
    --     Backend no longer writes job_token_expires_at, so queued jobs always
    --     have it NULL. Simplified to just status check.
    --
    --   Case B (running, crashed worker):
    --     status = 'running'
    --     AND job_token_expires_at IS NOT NULL
    --     AND job_token_expires_at < now()
    --
    --   Both cases require: attempts < max_attempts

    RETURN QUERY
    UPDATE analysis_jobs
    SET
        status               = 'running',
        stage                = 'created',
        job_token            = p_token,
        job_token_expires_at = now() + make_interval(secs => p_lease_secs),
        attempts             = attempts + 1,
        updated_at           = now()
    WHERE id = (
        SELECT id
        FROM   analysis_jobs
        WHERE  attempts < max_attempts
          AND  (
                   -- Case A: queued job (no lease to check)
                   status = 'queued'
                   OR
                   -- Case B: running job with expired lease (crashed worker)
                   (
                       status = 'running'
                       AND job_token_expires_at IS NOT NULL
                       AND job_token_expires_at < now()
                   )
               )
        ORDER BY created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING *;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.claim_analysis_job(text, int) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION public.claim_analysis_job(text, int) TO   service_role;
