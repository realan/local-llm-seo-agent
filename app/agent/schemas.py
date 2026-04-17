"""
Pydantic schemas for agent request/response contracts.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ActionResponse(BaseModel):
    """
    Response when agent chooses to use a tool.
    Model must return only one structured object (no markdown wrappers).
    """

    thought: str = Field(..., description="Agent's reasoning before the action")
    action: str = Field(..., description="Tool name to call")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")

    class Config:
        json_schema_extra = {
            "example": {
                "thought": "I need to calculate the expression",
                "action": "calculator",
                "args": {"expression": "(123 + 456) * 2"},
            }
        }


class FinalResponse(BaseModel):
    """
    Response when agent completes the task.
    Returned when task is complete.
    """

    final_answer: str = Field(..., description="Task completion result")

    class Config:
        json_schema_extra = {"example": {"final_answer": "The result is 1158"}}


class AgentStep(BaseModel):
    """
    Represents one cycle in the agent loop: thought -> action -> observation.
    """

    step_number: int
    thought: str
    action: str
    args: dict[str, Any]
    observation: str
    observation_summary: Optional[str] = None


class AgentRunResult(BaseModel):
    """
    Final result of agent run with step history.
    """

    success: bool
    final_answer: Optional[str] = None
    error: Optional[str] = None
    steps: list[AgentStep] = Field(default_factory=list)
    total_steps: int = 0
    mode: str  # "demo_mode" or "catalog_mode"

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "final_answer": "The result is 1158",
                "error": None,
                "steps": [],
                "total_steps": 2,
                "mode": "demo_mode",
            }
        }
