"""
Agent runner implementing the thought-action-observation loop.
Handles LLM calls, structured output parsing, tool dispatch, and step history.
"""

import json
import logging
from typing import Optional

from app.llm.ollama_client import OllamaClient
from app.tools.base import ToolRegistry
from app.agent.schemas import ActionResponse, FinalResponse, AgentStep, AgentRunResult
from app.agent.prompts import (
    get_system_prompt,
    get_user_prompt,
    get_repair_prompt,
    format_tool_observation,
)

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Executes agent loop: thought -> action -> observation -> repeat.
    Manages structured output parsing, tool dispatch, and step history.
    """

    def __init__(
        self,
        llm_client: OllamaClient,
        tool_registry: ToolRegistry,
        task: str,
        mode: str = "demo_mode",
        max_steps: Optional[int] = None,
    ):
        """
        Initialize agent runner.

        Args:
            llm_client: OllamaClient instance
            tool_registry: ToolRegistry with available tools
            task: Task to solve
            mode: 'demo_mode' or 'catalog_mode'
            max_steps: Max steps before failure (uses default from YAML if None)
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.task = task
        self.mode = mode

        # Set max steps based on mode
        if max_steps is None:
            if mode == "demo_mode":
                max_steps = 5
            else:
                max_steps = 8
        self.max_steps = max_steps

        self.step_history: list[AgentStep] = []
        self.system_prompt = get_system_prompt(tool_registry.list_tools())

    def run(self) -> AgentRunResult:
        """
        Run the agent loop until completion or max steps.

        Returns:
            AgentRunResult with success status, answer, and step history
        """
        logger.info(f"Starting agent (mode={self.mode}, max_steps={self.max_steps})")
        logger.info(f"Task: {self.task}")

        for step_num in range(1, self.max_steps + 1):
            logger.debug(f"--- Step {step_num}/{self.max_steps} ---")

            # Get model response
            try:
                response_text = self._get_model_response(step_num)
            except Exception as e:
                error_msg = f"Model request failed at step {step_num}: {str(e)}"
                logger.error(error_msg)
                return self._make_failed_result(error_msg)

            # Try to parse as JSON
            response_dict = self.llm_client.parse_json_response(response_text)

            # If parsing fails, retry once with repair prompt
            if response_dict is None:
                logger.warning(f"Step {step_num}: Invalid JSON, attempting repair")
                try:
                    response_text = self._get_repair_response(response_text)
                except Exception as e:
                    error_msg = (
                        f"Model repair request failed at step {step_num}: {str(e)}"
                    )
                    logger.error(error_msg)
                    return self._make_failed_result(error_msg)
                response_dict = self.llm_client.parse_json_response(response_text)

            if response_dict is None:
                error_msg = (
                    f"Failed to parse model output after retry at step {step_num}"
                )
                logger.error(error_msg)
                return self._make_failed_result(error_msg)

            # Check if this is a final response
            if "final_answer" in response_dict:
                try:
                    final_response = FinalResponse(**response_dict)
                    logger.info(f"Task completed at step {step_num}")
                    return self._make_success_result(final_response.final_answer)
                except ValueError as e:
                    error_msg = f"Invalid final_answer structure: {str(e)}"
                    logger.error(error_msg)
                    return self._make_failed_result(error_msg)

            # Parse as action response
            try:
                action_response = ActionResponse(**response_dict)
            except ValueError as e:
                error_msg = f"Invalid action response: {str(e)}"
                logger.error(error_msg)
                return self._make_failed_result(error_msg)

            # Log the step before tool execution
            logger.info(f"Step {step_num}: {action_response.thought[:80]}")
            logger.info(f"  Action: {action_response.action}")
            if action_response.args:
                args_str = str(action_response.args)[:100]
                logger.info(f"  Args: {args_str}")

            # Execute tool
            tool = self.tool_registry.get(action_response.action)
            if tool is None:
                observation = f"Tool '{action_response.action}' not found"
                logger.warning(observation)
            else:
                success, tool_result = tool.safe_run(**action_response.args)
                if success:
                    observation = format_tool_observation(
                        action_response.action, tool_result
                    )
                    observation_summary = self._make_observation_summary(tool_result)
                else:
                    observation = f"Tool error: {tool_result}"
                    observation_summary = observation

                logger.info(f"  Observation: {observation_summary[:80]}")

            # Record step
            step = AgentStep(
                step_number=step_num,
                thought=action_response.thought,
                action=action_response.action,
                args=action_response.args,
                observation=observation,
                observation_summary=observation_summary if tool else observation,
            )
            self.step_history.append(step)

        # Max steps exceeded
        error_msg = f"Max steps ({self.max_steps}) exceeded without task completion"
        logger.error(error_msg)
        return self._make_failed_result(error_msg)

    def _get_model_response(self, step_num: int) -> str:
        """
        Query model for next step.

        Args:
            step_num: Current step number

        Returns:
            Raw model response text
        """
        user_prompt = get_user_prompt(
            self.task,
            self.step_history,
            step_num,
            self.max_steps,
        )

        full_prompt = f"{self.system_prompt}\n\n{user_prompt}"

        logger.debug(f"Sending prompt to model (length={len(full_prompt)})")
        response = self.llm_client.generate(
            prompt=full_prompt,
            temperature=0.7,
        )
        logger.debug(f"Model response: {response[:200]}")
        return response

    def _get_repair_response(self, invalid_output: str) -> str:
        """
        Ask model to fix invalid output.

        Args:
            invalid_output: The invalid JSON from previous attempt

        Returns:
            Repaired model response text
        """
        repair_prompt = get_repair_prompt(invalid_output, "Invalid JSON format")

        full_prompt = f"{self.system_prompt}\n\n{repair_prompt}"

        logger.debug("Sending repair prompt to model")
        response = self.llm_client.generate(
            prompt=full_prompt,
            temperature=0.5,  # Lower temperature for repair
        )
        logger.debug(f"Repair response: {response[:200]}")
        return response

    def _make_observation_summary(self, tool_result: dict) -> str:
        """
        Create a short summary of tool result for logging.

        Args:
            tool_result: Tool execution result

        Returns:
            Summary string (max 80 chars)
        """
        summary_parts = []
        for key, value in tool_result.items():
            if isinstance(value, str):
                val = value[:50]
            else:
                val = str(value)[:50]
            summary_parts.append(f"{key}={val}")

        summary = ", ".join(summary_parts)
        if len(summary) > 80:
            summary = summary[:77] + "..."
        return summary

    def _make_success_result(self, final_answer: str) -> AgentRunResult:
        """Create successful result."""
        return AgentRunResult(
            success=True,
            final_answer=final_answer,
            error=None,
            steps=self.step_history,
            total_steps=len(self.step_history),
            mode=self.mode,
        )

    def _make_failed_result(self, error: str) -> AgentRunResult:
        """Create failed result."""
        return AgentRunResult(
            success=False,
            final_answer=None,
            error=error,
            steps=self.step_history,
            total_steps=len(self.step_history),
            mode=self.mode,
        )
