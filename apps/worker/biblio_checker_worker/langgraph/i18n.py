"""Worker-side message catalog and renderer.

This module is the single source of truth for every natural-language string the
worker emits into the final ResultsV1 payload (``decisionReason`` values on
``ReferenceResult`` and ``message`` values on ``Warning``).

Do NOT import this module from anything outside the worker. Frontend and
backend have their own catalogs.

Missing-key policy: if ``key`` is not present in the requested ``locale`` we
fall back to Spanish (``DEFAULT_LOCALE``). If it is missing there too we return
``f"[i18n:{key}]"`` and emit a structured-log warning ``i18n_missing_key`` so
QA surfaces the gap.

Interpolation safety: ``_SafeFormatter`` rejects any field name that is not a
plain Python identifier (e.g. ``{title.__class__.__mro__}`` is blocked). This
prevents format-string injection (CWE-134) from attacker-controlled PDF content
that reaches ``decisionReason`` / warning message templates.

Fail-soft on render error: if interpolation fails for any reason (bad template,
missing key, security rejection) ``render()`` returns ``"[i18n:<key>]"`` and
logs the error rather than raising. A malformed catalog entry must never abort
an entire analysis job.
"""

from __future__ import annotations

import re
from string import Formatter
from typing import Any, Literal

import structlog

logger = structlog.get_logger(__name__)

Locale = Literal["es", "pt", "en"]
LOCALES: tuple[Locale, ...] = ("es", "pt", "en")
DEFAULT_LOCALE: Locale = "es"


def normalize_locale(value: str | None) -> Locale:
    """Coerce an arbitrary string into a supported Locale.

    Region suffixes are stripped (``"es-MX"`` -> ``"es"``). Unknown values
    fall back to :data:`DEFAULT_LOCALE`. ``None`` / empty returns default.
    """
    if not value:
        return DEFAULT_LOCALE
    base = value.lower().split("-")[0]
    if base in LOCALES:
        return base  # type: ignore[return-value]
    return DEFAULT_LOCALE


# Templates are initialised as empty dicts per locale; catalog sub-modules
# populate the ``class.*`` and ``warn.*`` namespaces via ``register()``.
TEMPLATES: dict[Locale, dict[str, str]] = {
    "es": {},
    "pt": {},
    "en": {},
}


def register(key: str, translations: dict[Locale, str]) -> None:
    """Register a translation bundle. Called at import time from catalog files.

    All three locale entries should be provided in each call so copy drift is
    immediately visible in code review.
    """
    for locale, text in translations.items():
        TEMPLATES[locale][key] = text


# ---------------------------------------------------------------------------
# Safe interpolation (CWE-134 mitigation)
# ---------------------------------------------------------------------------


class _SafeFormatter(Formatter):
    """``string.Formatter`` subclass that blocks attribute traversal in field names.

    Standard ``str.format_map`` permits ``{title.__class__.__mro__}`` which
    would let attacker-controlled PDF content traverse arbitrary Python objects.
    This subclass rejects any field name that is not a plain identifier.
    """

    _ident = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def get_field(self, field_name: str, args: Any, kwargs: Any) -> tuple[Any, str]:
        if not self._ident.fullmatch(field_name):
            raise ValueError(f"i18n: disallowed field expression {field_name!r}")
        return kwargs[field_name], field_name


_formatter = _SafeFormatter()


# ---------------------------------------------------------------------------
# Public render entry point
# ---------------------------------------------------------------------------


def render(key: str, locale: str | None = None, **params: Any) -> str:
    """Return the localised template for ``key`` interpolated with ``params``.

    * ``locale`` is normalised via :func:`normalize_locale`.
    * Missing keys fall back to ``DEFAULT_LOCALE``.
    * Missing in default too -> returns ``"[i18n:<key>]"`` and logs a warning.
    * Interpolation errors (missing param, security rejection) -> returns
      ``"[i18n:<key>]"`` and logs an error. Never raises — a bad template must
      not abort an analysis job (fail-soft contract).
    """
    loc = normalize_locale(locale)
    bucket = TEMPLATES.get(loc, {})
    template = bucket.get(key)
    if template is None and loc != DEFAULT_LOCALE:
        template = TEMPLATES[DEFAULT_LOCALE].get(key)
    if template is None:
        logger.warning("i18n_missing_key", key=key, locale=loc)
        return f"[i18n:{key}]"
    try:
        return _formatter.vformat(template, (), params)
    except (KeyError, ValueError) as exc:
        logger.error("i18n_render_failed", key=key, locale=loc, reason=str(exc))
        return f"[i18n:{key}]"


# ---------------------------------------------------------------------------
# Catalog imports — MUST be at the bottom so ``register`` is already bound
# ---------------------------------------------------------------------------

from biblio_checker_worker.langgraph.i18n_catalog import (  # noqa: E402, I001
    classification as _cls_catalog,  # noqa: F401
    warnings as _warn_catalog,  # noqa: F401
)
