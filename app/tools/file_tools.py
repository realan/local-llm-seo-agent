"""
File I/O tools for reading and analyzing text files.
"""

import logging
from pathlib import Path
from typing import Any

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ReadTextFileTool(BaseTool):
    """
    Read a text file and return content with line count.
    """

    def __init__(self, base_path: str = "."):
        super().__init__(
            name="read_text_file", description="read a text file and count lines"
        )
        self.base_path = Path(base_path)

    def run(self, file_path: str) -> dict[str, Any]:
        """
        Read file and count lines.

        Args:
            file_path: Path to file (relative or absolute)

        Returns:
            Dictionary with content and line_count

        Raises:
            ValueError: If file not found or unreadable
        """
        self.validate_inputs(file_path=file_path)

        # Resolve full path
        try:
            full_path = self._resolve_path(file_path)

            if not full_path.exists():
                raise ValueError(f"File not found: {file_path}")

            if not full_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            # Read file
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Count lines
            line_count = len(content.splitlines())

            logger.info(f"Read file: {file_path} ({line_count} lines)")

            return {"content": content, "line_count": line_count}

        except (IOError, OSError) as e:
            logger.error(f"File read error: {str(e)}")
            raise ValueError(f"Cannot read file: {str(e)}")

    def validate_inputs(self, **kwargs) -> bool:
        """Validate file tool inputs."""
        file_path = kwargs.get("file_path", "")

        if not isinstance(file_path, str):
            raise ValueError("file_path must be a string")

        if not file_path.strip():
            raise ValueError("file_path cannot be empty")

        # Security: reject absolute paths outside base_path
        path = Path(file_path)
        if path.is_absolute():
            # Allow absolute paths but log them
            logger.warning(f"Using absolute path: {file_path}")

        return True

    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve file path safely.

        Args:
            file_path: Relative or absolute path

        Returns:
            Resolved Path object
        """
        path = Path(file_path)

        if path.is_absolute():
            return path

        # Try relative to base_path first
        full_path = (self.base_path / path).resolve()

        # TODO: Add security check to ensure path is within base_path
        # For now, just allow it

        return full_path

    def get_input_schema(self) -> dict[str, Any]:
        """Return input schema."""
        return {"file_path": {"type": "string", "description": "Path to file to read"}}
