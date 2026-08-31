"""AgentBench: Evaluation and Benchmarking Harness for AI Agents."""

__version__ = "0.1.0"

from agentbench.adapters.base import AgentExecutionContext, AgentResponse, BaseAgent
from agentbench.adapters.mock import MockAgent
from agentbench.adapters.scripted import ScriptedAgent
from agentbench.adapters.http_llm import GenericLLMAgent
from agentbench.adapters.registry import get_adapter, list_adapters, register_adapter
from agentbench.evaluators.base import BaseEvaluator, EvaluationContext
from agentbench.evaluators.registry import get_evaluator, list_evaluators, register_evaluator
from agentbench.loader import load_suite, save_suite
from agentbench.models.event import AgentEvent, EventType, TokenUsage, ToolCallEvent
from agentbench.models.report import BenchmarkReport, SuiteMetrics
from agentbench.models.result import EvaluationResult, RunStatus, TaskRunResult
from agentbench.models.task import EvaluatorConfig, Task, TaskSuite, ToolDefinition
from agentbench.reporting.formatter import generate_markdown_report, print_cli_report
from agentbench.reporting.json_report import load_report_json, save_report_json
from agentbench.runner.context import RunnerOptions
from agentbench.runner.runner import BenchmarkRunner

__all__ = [
    "__version__",
    "BaseAgent",
    "AgentExecutionContext",
    "AgentResponse",
    "MockAgent",
    "ScriptedAgent",
    "GenericLLMAgent",
    "get_adapter",
    "list_adapters",
    "register_adapter",
    "BaseEvaluator",
    "EvaluationContext",
    "get_evaluator",
    "list_evaluators",
    "register_evaluator",
    "load_suite",
    "save_suite",
    "AgentEvent",
    "EventType",
    "TokenUsage",
    "ToolCallEvent",
    "EvaluatorConfig",
    "Task",
    "TaskSuite",
    "ToolDefinition",
    "RunStatus",
    "EvaluationResult",
    "TaskRunResult",
    "BenchmarkReport",
    "SuiteMetrics",
    "print_cli_report",
    "generate_markdown_report",
    "save_report_json",
    "load_report_json",
    "BenchmarkRunner",
    "RunnerOptions",
]
