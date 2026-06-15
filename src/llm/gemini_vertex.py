"""Vertex AI client construction for the gemini transport.

Honcho's default gemini path authenticates with a Gemini Developer API key
(``genai.Client(api_key=...)``). When Vertex mode is enabled
(``GOOGLE_GENAI_USE_VERTEXAI=True``), we instead build a Vertex-backed client
that authenticates via a service-account JSON / Application Default Credentials
and targets a specific GCP project + location. In that mode no API key is
required — callers must consult :func:`vertex_enabled` before enforcing the
api-key guard.

Centralizing construction here keeps the chat path (``src/llm/registry.py``)
and the embedding path (``src/embedding_client.py``) byte-for-byte consistent.
"""

from __future__ import annotations

from functools import lru_cache

from google import genai

from src.config import settings

# Vertex AI requires the cloud-platform OAuth scope.
_VERTEX_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def vertex_enabled() -> bool:
    """True when the gemini transport should use the direct Vertex AI SDK path."""
    return bool(settings.LLM.GEMINI_USE_VERTEX)


@lru_cache(maxsize=1)
def _load_vertex_credentials(credentials_path: str | None):
    """Load service-account credentials from a JSON file, or None for ADC.

    Cached on the path so we don't re-read/parse the key file on every client
    construction. When ``credentials_path`` is None the genai SDK falls back to
    ambient Application Default Credentials.
    """
    if not credentials_path:
        return None
    # Imported lazily so environments that never touch Vertex don't pay the
    # google-auth import cost at module load.
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_file(  # pyright: ignore[reportUnknownMemberType]
        credentials_path, scopes=_VERTEX_SCOPES
    )


def build_vertex_client() -> genai.Client:
    """Construct a Vertex-AI-backed ``genai.Client`` from settings.

    Reads project / location / credentials-path from ``settings.LLM``. Raises
    via the SDK if project/location are missing or the credentials file is
    unreadable — callers get a clear failure instead of a silent fallback to
    the (wrong) Developer-API path.
    """
    credentials = _load_vertex_credentials(settings.LLM.GEMINI_VERTEX_CREDENTIALS_PATH)
    return genai.Client(
        vertexai=True,
        project=settings.LLM.GEMINI_VERTEX_PROJECT,
        location=settings.LLM.GEMINI_VERTEX_LOCATION,
        credentials=credentials,
    )
