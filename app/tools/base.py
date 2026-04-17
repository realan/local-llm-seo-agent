"""
Base class for all tools used by the agent.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for agent tools."""

    def __init__(self, name: str, description: str):
        """
        Initialize tool.

        Args:
            name: Tool name (used in agent actions)
            description: Human-readable description
        """
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, **kwargs) -> dict[str, Any]:
        """
        Execute the tool with given arguments.

        Returns:
            Dictionary with tool results. Must include at minimum tool-specific outputs.
            Structure depends on tool implementation.

        Raises:
            ValueError: If input validation fails
            Exception: If tool execution fails
        """
        pass

    def schema(self) -> dict[str, Any]:
        """
        Return tool schema for LLM context.
        Override in subclass for custom schema.

        Returns:
            Tool definition with name, description, and inputs
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.get_input_schema(),
        }

    def get_input_schema(self) -> dict[str, Any]:
        """
        Return input parameter schema for this tool.
        Override in subclass.

        Returns:
            Dictionary describing required and optional inputs
        """
        return {}

    def validate_inputs(self, **kwargs) -> bool:
        """
        Validate tool inputs before execution.
        Override in subclass for custom validation.

        Args:
            **kwargs: Tool arguments

        Returns:
            True if valid, raises ValueError otherwise
        """
        return True

    def safe_run(self, **kwargs) -> tuple[bool, Any]:
        """
        Run tool with error handling.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tuple (success: bool, result: Any)
            - On success: (True, result_dict)
            - On failure: (False, error_message)
        """
        try:
            self.validate_inputs(**kwargs)
            result = self.run(**kwargs)
            return True, result
        except ValueError as e:
            error_msg = f"Invalid input: {str(e)}"
            logger.error(f"{self.name}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            logger.error(f"{self.name}: {error_msg}")
            return False, error_msg


class ToolRegistry:
    """Registry for available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.

        Args:
            tool: BaseTool instance
        """
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all registered tools with schemas.

        Returns:
            List of tool schemas
        """
        return [tool.schema() for tool in self._tools.values()]

    def all_tools(self) -> dict[str, BaseTool]:
        """
        Get all registered tools.

        Returns:
            Dictionary of tool_name -> tool_instance
        """
        return self._tools.copy()
