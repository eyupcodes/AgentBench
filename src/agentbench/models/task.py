"""Task and Benchmark Suite models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Specification of a tool input parameter."""
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Definition of a mock or live tool available to the agent during evaluation."""
    name: str
    description: str
    parameters: Dict[str, ToolParameter] = Field(default_factory=dict)
    mock_response: Optional[Any] = None


class EvaluatorConfig(BaseModel):
    """Configuration for a deterministic evaluator."""
    type: str  # e.g., "exact_match", "contains", "regex", "json_schema", "tool_call", "custom"
    expected: Optional[Any] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0
    description: Optional[str] = None


class Task(BaseModel):
    """A single benchmark task for an agent to perform."""
    id: str
    name: str
    description: Optional[str] = None
    prompt: str
    system_prompt: Optional[str] = None
    tools: List[ToolDefinition] = Field(default_factory=list)
    evaluators: List[EvaluatorConfig] = Field(default_factory=list)
    expected_output: Optional[Any] = None
    timeout_seconds: float = 30.0
    max_retries: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskSuite(BaseModel):
    """A collection of tasks that form a benchmark suite."""
    name: str
    version: str = "1.0"
    description: Optional[str] = None
    tasks: List[Task] = Field(default_factory=list)
    default_timeout_seconds: float = 30.0
    default_max_retries: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)
