"""Tests for app.api.i18n.http_errors — locale resolution and message translation.

Covers:
- resolve_locale: None, highest-q tag, region stripping, unknown fallback
- t: known code all locales, unknown code, None header
- Security: 10 000-char header resolves without crash in < 10 ms
- Security: 50-tag header only inspects first 10 tags
"""

from __future__ import annotations

import time

from app.api.i18n.http_errors import (
    _MAX_HEADER_LEN,
    _MAX_TAGS,
    _SUPPORTED,
    resolve_locale,
    t,
)


class TestResolveLocale:
    def test_defaults_to_es_when_none(self):
        assert resolve_locale(None) == "es"

    def test_defaults_to_es_when_empty_string(self):
        assert resolve_locale("") == "es"

    def test_simple_supported_locale(self):
        assert resolve_locale("en") == "en"

    def test_picks_highest_q(self):
        assert resolve_locale("en;q=0.1,pt;q=0.9") == "pt"

    def test_strips_region(self):
        assert resolve_locale("pt-BR") == "pt"

    def test_strips_region_complex(self):
        assert resolve_locale("pt-BR,pt;q=0.9,en;q=0.8") == "pt"

    def test_unknown_falls_back_to_es(self):
        assert resolve_locale("fr,zh-CN;q=0.8") == "es"

    def test_all_supported_locales_round_trip(self):
        for locale in _SUPPORTED:
            assert resolve_locale(locale) == locale

    def test_es_es_normalises_to_es(self):
        assert resolve_locale("es-ES") == "es"

    def test_en_us_normalises_to_en(self):
        assert resolve_locale("en-US,en;q=0.9") == "en"

    # --- Security hardening ---

    def test_ten_thousand_char_header_resolves_fast(self):
        """A 10 000-char header must resolve in under 10 ms."""
        big_header = "fr," * 3000 + "en"  # well over 10 000 chars
        start = time.monotonic()
        result = resolve_locale(big_header)
        elapsed_ms = (time.monotonic() - start) * 1000
        # After truncation to _MAX_HEADER_LEN=256, "en" may not survive the cut;
        # but the call must be fast and must not crash.
        assert elapsed_ms < 10, f"took {elapsed_ms:.2f} ms — expected < 10 ms"
        # Result must always be one of the supported locales or default
        assert result in _SUPPORTED

    def test_fifty_tag_header_only_inspects_first_ten(self):
        """Build a header where only tags 11-50 contain 'en'; result must be 'es'."""
        # First _MAX_TAGS (10) tags are all unsupported "fr"
        first_ten = ",".join("fr" for _ in range(_MAX_TAGS))
        # Tags 11-50 are "en" — these must NOT be inspected
        remaining = ",".join("en" for _ in range(40))
        header = f"{first_ten},{remaining}"
        result = resolve_locale(header)
        # Only fr in first 10 → falls back to "es"
        assert result == "es"

    def test_max_header_len_constant(self):
        assert _MAX_HEADER_LEN == 256

    def test_max_tags_constant(self):
        assert _MAX_TAGS == 10


class TestTranslate:
    def test_known_code_all_locales(self):
        for locale_tag in ("es", "pt", "en"):
            msg = t("invalid_or_expired_token", locale_tag)
            assert msg
            assert msg != "invalid_or_expired_token"

    def test_unknown_code_returns_code(self):
        assert t("does_not_exist", "es") == "does_not_exist"

    def test_unknown_code_with_none_header(self):
        assert t("does_not_exist", None) == "does_not_exist"

    def test_invalid_or_expired_token_en(self):
        assert t("invalid_or_expired_token", "en") == "Invalid or expired token."

    def test_invalid_or_expired_token_pt(self):
        assert t("invalid_or_expired_token", "pt") == "Token inválido ou expirado."

    def test_invalid_or_expired_token_es(self):
        assert t("invalid_or_expired_token", "es") == "Token inválido o expirado."

    def test_service_unavailable_all_locales(self):
        for locale_tag in ("es", "pt", "en"):
            msg = t("service_temporarily_unavailable", locale_tag)
            assert msg
            assert msg != "service_temporarily_unavailable"

    def test_none_header_falls_back_to_es(self):
        msg_none = t("invalid_or_expired_token", None)
        msg_es = t("invalid_or_expired_token", "es")
        assert msg_none == msg_es

    def test_unknown_locale_header_falls_back_to_es(self):
        msg = t("invalid_or_expired_token", "fr")
        msg_es = t("invalid_or_expired_token", "es")
        assert msg == msg_es
