"""Execution result models for tasks and evaluation checks."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agentbench.models.event import AgentEvent, TokenUsage, ToolCallEvent


class RunStatus(str, Enum):
    """Overall status of a task execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


class EvaluationResult(BaseModel):
    """Result from a single deterministic evaluation check."""

    evaluator_type: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0, default=1.0)
    expected: Any | None = None
    actual: Any | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskRunResult(BaseModel):
    """Complete result record of running an agent on a single task."""

    task_id: str
    task_name: str
    agent_name: str
    status: RunStatus
    output: Any | None = None
    error: str | None = None
    execution_time_seconds: float = 0.0
    retry_count: int = 0
    tool_calls: list[ToolCallEvent] = Field(default_factory=list)
    events: list[AgentEvent] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    evaluations: list[EvaluationResult] = Field(default_factory=list)
    passed: bool = False
    overall_score: float = 0.0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
