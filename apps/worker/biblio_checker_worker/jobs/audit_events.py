from __future__ import annotations

import enum


class JobEventType(enum.StrEnum):
    JOB_CREATED = "job_created"
    JOB_CLAIMED = "job_claimed"
    STAGE_CHANGED = "stage_changed"
    JOB_SUCCEEDED = "job_succeeded"
    JOB_FAILED = "job_failed"
    JOB_REQUEUED = "job_requeued"
