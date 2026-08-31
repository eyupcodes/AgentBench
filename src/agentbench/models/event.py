"""Event logging models for tracking agent actions, tool calls, retries, and metrics."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events emitted during an agent's task execution."""
    TASK_START = "task_start"
    TASK_END = "task_end"
    THOUGHT = "thought"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    LLM_CALL = "llm_call"
    RETRY = "retry"
    ERROR = "error"
    OUTPUT = "output"


class TokenUsage(BaseModel):
    """Token consumption and estimated cost tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost_usd=round(self.estimated_cost_usd + other.estimated_cost_usd, 6),
        )


class ToolCallEvent(BaseModel):
    """Detailed log of a single tool call execution."""
    tool_name: str
    call_id: Optional[str] = None
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_output: Optional[Any] = None
    duration_ms: float = 0.0
    status: str = "success"  # "success" or "error"
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentEvent(BaseModel):
    """A generic structured event emitted during benchmark execution."""
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: Optional[str] = None
    tool_call: Optional[ToolCallEvent] = None
    retry_attempt: Optional[int] = None
    token_usage: Optional[TokenUsage] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
