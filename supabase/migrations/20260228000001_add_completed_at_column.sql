-- =============================================================================
-- Migration: 20260228000001_add_completed_at_column
-- Purpose:   Add completed_at timestamp for tracking when jobs reach a
--            terminal state (succeeded or failed permanently).
--
-- The backend status controller reads this column and exposes it as
-- `completedAt` in the API response. The frontend displays it as a
-- relative time ("Completed 3 minutes ago" / "Failed 5 minutes ago").
-- =============================================================================

ALTER TABLE analysis_jobs
  ADD COLUMN IF NOT EXISTS completed_at timestamptz;
