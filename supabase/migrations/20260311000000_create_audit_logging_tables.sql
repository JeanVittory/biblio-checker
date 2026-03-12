-- =============================================================================
-- Migration: 20260311000000_create_audit_logging_tables
-- Purpose:   Audit logging tables for job lifecycle events and per-reference
--            classification results.
--
-- Spec:      spec/audit-logging/02-job-events-schema/spec.md
--            spec/audit-logging/03-reference-audit-schema/spec.md
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: public.job_events
--
-- Records discrete lifecycle events for each analysis job. One row per event
-- transition (e.g. job_created, job_claimed, stage_changed, job_succeeded,
-- job_failed, job_requeued). Rows are append-only; no UPDATE is expected.
--
-- Columns:
--   id           bigint   Surrogate PK, system-generated.
--   job_id       uuid     FK → analysis_jobs(id). Cascades on job deletion.
--   event_type   text     Discriminator; restricted to the canonical event set.
--   stage        text     Pipeline stage at time of event; NULL when not applicable.
--   status       text     Job status at time of event; NULL when not applicable.
--   error_code   text     Structured error code; NULL for non-error events.
--   error_detail text     Human-readable error detail; NULL for non-error events.
--   attempt      int      Attempt counter at time of event; NULL when not applicable.
--   metadata     jsonb    Arbitrary structured context (e.g. duration_ms, source).
--   created_at   timestamptz  Wall-clock timestamp when the event was recorded.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.job_events (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id       uuid        NOT NULL
                     REFERENCES public.analysis_jobs(id) ON DELETE CASCADE,
    event_type   text        NOT NULL
                     CHECK (event_type IN (
                         'job_created',
                         'job_claimed',
                         'stage_changed',
                         'job_succeeded',
                         'job_failed',
                         'job_requeued'
                     )),
    stage        text,
    status       text,
    error_code   text,
    error_detail text,
    attempt      int,
    metadata     jsonb       NOT NULL DEFAULT '{}',
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_job_events_job_id
    ON public.job_events (job_id);

CREATE INDEX IF NOT EXISTS idx_job_events_created_at
    ON public.job_events (created_at);

-- -----------------------------------------------------------------------------
-- Permission model for job_events:
--   - Revoke all access from PUBLIC (deny-by-default).
--   - Grant SELECT and INSERT to service_role (backend and worker connections).
--   - Grant USAGE on the identity sequence to service_role so INSERT works.
-- -----------------------------------------------------------------------------
REVOKE ALL   ON public.job_events FROM PUBLIC;
GRANT  SELECT, INSERT ON public.job_events TO service_role;
GRANT  USAGE  ON SEQUENCE public.job_events_id_seq TO service_role;

-- -----------------------------------------------------------------------------
-- Table: public.reference_audit_log
--
-- Records the per-reference classification outcome produced by the pipeline for
-- each analysis job. One row per (job_id, reference_id) pair. Rows are
-- append-only; no UPDATE is expected.
--
-- Columns:
--   id                bigint   Surrogate PK, system-generated.
--   job_id            uuid     FK → analysis_jobs(id). Cascades on job deletion.
--   reference_id      text     Stable identifier for the reference within its job.
--   raw_text          text     Original reference string as extracted; NULL if unavailable.
--   classification    text     Classification label (e.g. 'verified', 'hallucinated').
--   confidence_score  double precision  Model confidence in [0, 1]; NULL if not produced.
--   reason_code       text     Structured reason code for the classification; NULL if not produced.
--   sources_checked   text[]   Ordered list of external sources consulted.
--   match_found       boolean  Whether at least one source returned a positive match.
--   error_detail      text     Pipeline error detail if this reference failed; NULL otherwise.
--   created_at        timestamptz  Wall-clock timestamp when the row was written.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reference_audit_log (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id           uuid               NOT NULL
                         REFERENCES public.analysis_jobs(id) ON DELETE CASCADE,
    reference_id     text               NOT NULL,
    raw_text         text,
    classification   text,
    confidence_score double precision,
    reason_code      text,
    sources_checked  text[]             NOT NULL DEFAULT '{}',
    match_found      boolean,
    error_detail     text,
    created_at       timestamptz        NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ref_audit_job_id
    ON public.reference_audit_log (job_id);

CREATE INDEX IF NOT EXISTS idx_ref_audit_classification
    ON public.reference_audit_log (classification);

CREATE INDEX IF NOT EXISTS idx_ref_audit_created_at
    ON public.reference_audit_log (created_at);

-- -----------------------------------------------------------------------------
-- Permission model for reference_audit_log:
--   - Revoke all access from PUBLIC (deny-by-default).
--   - Grant SELECT and INSERT to service_role (backend and worker connections).
--   - Grant USAGE on the identity sequence to service_role so INSERT works.
-- -----------------------------------------------------------------------------
REVOKE ALL   ON public.reference_audit_log FROM PUBLIC;
GRANT  SELECT, INSERT ON public.reference_audit_log TO service_role;
GRANT  USAGE  ON SEQUENCE public.reference_audit_log_id_seq TO service_role;
