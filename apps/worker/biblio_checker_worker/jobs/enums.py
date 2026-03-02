from __future__ import annotations

import enum


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobStage(enum.StrEnum):
    CREATED = "created"
    EXTRACT_DONE = "extract_done"
    LANGGRAPH_RUNNING = "langgraph_running"
    VERIFYING_REFERENCES = "verifying_references"
    PERSISTING_RESULT = "persisting_result"
    DONE = "done"
