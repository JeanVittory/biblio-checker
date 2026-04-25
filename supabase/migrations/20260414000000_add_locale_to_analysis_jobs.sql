-- =============================================================================
-- Migration: 20260414000000_add_locale_to_analysis_jobs
-- Purpose:   Add locale column to analysis_jobs so the worker can render
--            decisionReason and warnings[].message in the user's selected
--            language.
-- Supported locales: es (default), pt, en.
--
-- The claim_analysis_job RPC (20260228000000_create_claim_analysis_job_rpc.sql)
-- uses RETURNS SETOF analysis_jobs + RETURNING * — no RPC change is needed;
-- the new column is projected automatically.
-- =============================================================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'analysis_jobs' AND column_name = 'locale'
  ) THEN
    ALTER TABLE analysis_jobs
      ADD COLUMN locale TEXT NOT NULL DEFAULT 'es';
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name = 'analysis_jobs'
      AND constraint_name = 'analysis_jobs_locale_check'
  ) THEN
    ALTER TABLE analysis_jobs
      ADD CONSTRAINT analysis_jobs_locale_check
      CHECK (locale IN ('es', 'pt', 'en'));
  END IF;
END $$;

COMMENT ON COLUMN analysis_jobs.locale IS
  'Language the worker must use when rendering decisionReason and warning messages. Immutable after insert.';
