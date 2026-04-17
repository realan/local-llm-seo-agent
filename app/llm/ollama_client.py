"""
Ollama LLM client for qwen3.5:4b model.
Handles structured output parsing and retries.
"""

import json
import logging
import os
from typing import Optional

import requests
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

load_dotenv()


class OllamaClientError(Exception):
    """Base exception for Ollama client failures."""


class OllamaModelNotFoundError(OllamaClientError):
    """Raised when configured Ollama model is not installed."""


def _should_retry_request_error(exc: Exception) -> bool:
    """Retry only transient request failures, not permanent config errors."""
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True

    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code >= 500

    return False


class OllamaClient:
    """Client for Ollama API running qwen3.5:4b locally."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        timeout_sec: Optional[int] = None,
    ):
        """
        Initialize Ollama client.

        Args:
            endpoint: Ollama API endpoint
            model: Model name to use
            timeout_sec: Request timeout in seconds
        """
        self.endpoint = endpoint or os.getenv(
            "OLLAMA_ENDPOINT", "http://localhost:11434/api/generate"
        )
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
        self.timeout_sec = self._resolve_timeout(timeout_sec)

    @retry(
        retry=retry_if_exception(_should_retry_request_error),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate(
        self, prompt: str, temperature: float = 0.7, top_p: float = 0.9, top_k: int = 40
    ) -> str:
        """
        Generate text from the model.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter

        Returns:
            Generated text

        Raises:
            OllamaModelNotFoundError: If configured model is not installed
            OllamaClientError: If API call fails
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }

        try:
            response = requests.post(
                self.endpoint, json=payload, timeout=self.timeout_sec
            )
            if response.status_code == 404:
                error_message = self._extract_error_message(response)
                if "model" in error_message.lower() and "not found" in error_message.lower():
                    logger.error("Ollama model error: %s", error_message)
                    raise OllamaModelNotFoundError(
                        f"Configured Ollama model '{self.model}' is not installed. "
                        f"Run: ollama pull {self.model}"
                    )

            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except OllamaClientError:
            raise
        except requests.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise OllamaClientError(str(e)) from e

    def parse_json_response(self, text: str) -> Optional[dict]:
        """
        Parse JSON-like response from model.
        Attempts to extract valid JSON from model output.

        Args:
            text: Raw model output

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Try direct JSON parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from text (e.g., ```json ... ```)
        text = text.strip()
        if "```json" in text:
            try:
                start = text.index("```json") + 7
                end = text.index("```", start)
                json_str = text[start:end].strip()
                return json.loads(json_str)
            except (ValueError, json.JSONDecodeError):
                pass

        if text.startswith("{"):
            try:
                # Try to find matching closing brace
                for i in range(len(text), 0, -1):
                    try:
                        return json.loads(text[:i])
                    except json.JSONDecodeError:
                        continue
            except Exception:
                pass

        logger.warning(f"Could not parse JSON from response: {text[:100]}...")
        return None

    def list_available_models(self) -> list[str]:
        """Return installed Ollama model names."""
        response = requests.get(
            f"{self.endpoint.rsplit('/api', 1)[0]}/api/tags", timeout=5
        )
        response.raise_for_status()
        payload = response.json()
        return [item.get("name", "") for item in payload.get("models", []) if item.get("name")]

    def health_status(self) -> tuple[bool, str]:
        """
        Check if Ollama is accessible and the configured model is available.

        Returns:
            Tuple of (ready, message)
        """
        try:
            models = self.list_available_models()
        except requests.RequestException as e:
            return False, f"Ollama is not accessible: {e}"

        if self.model not in models:
            available = ", ".join(models) if models else "no models installed"
            return (
                False,
                f"Ollama is reachable, but model '{self.model}' is not installed. "
                f"Available models: {available}",
            )

        return True, "Ollama is running and the configured model is available"

    def health_check(self) -> bool:
        """
        Compatibility wrapper for callers that only need a boolean.

        Returns:
            True if service is reachable and configured model is available
        """
        ok, _ = self.health_status()
        return ok

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        """Extract best-effort error message from Ollama response."""
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or f"HTTP {response.status_code}"

        if isinstance(payload, dict):
            return str(payload.get("error") or payload)

        return str(payload)

    @staticmethod
    def _resolve_timeout(timeout_sec: Optional[int]) -> int:
        """Resolve request timeout from explicit arg or environment."""
        if timeout_sec is not None:
            return int(timeout_sec)

        raw_timeout = os.getenv("OLLAMA_TIMEOUT_SEC", "120")
        try:
            return int(raw_timeout)
        except ValueError:
            logger.warning(
                "Invalid OLLAMA_TIMEOUT_SEC=%r, falling back to 120", raw_timeout
            )
            return 120
