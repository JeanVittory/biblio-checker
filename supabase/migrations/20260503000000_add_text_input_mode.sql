-- =============================================================================
-- Migration: 20260503000000_add_text_input_mode
-- Purpose:   Extend analysis_jobs to support text-only input (single reference
--            paste flow). Adds input_kind discriminator and raw_reference_text
--            payload column; makes four file-specific columns nullable; enforces
--            per-mode field presence via a named CHECK constraint.
--
-- Spec:      spec/single-reference-text-check/02-database-schema/spec.md
--
-- RPC note:  claim_analysis_job (20260301000001_fix_claim_rpc_for_split_tokens)
--            returns SETOF analysis_jobs and uses RETURNING * (line 88). New
--            columns are projected automatically — no CREATE OR REPLACE needed.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Add input_kind column (discriminator)
--    DEFAULT 'file' ensures all existing rows are immediately valid.
-- -----------------------------------------------------------------------------
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'analysis_jobs' AND column_name = 'input_kind'
  ) THEN
    ALTER TABLE analysis_jobs
      ADD COLUMN input_kind TEXT NOT NULL DEFAULT 'file';
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name = 'analysis_jobs'
      AND constraint_name = 'analysis_jobs_input_kind_check'
  ) THEN
    ALTER TABLE analysis_jobs
      ADD CONSTRAINT analysis_jobs_input_kind_check
      CHECK (input_kind IN ('file', 'text'));
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 2) Add raw_reference_text column (text-mode payload)
--    VARCHAR(2000) mirrors the Pydantic 2000-char limit as defense-in-depth.
-- -----------------------------------------------------------------------------
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'analysis_jobs' AND column_name = 'raw_reference_text'
  ) THEN
    ALTER TABLE analysis_jobs
      ADD COLUMN raw_reference_text VARCHAR(2000) NULL;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 3) Drop NOT NULL from the four file-specific columns
--    ALTER COLUMN … DROP NOT NULL is a no-op if the column is already nullable,
--    so these statements are inherently idempotent.
-- -----------------------------------------------------------------------------
ALTER TABLE analysis_jobs ALTER COLUMN bucket      DROP NOT NULL;
ALTER TABLE analysis_jobs ALTER COLUMN path        DROP NOT NULL;
ALTER TABLE analysis_jobs ALTER COLUMN sha256      DROP NOT NULL;
ALTER TABLE analysis_jobs ALTER COLUMN source_type DROP NOT NULL;

-- -----------------------------------------------------------------------------
-- 4) Explicit safety backfill
--    The DEFAULT 'file' already covers existing rows at DDL time, but an
--    explicit UPDATE guards against any edge case (e.g. a replication lag
--    window, a partial restore) where the default was not applied.
-- -----------------------------------------------------------------------------
UPDATE analysis_jobs
SET input_kind = 'file'
WHERE input_kind IS NULL;

-- -----------------------------------------------------------------------------
-- 5) Per-mode consistency CHECK constraint
--    file  → file fields NOT NULL, raw_reference_text IS NULL
--    text  → file fields IS NULL,  raw_reference_text IS NOT NULL
-- -----------------------------------------------------------------------------
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name = 'analysis_jobs'
      AND constraint_name = 'analysis_jobs_input_kind_consistency'
  ) THEN
    ALTER TABLE analysis_jobs
      ADD CONSTRAINT analysis_jobs_input_kind_consistency CHECK (
        (
          input_kind = 'file'
          AND bucket IS NOT NULL
          AND path IS NOT NULL
          AND sha256 IS NOT NULL
          AND source_type IS NOT NULL
          AND raw_reference_text IS NULL
        )
        OR
        (
          input_kind = 'text'
          AND bucket IS NULL
          AND path IS NULL
          AND sha256 IS NULL
          AND source_type IS NULL
          AND raw_reference_text IS NOT NULL
        )
      );
  END IF;
END $$;

COMMENT ON COLUMN analysis_jobs.input_kind IS
  'Discriminator: ''file'' for document-upload jobs, ''text'' for single-reference paste jobs. Immutable after insert.';

COMMENT ON COLUMN analysis_jobs.raw_reference_text IS
  'Pasted reference text for text-mode jobs (input_kind = ''text''). NULL for file-mode jobs. Capped at 2000 chars at the DB layer as defense-in-depth.';
