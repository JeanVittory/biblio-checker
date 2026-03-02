from __future__ import annotations

from dataclasses import dataclass, field

from biblio_checker_worker.jobs.models import AnalysisJob


@dataclass
class JobContext:
    """Mutable context object threaded through each pipeline stage.

    Stages read from and write to this object to pass intermediate results
    (downloaded bytes, extracted text, LangGraph output) to downstream stages
    without coupling the stage functions to each other directly.
    """

    job: AnalysisJob
    token: str
    file_bytes: bytes = b""
    extracted_text: str = ""
    result_json: dict = field(default_factory=dict)
