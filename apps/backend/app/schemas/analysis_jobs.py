from enum import StrEnum


class AnalysisJobStage(StrEnum):
    CREATED = "created"
    LANGGRAPH_RUNNING = "langgraph_running"
    VERIFYING_REFERENCES = "verifying_references"
    PERSISTING_RESULT = "persisting_result"


class AnalysisJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

