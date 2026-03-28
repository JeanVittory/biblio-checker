# Step 03 — Text Extraction Node

## Scope

- Implement the `extract_text` graph node that converts raw file bytes into plain text
- Port text extraction logic from the backend (`apps/backend/app/services/text_extraction.py`)
- Define error handling behavior within the graph context

**Out of scope:** PDF/DOCX library selection (already decided: pdfminer.six, python-docx). File download from Supabase (handled by the existing extract pipeline stage).

## Context

The backend already has a working text extraction implementation in `apps/backend/app/services/text_extraction.py`. This node duplicates that logic into the worker to avoid cross-app imports. The function `extract_text_from_bytes()` accepts `source_type`, `content` (bytes), and `max_chars`, and returns a normalized plain text string.

The uploaded document contains **only** bibliographic references — there is no paper body to strip. The full extracted text is passed directly to the `parse_references` node.

**Reference implementation:** `apps/backend/app/services/text_extraction.py`

## Requirements

### 1. Node Function — `nodes/extract_text.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/nodes/extract_text.py`

```python
def extract_text(state: GraphState) -> dict:
```

**Behavior:**

1. Read `state["file_bytes"]` and `state["source_type"]`
2. Extract text using the appropriate library:
   - `"pdf"` → `pdfminer.high_level.extract_text()` with `LAParams()`
   - `"docx"` → `docx.Document()`, join all `paragraph.text` with `\n`
3. Normalize line endings: `\r\n` → `\n`, `\r` → `\n`
4. Enforce `MAX_TEXT_CHARS` limit from config. If exceeded, raise an exception.
5. Return `{"raw_text": extracted_text}`

### 2. Text Extraction Logic

The extraction logic MUST match the backend implementation:

**PDF extraction:**
```python
from pdfminer.high_level import extract_text as pdf_extract_text
from pdfminer.layout import LAParams

text = pdf_extract_text(io.BytesIO(content), laparams=LAParams())
```

**DOCX extraction (with ZIP bomb protection):**
```python
import zipfile
from docx import Document

# ZIP bomb protection — reject DOCX archives that decompress to more than 50 MB
with zipfile.ZipFile(io.BytesIO(content)) as z:
    total_uncompressed = sum(info.file_size for info in z.infolist())
    if total_uncompressed > 50 * 1024 * 1024:  # 50 MB
        raise ValueError(
            f"DOCX archive too large when decompressed: {total_uncompressed} bytes"
        )

doc = Document(io.BytesIO(content))
text = "\n".join(p.text for p in doc.paragraphs)
```

**Post-processing (both formats):**
```python
text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
```

### 3. Error Handling

| Error scenario | Behavior |
|---------------|----------|
| `pdfminer` not installed | Raise exception (dependency must be installed via Step 01) |
| `python-docx` not installed | Raise exception (dependency must be installed via Step 01) |
| Corrupt/unreadable PDF | Let `pdfminer` exception propagate — caught by `run_langgraph_stage` as transient StageError |
| Corrupt/unreadable DOCX | Let `python-docx` exception propagate — same handling |
| DOCX decompresses to > 50MB | Raise `ValueError` before extraction (ZIP bomb protection) |
| Extracted text exceeds `max_text_chars` | Raise `ValueError` with message including char count and limit |
| Unsupported `source_type` | Raise `ValueError(f"Unsupported source_type: {source_type}")` |
| Empty document (0 chars extracted) | Return `{"raw_text": ""}` — the `parse_references` node will handle empty text |

### 4. Logging

Use `structlog.stdlib.get_logger("biblio_checker_worker.langgraph.nodes.extract_text")`.

Log:
- INFO at start: `"extract_text_starting"` with `source_type` and `content_bytes=len(file_bytes)`
- INFO on success: `"extract_text_complete"` with `chars=len(raw_text)`
- ERROR on failure: `"extract_text_failed"` with `error=str(exc)`

### 5. Configuration Access

Read `MAX_TEXT_CHARS` from the `Settings` singleton. The node MUST access settings at call time (not at import time) to support test overrides.

```python
from biblio_checker_worker.core.config import get_settings

settings = get_settings()
max_chars = settings.max_text_chars
```

## Acceptance Criteria

- [ ] Node function has signature `extract_text(state: GraphState) -> dict`
- [ ] Returns `{"raw_text": str}` on success
- [ ] PDF extraction uses `pdfminer.high_level.extract_text` with `LAParams()`
- [ ] DOCX extraction uses `docx.Document` joining paragraph texts with newlines
- [ ] Line endings are normalized (`\r\n` → `\n`, `\r` → `\n`)
- [ ] Raises `ValueError` if extracted text exceeds `max_text_chars`
- [ ] DOCX zip bomb protection rejects archives > 50MB uncompressed
- [ ] Raises `ValueError` for unsupported `source_type`
- [ ] Returns empty string for empty documents (does not raise)
- [ ] Logging at INFO level for start/complete and ERROR for failures
- [ ] Unit tests cover: PDF extraction, DOCX extraction, empty document, oversized document, unsupported type

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| PDF with no text (scanned image) | `pdfminer` returns empty string. Node returns `{"raw_text": ""}`. |
| DOCX with no paragraphs | `python-docx` returns empty string. Node returns `{"raw_text": ""}`. |
| Very large PDF (e.g., 10MB) | Extraction may take seconds but should complete. `MAX_TEXT_CHARS` check prevents memory issues downstream. |
| PDF with mixed encodings | `pdfminer` handles encoding internally. Output is always Python str. |
| DOCX with tables/headers | Only `paragraph.text` is extracted; tables and headers are ignored. This is acceptable because uploaded documents contain only reference lists. |

## Dependencies

- **Depends on:** Step 01 (dependencies: `pdfminer.six`, `python-docx`), Step 02 (GraphState definition)
- **Informs:** Step 05 (parse_references receives `raw_text`)
