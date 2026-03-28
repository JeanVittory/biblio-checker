-- =============================================================================
-- Migration: 20260318000000_create_renew_lease_rpc
-- Purpose:   Create renew_analysis_job_lease RPC so workers can extend their
--            lease while actively processing a long-running job, preventing
--            spurious reclaims by other workers.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.renew_analysis_job_lease(
    p_job_id     uuid,
    p_token      text,
    p_lease_secs int DEFAULT 300
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    rows_updated int;
BEGIN
    IF p_lease_secs < 1 OR p_lease_secs > 7200 THEN
        RAISE EXCEPTION 'renew_analysis_job_lease: p_lease_secs must be between 1 and 7200 (got %)',
            p_lease_secs
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    UPDATE analysis_jobs
    SET
        job_token_expires_at = now() + p_lease_secs * interval '1 second',
        updated_at           = now()
    WHERE id        = p_job_id
      AND job_token = p_token
      AND status    = 'running';

    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RETURN rows_updated > 0;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.renew_analysis_job_lease(uuid, text, int) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION public.renew_analysis_job_lease(uuid, text, int) TO   service_role;
