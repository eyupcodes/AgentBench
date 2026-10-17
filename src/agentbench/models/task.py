"""Task and Benchmark Suite models."""

from typing import Any

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Specification of a tool input parameter."""

    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any | None = None


class ToolDefinition(BaseModel):
    """Definition of a mock or live tool available to the agent during evaluation."""

    name: str
    description: str
    parameters: dict[str, ToolParameter] = Field(default_factory=dict)
    mock_response: Any | None = None


class EvaluatorConfig(BaseModel):
    """Configuration for a deterministic evaluator."""

    type: str  # e.g., "exact_match", "contains", "regex", "json_schema", "tool_call", "custom"
    expected: Any | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0
    description: str | None = None


class Task(BaseModel):
    """A single benchmark task for an agent to perform."""

    id: str
    name: str
    description: str | None = None
    prompt: str
    system_prompt: str | None = None
    tools: list[ToolDefinition] = Field(default_factory=list)
    evaluators: list[EvaluatorConfig] = Field(default_factory=list)
    expected_output: Any | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskSuite(BaseModel):
    """A collection of tasks that form a benchmark suite."""

    name: str
    version: str = "1.0"
    description: str | None = None
    tasks: list[Task] = Field(default_factory=list)
    default_timeout_seconds: float = 30.0
    default_max_retries: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
