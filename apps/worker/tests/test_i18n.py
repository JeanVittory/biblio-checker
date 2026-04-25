"""Unit tests for the worker i18n module (Step 05)."""

from __future__ import annotations

from biblio_checker_worker.langgraph import i18n


def setup_module(module: object) -> None:
    i18n.register(
        "test.simple", {"es": "hola {name}", "pt": "olá {name}", "en": "hi {name}"}
    )
    i18n.register("test.only_es", {"es": "solo-es"})


class TestNormalizeLocale:
    def test_none(self) -> None:
        assert i18n.normalize_locale(None) == "es"

    def test_empty_string(self) -> None:
        assert i18n.normalize_locale("") == "es"

    def test_strips_region(self) -> None:
        assert i18n.normalize_locale("pt-BR") == "pt"

    def test_lowercases(self) -> None:
        assert i18n.normalize_locale("EN") == "en"

    def test_fallback_for_unknown(self) -> None:
        assert i18n.normalize_locale("fr") == "es"

    def test_pt_direct(self) -> None:
        assert i18n.normalize_locale("pt") == "pt"

    def test_en_direct(self) -> None:
        assert i18n.normalize_locale("en") == "en"

    def test_es_direct(self) -> None:
        assert i18n.normalize_locale("es") == "es"


class TestRender:
    def test_supported_locales(self) -> None:
        assert i18n.render("test.simple", "es", name="A") == "hola A"
        assert i18n.render("test.simple", "pt", name="A") == "olá A"
        assert i18n.render("test.simple", "en", name="A") == "hi A"

    def test_fallback_to_default(self) -> None:
        # "test.only_es" has no "pt" entry; must fall back to "es"
        assert i18n.render("test.only_es", "pt") == "solo-es"

    def test_unknown_key_returns_placeholder(self) -> None:
        result = i18n.render("no.such.key", "es")
        assert result == "[i18n:no.such.key]"

    def test_missing_param_returns_placeholder_fail_soft(self) -> None:
        # Missing {name} → fail-soft returns placeholder, does not raise
        result = i18n.render("test.simple", "es")
        assert result == "[i18n:test.simple]"

    def test_none_locale_defaults_to_es(self) -> None:
        assert i18n.render("test.simple", None, name="X") == "hola X"

    def test_unknown_key_pt_returns_placeholder(self) -> None:
        result = i18n.render("no.such.key", "pt")
        assert result == "[i18n:no.such.key]"


class TestSafeFormatterSecurity:
    """Verify CWE-134 mitigation: attribute traversal in field names is blocked."""

    def setup_method(self) -> None:
        # Register a key with a plain {value} placeholder for security tests
        i18n.register(
            "test.security",
            {"es": "val={value}", "pt": "val={value}", "en": "val={value}"},
        )

    def test_plain_param_value_not_traversed(self) -> None:
        """A param whose VALUE contains dunder notation is treated as a string."""
        # The param VALUE is attacker-controlled but render() only substitutes
        # the placeholder {value} with the literal string passed in.
        result = i18n.render("test.security", "es", value="{__class__}")
        # The literal braces in the value should appear verbatim — NOT evaluated
        assert result == "val={__class__}"

    def test_disallowed_field_expression_in_template_fails_soft(self) -> None:
        """A template with a dotted field name must fail-soft, not traverse attrs."""
        i18n.register(
            "test.malicious_template",
            {
                "es": "bad={title.__class__.__mro__}",
                "pt": "bad={title.__class__.__mro__}",
                "en": "bad={title.__class__.__mro__}",
            },
        )
        result = i18n.render("test.malicious_template", "es", title="some title")
        # Must not succeed — must return the safe placeholder
        assert result == "[i18n:test.malicious_template]"
        assert "mro" not in result

    def test_dunder_param_name_rejected(self) -> None:
        """Dunder field names in templates must fail-soft, not traverse objects."""
        # We pass __class__ as a kwarg; the formatter must reject it.
        i18n.register(
            "test.dunder_key",
            {
                "es": "{__class__}",
                "pt": "{__class__}",
                "en": "{__class__}",
            },
        )
        result = i18n.render("test.dunder_key", "es")
        assert result == "[i18n:test.dunder_key]"
