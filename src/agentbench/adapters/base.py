"""Base classes and execution context for agent adapters."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from agentbench.models.event import AgentEvent, EventType, TokenUsage, ToolCallEvent
from agentbench.models.task import Task


class AgentResponse(BaseModel):
    """Output returned by an agent after processing a task."""
    output: Any
    tool_calls: List[ToolCallEvent] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentExecutionContext:
    """Context provided to an agent during task execution to emit events and track actions."""

    def __init__(self, task: Task, event_callback: Optional[Callable[[AgentEvent], None]] = None) -> None:
        self.task = task
        self.event_callback = event_callback
        self.events: List[AgentEvent] = []
        self.tool_calls: List[ToolCallEvent] = []
        self.token_usage = TokenUsage()

    def emit(self, event: AgentEvent) -> None:
        """Emit an event to the execution history and any active subscriber."""
        self.events.append(event)
        if self.event_callback:
            self.event_callback(event)

    def record_thought(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record an internal reasoning or plan step."""
        event = AgentEvent(
            event_type=EventType.THOUGHT,
            message=message,
            metadata=metadata or {},
        )
        self.emit(event)

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Optional[Any] = None,
        duration_ms: float = 0.0,
        status: str = "success",
        error: Optional[str] = None,
    ) -> ToolCallEvent:
        """Record a completed tool call."""
        tool_event = ToolCallEvent(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            duration_ms=duration_ms,
            status=status,
            error=error,
        )
        self.tool_calls.append(tool_event)
        self.emit(
            AgentEvent(
                event_type=EventType.TOOL_CALL_END,
                tool_call=tool_event,
                metadata={"tool_name": tool_name},
            )
        )
        return tool_event

    def record_token_usage(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
    ) -> None:
        """Record token consumption and cost."""
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )
        self.token_usage = self.token_usage.add(usage)
        self.emit(
            AgentEvent(
                event_type=EventType.LLM_CALL,
                token_usage=usage,
            )
        )


class BaseAgent(ABC):
    """Abstract interface for benchmarkable agent adapters."""

    def __init__(self, name: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> None:
        self.name = name or self.__class__.__name__
        self.config = config or {}

    @abstractmethod
    async def run(self, task: Task, context: AgentExecutionContext) -> AgentResponse:
        """Execute the agent on the given task and return the structured response."""
        pass
