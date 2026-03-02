-- =============================================================================
-- Migration: 20260301000000_split_poll_and_lease_tokens
-- Purpose:   Separate frontend polling auth token from worker lease token.
--
-- Before this migration, job_token and token_expires_at served dual purpose:
--   1. Frontend auth for status polling (TTL 1h)
--   2. Worker lease for exclusive processing (TTL 5min)
-- When the worker claimed a job it overwrote both, breaking frontend access.
--
-- After this migration:
--   poll_status_token / poll_status_token_expires_at → frontend auth (immutable)
--   job_token / job_token_expires_at                 → worker lease (renamed)
-- =============================================================================

-- New columns for frontend polling auth
ALTER TABLE analysis_jobs
  ADD COLUMN IF NOT EXISTS poll_status_token text,
  ADD COLUMN IF NOT EXISTS poll_status_token_expires_at timestamptz;

-- Rename for symmetry with job_token
ALTER TABLE analysis_jobs
  RENAME COLUMN token_expires_at TO job_token_expires_at;
