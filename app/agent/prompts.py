"""
System prompts and prompt formatting for the agent.
Handles task specification, tool definitions, and output format instructions.
"""

from typing import Optional
from app.agent.schemas import AgentStep


def get_system_prompt(tools_list: list[dict]) -> str:
    """
    Build system prompt with tool definitions.

    Args:
        tools_list: List of tool schema dicts from tool registry

    Returns:
        System prompt string for the model
    """
    tools_section = "\n".join(
        f"- {tool['name']}: {tool['description']}" for tool in tools_list
    )

    return f"""You are a helpful AI agent solving tasks step by step using available tools.

Your task-solving process:
1. Analyze the task carefully
2. Think about what needs to be done (output a THOUGHT)
3. Choose a tool to help solve the task (output an ACTION and ARGS)
4. The tool result will be provided to you (OBSERVATION)
5. Repeat steps 2-4 until the task is complete
6. When task is complete, output your FINAL ANSWER

Available tools:
{tools_section}

Tool usage hints:
- Use read_text_file only for plain text files
- For .xlsx/.xlsm files, use get_excel_info or read_excel_row instead of read_text_file

Output Requirements (CRITICAL):
- You MUST respond with ONLY valid JSON, no other text
- When you need to use a tool, respond with this JSON structure:
  {{"thought": "...", "action": "tool_name", "args": {{...}}}}
- When the task is complete, respond with this JSON structure:
  {{"final_answer": "..."}}
- Do NOT add markdown wrappers, code blocks, or any text outside the JSON
- Do NOT invent tool results - wait for the actual observation
- Every word you output must be part of the JSON object

Examples of valid responses:
{{"thought": "I need to calculate this expression", "action": "calculator", "args": {{"expression": "(123 + 456) * 2"}}}}
{{"final_answer": "The calculation is complete. The result is 1158"}}

Do NOT output anything except the JSON object."""


def get_user_prompt(
    task: str, step_history: list[AgentStep], current_step: int, max_steps: int
) -> str:
    """
    Build user prompt with task and context.

    Args:
        task: The main task to solve
        step_history: Prior steps taken
        current_step: Current step number (1-indexed)
        max_steps: Maximum allowed steps

    Returns:
        User prompt string for the model
    """
    prompt = f"Task: {task}\n\n"

    if step_history:
        prompt += "Prior steps:\n"
        for step in step_history:
            prompt += f"  Step {step.step_number}: {step.thought[:60]}\n"
            prompt += f"    -> Used: {step.action}\n"
            if step.observation_summary:
                obs_text = step.observation_summary[:80]
            else:
                obs_text = step.observation[:80]
            prompt += f"    ← Observed: {obs_text}\n"
        prompt += "\n"

    prompt += f"Current step: {current_step} of {max_steps}\n"
    prompt += "\nNow, think about the next step and respond with JSON."

    return prompt


def get_repair_prompt(invalid_output: str, error_message: str) -> str:
    """
    Build repair prompt when model returns invalid JSON.
    Gives model one chance to fix the output.

    Args:
        invalid_output: The invalid output from model
        error_message: Description of what was wrong

    Returns:
        Repair prompt string
    """
    return f"""Your previous response was invalid: {error_message}

Invalid output was:
{invalid_output[:200]}

Please respond with ONLY valid JSON. No other text.
Remember:
- If using a tool: {{"thought": "...", "action": "tool_name", "args": {{...}}}}
- If task is complete: {{"final_answer": "..."}}
- NOTHING ELSE. No markdown, no explanation, just JSON."""


def format_tool_observation(tool_name: str, result: dict) -> str:
    """
    Format tool execution result as observation for model.

    Args:
        tool_name: Name of tool that was executed
        result: Tool result dictionary

    Returns:
        Formatted observation string
    """
    observation = f"Tool '{tool_name}' executed:\n"
    for key, value in result.items():
        if isinstance(value, str) and len(value) > 200:
            observation += f"  {key}: {value[:200]}...\n"
        else:
            observation += f"  {key}: {value}\n"
    return observation.strip()


def get_demo_scenario_task(scenario_name: str) -> str:
    """
    Get the task description for demo scenarios.

    Args:
        scenario_name: One of 'calculator', 'file_read', 'http_get'

    Returns:
        Task description string
    """
    scenarios = {
        "calculator": "Calculate (123 + 456) * 2. Show the final result.",
        "file_read": "Read the file at samples/test.txt and tell me how many lines it contains.",
        "http_get": "Make an HTTP GET request to https://httpbin.org/status/200 and return the first 300 characters of the response.",
    }
    return scenarios.get(scenario_name, "")
