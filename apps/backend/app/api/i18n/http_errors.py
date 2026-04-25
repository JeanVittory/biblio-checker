"""Translation of user-facing HTTP error messages.

Used only for responses emitted before a job exists (auth, service availability,
request-validation). Worker-produced text uses the job's persisted locale — see
apps/worker/biblio_checker_worker/langgraph/i18n.py.

Security hardening:
- Accept-Language header is capped to _MAX_HEADER_LEN characters.
- Only the first _MAX_TAGS comma-separated tags are inspected.
"""

from __future__ import annotations

from typing import Literal

Locale = Literal["es", "pt", "en"]
_SUPPORTED: tuple[Locale, ...] = ("es", "pt", "en")
_DEFAULT: Locale = "es"

_MAX_HEADER_LEN: int = 256
_MAX_TAGS: int = 10


def resolve_locale(accept_language: str | None) -> Locale:
    """Pick the best supported locale from an Accept-Language header.

    Algorithm:
    - Truncate header to _MAX_HEADER_LEN characters.
    - Split by comma into at most _MAX_TAGS (tag, q) pairs.
    - Sort by q desc (default q=1.0).
    - For each tag, take the base two-letter code (before '-').
    - Return the first that is in _SUPPORTED.
    - Fall back to _DEFAULT.
    """
    accept_language = (accept_language or "")[:_MAX_HEADER_LEN]
    if not accept_language:
        return _DEFAULT

    candidates: list[tuple[float, str]] = []
    for part in accept_language.split(",")[:_MAX_TAGS]:
        tag, _, params = part.strip().partition(";")
        q = 1.0
        for p in params.split(";"):
            p = p.strip()
            if p.startswith("q="):
                try:
                    q = float(p[2:])
                except ValueError:
                    q = 1.0
        if tag.strip():
            candidates.append((q, tag.strip().lower()))

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
    """Return the translated error message for the given code.

    Resolves the locale from the Accept-Language header.  Falls back to
    _DEFAULT when the locale bucket is missing.  Returns the bare ``code``
    string when the code is not in the catalog — never raises.
    """
    locale = resolve_locale(accept_language)
    bucket = _ERRORS.get(code)
    if bucket is None:
        return code  # unknown code — return as-is; caller should never hit this
    return bucket.get(locale) or bucket[_DEFAULT]
