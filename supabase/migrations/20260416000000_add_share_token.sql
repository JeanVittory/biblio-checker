-- Migration: add share token columns to analysis_jobs
--
-- Adds two nullable columns used by the Share Link feature:
--   share_token             – URL-safe token; NULL when not shared
--   share_token_expires_at  – expiry timestamp; NULL when not shared
--
-- The UNIQUE constraint on share_token prevents collisions and provides
-- an implicit index for the public-read lookup (GET /api/analysis/shared/{token}).
--
-- Backward compatible: all existing rows receive NULL for both columns.
-- No existing columns are altered or dropped.

ALTER TABLE analysis_jobs
    ADD COLUMN IF NOT EXISTS share_token TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS share_token_expires_at TIMESTAMPTZ;
