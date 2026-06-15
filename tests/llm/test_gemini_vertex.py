"""Regression tests for the gemini Vertex AI (service-account / ADC) path.

Honcho's default gemini transport requires a Developer API key. When Vertex
mode is enabled, client construction must instead go through the Vertex SDK
path (``genai.Client(vertexai=True, ...)``) and must NOT require an api key —
on either the chat path (``src/llm/registry.py``) or the embedding path
(``src/embedding_client.py``).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.config import EmbeddingModelConfig, ModelConfig, settings


@pytest.fixture
def vertex_mode(monkeypatch: pytest.MonkeyPatch):
    """Enable Vertex mode with no Gemini api key (the case that used to raise)."""
    monkeypatch.setattr(settings.LLM, "GEMINI_USE_VERTEX", True)
    monkeypatch.setattr(settings.LLM, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings.LLM, "GEMINI_VERTEX_PROJECT", "test-project-123")
    monkeypatch.setattr(settings.LLM, "GEMINI_VERTEX_LOCATION", "us-central1")
    monkeypatch.setattr(
        settings.LLM, "GEMINI_VERTEX_CREDENTIALS_PATH", "/app/service-account.json"
    )
    # Clear the credential-load + client caches so each test builds fresh.
    from src.llm import gemini_vertex, registry

    gemini_vertex._load_vertex_credentials.cache_clear()
    registry.get_gemini_client.cache_clear()
    registry.get_gemini_override_client.cache_clear()


def test_client_for_model_config_vertex_no_api_key(
    vertex_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Under Vertex mode the gemini client builds without an api key.

    The pre-patch behavior raised ``ValidationException("Missing API key for
    gemini ...")`` here.
    """
    from src.llm import registry

    fake_client = MagicMock(name="VertexClient")
    monkeypatch.delitem(registry.CLIENTS, "gemini", raising=False)

    with (
        patch(
            "src.llm.gemini_vertex._load_vertex_credentials",
            return_value="FAKE_CREDS",
        ),
        patch(
            "src.llm.gemini_vertex.genai.Client", return_value=fake_client
        ) as mock_ctor,
    ):
        client = registry.client_for_model_config(
            "gemini", ModelConfig(transport="gemini", model="gemini-3.5-flash")
        )

    assert client is fake_client
    _, kwargs = mock_ctor.call_args
    assert kwargs["vertexai"] is True
    assert kwargs["project"] == "test-project-123"
    assert kwargs["location"] == "us-central1"
    assert kwargs["credentials"] == "FAKE_CREDS"


def test_get_gemini_client_vertex(
    vertex_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.llm import registry

    fake_client = MagicMock(name="VertexClient")
    with (
        patch("src.llm.gemini_vertex._load_vertex_credentials", return_value="C"),
        patch("src.llm.gemini_vertex.genai.Client", return_value=fake_client),
    ):
        assert registry.get_gemini_client() is fake_client


def test_embedding_client_vertex_no_api_key(vertex_mode: None) -> None:
    """The embedding client builds under Vertex mode without an api key.

    Pre-patch this raised ``ValueError("Gemini API key is required")``.
    """
    from src.embedding_client import _EmbeddingClient

    fake_client = MagicMock(name="VertexClient")
    with (
        patch("src.llm.gemini_vertex._load_vertex_credentials", return_value="C"),
        patch("src.llm.gemini_vertex.genai.Client", return_value=fake_client),
    ):
        client = _EmbeddingClient(
            EmbeddingModelConfig(
                transport="gemini",
                model="gemini-embedding-2",
                api_key=None,
                base_url=None,
            ),
            vector_dimensions=1536,
            max_input_tokens=8192,
            max_tokens_per_request=300_000,
            send_dimensions=True,
        )

    assert client.client is fake_client


def test_non_vertex_gemini_still_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without Vertex mode, the api-key guard is unchanged (no regression)."""
    from src.exceptions import ValidationException
    from src.llm import registry

    monkeypatch.setattr(settings.LLM, "GEMINI_USE_VERTEX", False)
    monkeypatch.setattr(settings.LLM, "GEMINI_API_KEY", None)
    monkeypatch.delitem(registry.CLIENTS, "gemini", raising=False)

    with pytest.raises(ValidationException, match="Missing API key for gemini"):
        registry.client_for_model_config(
            "gemini", ModelConfig(transport="gemini", model="gemini-3.5-flash")
        )
