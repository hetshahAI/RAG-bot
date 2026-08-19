import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import LLMConfig, settings
from app.services.interfaces import ILLMClient

logger = logging.getLogger("rag-backend.llm")


class OpenAICompatibleLLMClient(ILLMClient):
    """Client for OpenAI-compatible LLM providers (e.g. self-hosted, vLLM, Exo, Ollama, OpenAI)."""

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        api_key: Optional[str] = None,
    ):
        self.config = config or settings.rag.llm
        self.base_url = (self.config.base_url or "https://exo.manysphere.info/v1").rstrip("/")
        self.model = self.config.model or "mlx-community/Qwen3.6-35B-A3B-4bit"
        self.api_key = api_key or settings.llm_api_key
        self.temperature = self.config.temperature
        self.max_tokens = self.config.max_tokens
        self.timeout_seconds = self.config.timeout_seconds or 60

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Send chat completion request to the OpenAI-compatible endpoint."""
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key.strip():
            headers["Authorization"] = f"Bearer {self.api_key.strip()}"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        logger.info(
            "Sending LLM chat completion request to '%s' (model: '%s', messages: %d)",
            url,
            self.model,
            len(messages),
        )

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                error_body = response.text[:200]
                logger.error("LLM request failed with status %d: %s", response.status_code, error_body)
                raise RuntimeError(
                    f"LLM provider returned HTTP {response.status_code}: {error_body}"
                )

            data = response.json()
            choices = data.get("choices")
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                raise RuntimeError("LLM response contains no choices.")

            content = choices[0].get("message", {}).get("content", "")
            return content.strip()

        except httpx.TimeoutException as e:
            logger.error("LLM request timed out after %ds: %s", self.timeout_seconds, e)
            raise RuntimeError(f"LLM request timed out after {self.timeout_seconds} seconds.") from e
        except httpx.RequestError as e:
            logger.error("LLM connection error: %s", e)
            raise RuntimeError(f"LLM provider connection failed: {str(e)}") from e


_llm_client_instance: Optional[OpenAICompatibleLLMClient] = None


def get_llm_client() -> ILLMClient:
    """Dependency provider for LLM client."""
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = OpenAICompatibleLLMClient()
    return _llm_client_instance
