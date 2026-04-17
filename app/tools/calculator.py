"""
Calculator tool for safe arithmetic expression evaluation.
Uses numexpr for safe evaluation without direct eval().
"""

import logging
import re
from typing import Any

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CalculatorTool(BaseTool):
    """
    Evaluates arithmetic expressions safely.
    Supports: +, -, *, /, //, %, ** operators and parentheses.
    No variables or functions allowed.
    """

    def __init__(self):
        super().__init__(
            name="calculator", description="evaluate arithmetic expression"
        )

    def run(self, expression: str) -> dict[str, Any]:
        """
        Evaluate arithmetic expression.

        Args:
            expression: Arithmetic expression string

        Returns:
            Dictionary with result

        Raises:
            ValueError: If expression is invalid or unsafe
        """
        self.validate_inputs(expression=expression)

        try:
            # Use numexpr if available for safe eval, otherwise use restricted eval
            try:
                import numexpr

                result = numexpr.evaluate(expression).item()
            except ImportError:
                # Fallback to restricted eval
                result = self._safe_eval(expression)

            # Format result
            if isinstance(result, float):
                # Remove trailing zeros
                if result == int(result):
                    result_str = str(int(result))
                else:
                    result_str = f"{result:.10g}"
            else:
                result_str = str(result)

            logger.info(f"Calculator: {expression} = {result_str}")

            return {"result": result_str}

        except Exception as e:
            logger.error(f"Calculator error: {str(e)}")
            raise ValueError(f"Failed to evaluate expression: {str(e)}")

    def validate_inputs(self, **kwargs) -> bool:
        """Validate calculator inputs."""
        expression = kwargs.get("expression", "")

        if not isinstance(expression, str):
            raise ValueError("expression must be a string")

        if not expression.strip():
            raise ValueError("expression cannot be empty")

        if len(expression) > 500:
            raise ValueError("expression too long (max 500 chars)")

        # Check for allowed characters only
        allowed_chars = set("0123456789+-*/%().() \t")
        if not all(c in allowed_chars for c in expression):
            raise ValueError("expression contains invalid characters")

        # Reject keywords/function calls
        dangerous_patterns = [
            r"\b(import|exec|eval|open|__)\b",
            r"[a-zA-Z_][a-zA-Z0-9_]*\s*\(",  # Function calls
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, expression):
                raise ValueError("expression contains invalid operations")

        return True

    def _safe_eval(self, expression: str) -> float:
        """
        Safely evaluate arithmetic expression without numexpr.

        Args:
            expression: Expression to evaluate

        Returns:
            Numeric result
        """
        # Clean up expression
        expr = expression.strip()

        # Final whitelist validation
        allowed = set("0123456789+-*/%().() \t")
        if not all(c in allowed for c in expr):
            raise ValueError("Invalid characters in expression")

        # Use limited eval with safe namespace
        safe_dict = {
            "__builtins__": {},
            "abs": abs,
            "pow": pow,
        }

        try:
            result = eval(expr, safe_dict)
            if not isinstance(result, (int, float)):
                raise ValueError("Result is not numeric")
            return float(result)
        except Exception as e:
            raise ValueError(f"Evaluation failed: {str(e)}")

    def get_input_schema(self) -> dict[str, Any]:
        """Return input schema."""
        return {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression e.g. '(123 + 456) * 2'",
            }
        }
