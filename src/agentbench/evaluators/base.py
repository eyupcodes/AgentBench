"""Base class and context for benchmark evaluators."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agentbench.models.event import AgentEvent, ToolCallEvent
from agentbench.models.result import EvaluationResult
from agentbench.models.task import EvaluatorConfig, Task


class EvaluationContext(BaseModel):
    """Contextual information provided to evaluators to score a task execution."""
    task: Task
    output: Any
    tool_calls: List[ToolCallEvent] = Field(default_factory=list)
    events: List[AgentEvent] = Field(default_factory=list)
    execution_time_seconds: float = 0.0
    error: Optional[str] = None
    retry_count: int = 0


class BaseEvaluator(ABC):
    """Abstract interface for deterministic evaluation metrics."""

    def __init__(self, config: Optional[EvaluatorConfig] = None) -> None:
        self.config = config or EvaluatorConfig(type=self.__class__.__name__)

    @abstractmethod
    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        """Evaluate agent performance on the task context and return structured result."""
        pass
