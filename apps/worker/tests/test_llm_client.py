"""Tests for Step 04 — LLM Client Factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.0,
    anthropic_key: str = "sk-ant-test",
    openai_key: str = "sk-openai-test",
) -> MagicMock:
    settings = MagicMock()
    settings.llm_provider = provider
    settings.llm_model = model
    settings.llm_temperature = temperature
    settings.anthropic_api_key = MagicMock()
    settings.anthropic_api_key.get_secret_value.return_value = anthropic_key
    settings.openai_api_key = MagicMock()
    settings.openai_api_key.get_secret_value.return_value = openai_key
    return settings


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    def test_returns_llm_instance_for_anthropic(self) -> None:
        """get_llm() returns the ChatAnthropic instance when provider='anthropic'."""
        mock_settings = _make_settings(provider="anthropic", anthropic_key="sk-ant-key")
        mock_llm = MagicMock()
        mock_anthropic_cls = MagicMock(return_value=mock_llm)

        with (
            patch(
                "biblio_checker_worker.langgraph.clients.llm.get_settings",
                return_value=mock_settings,
            ),
            patch("langchain_anthropic.ChatAnthropic", mock_anthropic_cls),
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            result = get_llm()

        assert result is mock_llm

    def test_anthropic_receives_correct_parameters(self) -> None:
        """ChatAnthropic is constructed with model, temperature, api_key, max_tokens=4096."""
        mock_settings = _make_settings(
            provider="anthropic",
            model="claude-opus-4",
            temperature=0.5,
            anthropic_key="sk-ant-secret",
        )
        mock_anthropic_cls = MagicMock()

        with (
            patch(
                "biblio_checker_worker.langgraph.clients.llm.get_settings",
                return_value=mock_settings,
            ),
            patch("langchain_anthropic.ChatAnthropic", mock_anthropic_cls),
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            get_llm()

        mock_anthropic_cls.assert_called_once_with(
            model="claude-opus-4",
            temperature=0.5,
            anthropic_api_key="sk-ant-secret",
            max_tokens=4096,
        )

    def test_uses_get_secret_value_for_anthropic_key(self) -> None:
        """API key is extracted via .get_secret_value() for Anthropic."""
        mock_settings = _make_settings(provider="anthropic", anthropic_key="my-key")
        mock_anthropic_cls = MagicMock()

        with (
            patch(
                "biblio_checker_worker.langgraph.clients.llm.get_settings",
                return_value=mock_settings,
            ),
            patch("langchain_anthropic.ChatAnthropic", mock_anthropic_cls),
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            get_llm()

        mock_settings.anthropic_api_key.get_secret_value.assert_called_once()


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    def test_returns_llm_instance_for_openai(self) -> None:
        """get_llm() returns the ChatOpenAI instance when provider='openai'."""
        mock_settings = _make_settings(provider="openai", openai_key="sk-openai-key")
        mock_llm = MagicMock()
        mock_openai_cls = MagicMock(return_value=mock_llm)

        with (
            patch(
                "biblio_checker_worker.langgraph.clients.llm.get_settings",
                return_value=mock_settings,
            ),
            patch("langchain_openai.ChatOpenAI", mock_openai_cls),
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            result = get_llm()

        assert result is mock_llm

    def test_openai_receives_correct_parameters(self) -> None:
        """ChatOpenAI is constructed with model, temperature, and api_key (no max_tokens)."""
        mock_settings = _make_settings(
            provider="openai",
            model="gpt-4o",
            temperature=0.2,
            openai_key="sk-openai-secret",
        )
        mock_openai_cls = MagicMock()

        with (
            patch(
                "biblio_checker_worker.langgraph.clients.llm.get_settings",
                return_value=mock_settings,
            ),
            patch("langchain_openai.ChatOpenAI", mock_openai_cls),
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            get_llm()

        mock_openai_cls.assert_called_once_with(
            model="gpt-4o",
            temperature=0.2,
            openai_api_key="sk-openai-secret",
        )

    def test_uses_get_secret_value_for_openai_key(self) -> None:
        """OpenAI API key is extracted via .get_secret_value()."""
        mock_settings = _make_settings(provider="openai", openai_key="sk-openai")
        mock_openai_cls = MagicMock()

        with (
            patch(
                "biblio_checker_worker.langgraph.clients.llm.get_settings",
                return_value=mock_settings,
            ),
            patch("langchain_openai.ChatOpenAI", mock_openai_cls),
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            get_llm()

        mock_settings.openai_api_key.get_secret_value.assert_called_once()


# ---------------------------------------------------------------------------
# Unsupported provider
# ---------------------------------------------------------------------------


class TestUnsupportedProvider:
    def test_raises_value_error_for_unknown_provider(self) -> None:
        """ValueError is raised for any provider that is not 'anthropic' or 'openai'."""
        mock_settings = _make_settings(provider="cohere")

        with (
            patch(
                "biblio_checker_worker.langgraph.clients.llm.get_settings",
                return_value=mock_settings,
            ),
            pytest.raises(ValueError, match="Unsupported llm_provider: cohere"),
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            get_llm()

    def test_error_message_includes_provider_name(self) -> None:
        """The ValueError message contains the bad provider string."""
        mock_settings = _make_settings(provider="gemini")

        with patch(
            "biblio_checker_worker.langgraph.clients.llm.get_settings",
            return_value=mock_settings,
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            with pytest.raises(ValueError) as exc_info:
                get_llm()

        assert "gemini" in str(exc_info.value)

    def test_no_module_level_caching(self) -> None:
        """Two consecutive get_llm() calls each invoke get_settings() independently."""
        call_count = 0

        def counting_get_settings() -> MagicMock:
            nonlocal call_count
            call_count += 1
            return _make_settings(provider="anthropic", anthropic_key="key")

        mock_anthropic_cls = MagicMock()

        with (
            patch(
                "biblio_checker_worker.langgraph.clients.llm.get_settings",
                side_effect=counting_get_settings,
            ),
            patch("langchain_anthropic.ChatAnthropic", mock_anthropic_cls),
        ):
            from biblio_checker_worker.langgraph.clients.llm import get_llm

            get_llm()
            get_llm()

        assert call_count == 2, "get_settings should be called once per get_llm() call"
