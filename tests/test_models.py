"""Unit tests for AgentBench data models."""

from agentbench.models.event import AgentEvent, EventType, TokenUsage, ToolCallEvent
from agentbench.models.task import EvaluatorConfig, Task, TaskSuite, ToolDefinition, ToolParameter
from agentbench.models.result import EvaluationResult, RunStatus, TaskRunResult
from agentbench.models.report import BenchmarkReport, SuiteMetrics


def test_token_usage_aggregation():
    t1 = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, estimated_cost_usd=0.002)
    t2 = TokenUsage(prompt_tokens=200, completion_tokens=80, total_tokens=280, estimated_cost_usd=0.003)
    combined = t1.add(t2)

    assert combined.prompt_tokens == 300
    assert combined.completion_tokens == 130
    assert combined.total_tokens == 430
    assert combined.estimated_cost_usd == 0.005


def test_tool_call_event():
    event = ToolCallEvent(
        tool_name="calculator",
        tool_input={"expr": "10 * 5"},
        tool_output=50,
        duration_ms=12.5,
    )
    assert event.tool_name == "calculator"
    assert event.tool_output == 50
    assert event.status == "success"


def test_task_suite_validation():
    suite = TaskSuite(
        name="test-suite",
        tasks=[
            Task(
                id="t1",
                name="Task 1",
                prompt="Say hello",
                expected_output="hello",
                tools=[
                    ToolDefinition(
                        name="echo",
                        description="Echoes input",
                        parameters={"msg": ToolParameter(type="string", required=True)},
                    )
                ],
                evaluators=[
                    EvaluatorConfig(type="exact_match", expected="hello")
                ],
            )
        ],
    )
    assert len(suite.tasks) == 1
    assert suite.tasks[0].id == "t1"
    assert suite.tasks[0].tools[0].parameters["msg"].required is True


def test_benchmark_report_metrics_computation():
    r1 = TaskRunResult(
        task_id="t1",
        task_name="Task 1",
        agent_name="TestAgent",
        status=RunStatus.SUCCESS,
        passed=True,
        overall_score=1.0,
        execution_time_seconds=1.5,
        retry_count=0,
        tool_calls=[ToolCallEvent(tool_name="tool_a", tool_input={})],
        token_usage=TokenUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120, estimated_cost_usd=0.001),
    )
    r2 = TaskRunResult(
        task_id="t2",
        task_name="Task 2",
        agent_name="TestAgent",
        status=RunStatus.FAILURE,
        passed=False,
        overall_score=0.5,
        execution_time_seconds=2.5,
        retry_count=1,
        tool_calls=[
            ToolCallEvent(tool_name="tool_a", tool_input={}),
            ToolCallEvent(tool_name="tool_b", tool_input={}),
        ],
        token_usage=TokenUsage(prompt_tokens=150, completion_tokens=30, total_tokens=180, estimated_cost_usd=0.002),
    )

    report = BenchmarkReport.from_results("MySuite", "TestAgent", [r1, r2])

    assert report.metrics.total_tasks == 2
    assert report.metrics.passed_tasks == 1
    assert report.metrics.failed_tasks == 1
    assert report.metrics.pass_rate == 50.0
    assert report.metrics.average_score == 0.75
    assert report.metrics.total_execution_time_seconds == 4.0
    assert report.metrics.total_tool_calls == 3
    assert report.metrics.total_retries == 1
    assert report.metrics.token_usage.total_tokens == 300
    assert report.metrics.tool_usage_breakdown == {"tool_a": 2, "tool_b": 1}
