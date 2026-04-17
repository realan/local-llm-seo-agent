"""
HTTP fetch tool for making GET requests.
"""

import logging
from typing import Any

import requests

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class HttpGetTool(BaseTool):
    """
    Make HTTP GET requests and return response.
    Includes timeout handling and text truncation for large responses.
    """

    def __init__(self, max_text_length: int = 5000):
        super().__init__(name="http_get", description="perform HTTP GET request")
        self.max_text_length = max_text_length

    def run(self, url: str, timeout_sec: int = 30) -> dict[str, Any]:
        """
        Make HTTP GET request.

        Args:
            url: URL to fetch
            timeout_sec: Timeout in seconds (default 30, max 120)

        Returns:
            Dictionary with status_code and text

        Raises:
            ValueError: If URL is invalid or request fails
        """
        self.validate_inputs(url=url, timeout_sec=timeout_sec)

        try:
            # Enforce timeout limits
            timeout = min(int(timeout_sec), 120)

            logger.info(f"HTTP GET: {url} (timeout={timeout}s)")

            response = requests.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={"User-Agent": "local-llm-seo-agent/1.0"},
            )

            # Get response text
            text = response.text

            # Truncate if needed
            if len(text) > self.max_text_length:
                text = text[: self.max_text_length]
                logger.info(f"Response truncated to {self.max_text_length} chars")

            logger.info(
                f"HTTP {response.status_code}: received {len(response.text)} chars"
            )

            return {"status_code": response.status_code, "text": text}

        except requests.Timeout:
            error = f"Request timeout after {timeout}s"
            logger.error(error)
            raise ValueError(error)

        except requests.ConnectionError as e:
            error = f"Connection error: {str(e)}"
            logger.error(error)
            raise ValueError(error)

        except requests.RequestException as e:
            error = f"Request failed: {str(e)}"
            logger.error(error)
            raise ValueError(error)

    def validate_inputs(self, **kwargs) -> bool:
        """Validate HTTP inputs."""
        url = kwargs.get("url", "")
        timeout_sec = kwargs.get("timeout_sec", 30)

        if not isinstance(url, str):
            raise ValueError("url must be a string")

        if not url.strip():
            raise ValueError("url cannot be empty")

        # Check URL format
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("url must start with http:// or https://")

        if len(url) > 2000:
            raise ValueError("url is too long")

        # Validate timeout
        try:
            timeout_int = int(timeout_sec)
            if timeout_int < 1 or timeout_int > 120:
                raise ValueError("timeout_sec must be between 1 and 120 seconds")
        except (ValueError, TypeError):
            raise ValueError("timeout_sec must be an integer")

        return True

    def get_input_schema(self) -> dict[str, Any]:
        """Return input schema."""
        return {
            "url": {
                "type": "string",
                "description": "URL to fetch (must start with http:// or https://)",
            },
            "timeout_sec": {
                "type": "integer",
                "description": "Request timeout in seconds (1-120, default 30)",
            },
        }
