# Step 03 — ISSN Format Validation

## Scope

- Add ISSN format validation to the normalize references node
- Follow the same pattern as existing DOI and arXiv ID validation

**Out of scope:** Validation of volume, issue, pages, or publisher (these are free-text and don't have strict formats). API client changes (Steps 04–06).

## Context

The normalize node already validates DOI and arXiv ID formats after LLM extraction (see `_validate_doi()` and `_validate_arxiv_id()` in `nodes/normalize.py`). ISSN has a well-defined format (4 digits, hyphen, 3 digits, check character) that should be validated before passing it to API clients.

## Requirements

### 1. ISSN Format Pattern

**File:** `apps/worker/biblio_checker_worker/langgraph/nodes/normalize.py`

Add a module-level regex constant:

```python
# ISSN format: 4 digits, hyphen, 3 digits, check digit (0-9 or X)
_ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dXx]$")
```

Valid examples: `0034-8910`, `1234-567X`, `0000-0000`
Invalid examples: `00348910` (no hyphen), `1234-56` (too short), `ABCD-1234` (letters in prefix)

**Case normalization:** If the check digit is lowercase `x`, normalize it to uppercase `X` before returning. This ensures consistent behavior with downstream APIs (OpenAlex, SciELO) which may be case-sensitive on the check digit.

### 2. Validation Function

Add `_validate_issn()` following the exact same pattern as `_validate_doi()`:

```python
def _validate_issn(issn: str | None) -> tuple[str | None, dict[str, Any] | None]:
    """Validate an ISSN string.

    Returns ``(issn, None)`` if valid, or ``(None, warning_dict)`` if invalid.
    """
    if issn is None:
        return None, None
    if _ISSN_RE.match(issn):
        return issn.upper(), None  # Normalize lowercase 'x' check digit to 'X'
    warning: dict[str, Any] = {
        "code": "invalid_issn_format",
        "message": f"ISSN '{issn}' does not match expected format and was discarded.",
        "referenceId": None,  # filled in by caller
        "details": None,
    }
    return None, warning
```

### 3. Wire Validation into `normalize_references()`

In the loop that processes each LLM-returned entry, add ISSN validation alongside the existing DOI and arXiv ID validations:

```python
# Existing validations
valid_doi, doi_warning = _validate_doi(entry.normalized.doi)
if doi_warning is not None:
    doi_warning["referenceId"] = reference_id
    validation_warnings.append(doi_warning)

valid_arxiv, arxiv_warning = _validate_arxiv_id(entry.normalized.arxiv_id)
if arxiv_warning is not None:
    arxiv_warning["referenceId"] = reference_id
    validation_warnings.append(arxiv_warning)

# NEW: ISSN validation
valid_issn, issn_warning = _validate_issn(entry.normalized.issn)
if issn_warning is not None:
    issn_warning["referenceId"] = reference_id
    validation_warnings.append(issn_warning)
```

Then use `valid_issn` in the output dict:

```python
"normalized": {
    ...
    "issn": valid_issn,
    ...
}
```

### 4. Volume, Issue, Pages, Publisher — No Validation

These fields are free-text with too many legitimate formats to validate with a regex:
- **volume**: `"26"`, `"XII"`, `"2021"` (year-as-volume in some journals)
- **issue**: `"3"`, `"105-106"`, `"Special"`, `"Suppl 1"`
- **pages**: `"41-72"`, `"e12345"`, `"S1-S15"`, `"100321"`
- **publisher**: any string

Pass them through as-is from the LLM output. The scoring engine (Step 08, unchanged) handles fuzzy matching downstream.

## Acceptance Criteria

- [ ] `_ISSN_RE` regex validates standard ISSN format: `^\d{4}-\d{3}[\dXx]$`
- [ ] `_validate_issn()` returns `(issn, None)` for valid, `(None, warning)` for invalid
- [ ] Invalid ISSNs produce warning with code `"invalid_issn_format"`
- [ ] Warning includes the reference ID
- [ ] `None` ISSN passes through without warning (no ISSN is valid)
- [ ] Volume, issue, pages, publisher are NOT validated (passed as-is)
- [ ] Existing DOI and arXiv validations are unaffected

## Unit Tests

Add to existing normalize node tests:

```python
class TestValidateIssn:
    def test_valid_issn_passes(self):
        assert _validate_issn("0034-8910") == ("0034-8910", None)

    def test_valid_issn_with_x_check_digit(self):
        assert _validate_issn("1234-567X") == ("1234-567X", None)

    def test_valid_issn_with_lowercase_x_normalized_to_uppercase(self):
        assert _validate_issn("1234-567x") == ("1234-567X", None)

    def test_none_passes(self):
        assert _validate_issn(None) == (None, None)

    def test_missing_hyphen_fails(self):
        issn, warning = _validate_issn("00348910")
        assert issn is None
        assert warning["code"] == "invalid_issn_format"

    def test_too_short_fails(self):
        issn, warning = _validate_issn("1234-56")
        assert issn is None
        assert warning is not None

    def test_letters_in_prefix_fails(self):
        issn, warning = _validate_issn("ABCD-1234")
        assert issn is None
        assert warning is not None
```

## Dependencies

- **Depends on:** Step 02 (new `issn` field in `NormalizedFields`)
- **Informs:** Step 05 (SciELO client uses validated ISSN), Step 04 (OpenAlex client uses validated ISSN)
