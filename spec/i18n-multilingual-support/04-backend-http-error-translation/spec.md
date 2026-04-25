# Step 04 — Backend HTTP Error Translation

## Scope

- Translate the handful of user-facing HTTP error messages emitted by backend controllers into ES/PT/EN.
- Provide a single helper `http_errors.py` that selects the correct string based on the request's `Accept-Language` header.
- Leave structured logs, Sentry messages, and internal error codes untouched (English, operator-facing).

**Out of scope:** Worker-generated warnings and decision reasons (Steps 06–07). Frontend toasts (Step 09 puts those in the catalog). Error codes / `reasonCode` enums (those are codes, translated on the frontend only).

## Context

Not every backend error can use the job's `locale`. Errors like `"Invalid or expired token"` (from `apps/backend/app/api/controllers/analysis/status.py`) happen *before* a job can be identified. For those, the only available signal is the `Accept-Language` header sent by the client.

We do **not** want to translate every log line or Sentry message — those are English, for operators. Only response bodies visible to the end user are translated here.

Known user-facing error strings today (from exploration):

| Controller | Status | English string |
|------------|--------|----------------|
| `analysis/status.py` | 401 | `"Invalid or expired token"` |
| `analysis/status.py` | 503 | `"Service temporarily unavailable"` |
| `analysis/start.py` | 400 | storage/source validation errors (enumerate while implementing) |
| `analysis/start.py` | 429 | rate-limit errors (if any) |

Do a quick `grep -rn "HTTPException\|raise HTTPException" apps/backend/app/api/controllers` during implementation and make sure every `detail=...` literal string is either:

- Translated via the helper (if user-facing), or
- Kept as-is (if it is an internal/operator message — e.g. `"Database unavailable"` returned only on 500 after logging).

Prefer translating any string that maps directly to a toast the user will see.

## Requirements

### 1. Locale Resolution Helper

**New file:** `apps/backend/app/api/i18n/http_errors.py`

```python
"""Translation of user-facing HTTP error messages.

Used only for responses emitted before a job exists (auth, service availability,
request-validation). Worker-produced text uses the job's persisted locale — see
apps/worker/biblio_checker_worker/langgraph/i18n.py.
"""

from __future__ import annotations

from typing import Literal

Locale = Literal["es", "pt", "en"]
_SUPPORTED: tuple[Locale, ...] = ("es", "pt", "en")
_DEFAULT: Locale = "es"


def resolve_locale(accept_language: str | None) -> Locale:
    """Pick the best supported locale from an Accept-Language header.

    Algorithm:
    - Split by comma into (tag, q) pairs.
    - Sort by q desc (default q=1.0).
    - For each tag, take the base two-letter code (before '-').
    - Return the first that is in _SUPPORTED.
    - Fall back to _DEFAULT.
    """
    if not accept_language:
        return _DEFAULT
    candidates: list[tuple[float, str]] = []
    for part in accept_language.split(","):
        tag, _, params = part.strip().partition(";")
        q = 1.0
        for p in params.split(";"):
            p = p.strip()
            if p.startswith("q="):
                try:
                    q = float(p[2:])
                except ValueError:
                    q = 1.0
        if tag:
            candidates.append((q, tag.lower()))
    candidates.sort(key=lambda c: c[0], reverse=True)
    for _, tag in candidates:
        base = tag.split("-")[0]
        if base in _SUPPORTED:
            return base  # type: ignore[return-value]
    return _DEFAULT


# --- Message catalog (extend as new error codes are added) ---

_ERRORS: dict[str, dict[Locale, str]] = {
    "invalid_or_expired_token": {
        "es": "Token inválido o expirado.",
        "pt": "Token inválido ou expirado.",
        "en": "Invalid or expired token.",
    },
    "service_temporarily_unavailable": {
        "es": "Servicio no disponible temporalmente.",
        "pt": "Serviço temporariamente indisponível.",
        "en": "Service temporarily unavailable.",
    },
    "invalid_file_format": {
        "es": "Formato de archivo no válido. Solo se aceptan PDF y DOCX.",
        "pt": "Formato de arquivo inválido. Apenas PDF e DOCX são aceitos.",
        "en": "Invalid file format. Only PDF and DOCX are accepted.",
    },
    "file_too_large": {
        "es": "El archivo excede el tamaño máximo de 10 MB.",
        "pt": "O arquivo excede o tamanho máximo de 10 MB.",
        "en": "File exceeds the maximum size of 10 MB.",
    },
    "rate_limited": {
        "es": "Demasiadas solicitudes. Intenta de nuevo en unos minutos.",
        "pt": "Demasiadas solicitações. Tente novamente em alguns minutos.",
        "en": "Too many requests. Try again in a few minutes.",
    },
    "internal_error": {
        "es": "Ocurrió un error inesperado.",
        "pt": "Ocorreu um erro inesperado.",
        "en": "An unexpected error occurred.",
    },
}


def t(code: str, accept_language: str | None) -> str:
    locale = resolve_locale(accept_language)
    bucket = _ERRORS.get(code)
    if bucket is None:
        return code  # unknown code — return as-is; caller should never hit this
    return bucket.get(locale) or bucket[_DEFAULT]
```

