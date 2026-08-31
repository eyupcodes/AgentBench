"""Configuration and options for the task benchmark runner."""

from typing import Callable, Optional
from pydantic import BaseModel, Field

from agentbench.models.event import AgentEvent
from agentbench.models.result import TaskRunResult


class RunnerOptions(BaseModel):
    """Execution options for running a benchmark suite."""
    max_concurrency: int = 1
    default_timeout_seconds: float = 30.0
    default_max_retries: int = 1
    retry_delay_seconds: float = 0.5
    stop_on_first_failure: bool = False
    verbose: bool = False