### 2. Use Helper in Controllers

**Pattern to apply in every user-facing `HTTPException`:**

```python
from fastapi import Header, HTTPException
from app.api.i18n.http_errors import t

@router.get("/api/jobs/status")
def get_status(
    poll_token: str,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    ...
):
    job = repo.get_by_poll_token(poll_token)
    if job is None:
        raise HTTPException(
            status_code=401,
            detail=t("invalid_or_expired_token", accept_language),
        )
    ...
```

Apply the same pattern to every user-facing error in:

- `apps/backend/app/api/controllers/analysis/status.py`
- `apps/backend/app/api/controllers/analysis/start.py`
- Any other file surfaced by `grep -rn "HTTPException" apps/backend/app/api/controllers`

**Do not translate** operator-facing errors returned only after logging (e.g. 500 with details scrubbed). Those stay in English.

### 3. Do Not Translate Error Codes

Responses that carry a machine-readable `code` (e.g. `{"code": "invalid_doi_format", "message": "..."}`) keep the `code` in English. Only the `message` field is translated — and the translation happens in the worker i18n module (Step 07), not here.

### 4. Testing Hooks

Export `resolve_locale` and `t` so that tests can assert behaviour directly without spinning up FastAPI.

## Acceptance Criteria

- [ ] `resolve_locale(None)` returns `"es"`.
- [ ] `resolve_locale("pt-BR,pt;q=0.9,en;q=0.8")` returns `"pt"`.
- [ ] `resolve_locale("fr,zh-CN;q=0.8")` returns `"es"` (fallback).
- [ ] `t("invalid_or_expired_token", "en")` returns `"Invalid or expired token."`.
- [ ] `t("nonexistent_code", "pt")` returns `"nonexistent_code"` (no crash).
- [ ] Every user-facing `HTTPException.detail` in the controllers uses `t(...)` with the request's `Accept-Language` header.
- [ ] Operator-facing 500 detail strings remain in English.
- [ ] Existing tests that assert on specific error strings are updated to read through `t(...)` or loosened to check the response code only.

## Unit Tests

**File:** `apps/backend/tests/test_http_errors.py`

```python
from app.api.i18n.http_errors import resolve_locale, t

class TestResolveLocale:
    def test_defaults_to_es(self):
        assert resolve_locale(None) == "es"

    def test_picks_highest_q(self):
        assert resolve_locale("en;q=0.1,pt;q=0.9") == "pt"

    def test_strips_region(self):
        assert resolve_locale("pt-BR") == "pt"

    def test_unknown_falls_back(self):
        assert resolve_locale("fr,zh-CN;q=0.8") == "es"


class TestTranslate:
    def test_known_code_all_locales(self):
        for locale_tag in ("es", "pt", "en"):
            msg = t("invalid_or_expired_token", locale_tag)
            assert msg and msg != "invalid_or_expired_token"

    def test_unknown_code_returns_code(self):
        assert t("does_not_exist", "es") == "does_not_exist"

    def test_missing_locale_falls_back_to_default(self):
        # simulate a partial catalog entry by monkeypatching if you add that edge case
        pass
```

**File:** `apps/backend/tests/test_status_controller.py` (extend an existing test)

```python
def test_invalid_token_returns_localized_message(client):
    response = client.get(
        "/api/jobs/status?poll_token=bad",
        headers={"Accept-Language": "pt-BR"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido ou expirado."
```

## Dependencies

- **Depends on:** Step 03 (Locale type is defined; backend already knows what a supported locale is)
- **Informs:** Step 09 (frontend may surface these messages as-is; no extra translation layer needed client-side since they arrive pre-translated)
