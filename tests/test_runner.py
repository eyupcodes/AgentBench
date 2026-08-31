"""Unit tests for BenchmarkRunner, timeout handling, retries, and suite execution."""

import pytest
from agentbench.adapters.mock import MockAgent
from agentbench.models.result import RunStatus
from agentbench.models.task import EvaluatorConfig, Task, TaskSuite
from agentbench.runner.context import RunnerOptions
from agentbench.runner.runner import BenchmarkRunner


@pytest.mark.asyncio
async def test_runner_successful_task():
    task = Task(
        id="t1",
        name="Successful Task",
        prompt="echo",
        expected_output="expected_val",
        evaluators=[EvaluatorConfig(type="exact_match", expected="expected_val")],
    )
    agent = MockAgent(default_response="expected_val")
    runner = BenchmarkRunner()

    result = await runner.run_task(task, agent)

    assert result.status == RunStatus.SUCCESS
    assert result.passed is True
    assert result.overall_score == 1.0
    assert result.retry_count == 0
    assert len(result.events) > 0


@pytest.mark.asyncio
async def test_runner_timeout_handling():
    task = Task(
        id="t_timeout",
        name="Timeout Task",
        prompt="slow prompt",
        timeout_seconds=0.1,
        max_retries=1,
    )
    # Agent sleeps for 0.5s, exceeding 0.1s timeout
    agent = MockAgent(delay_seconds=0.5)
    runner = BenchmarkRunner()

    result = await runner.run_task(task, agent)

    assert result.status == RunStatus.TIMEOUT
    assert result.passed is False
    assert "timeout" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_runner_retry_accounting():
    task = Task(
        id="t_retry",
        name="Retry Task",
        prompt="fail then check retries",
        max_retries=3,
    )
    agent = MockAgent(simulate_error="Temporary backend error")
    options = RunnerOptions(retry_delay_seconds=0.01)
    runner = BenchmarkRunner(options=options)

    result = await runner.run_task(task, agent)

    assert result.status == RunStatus.ERROR
    assert result.passed is False
    assert result.retry_count == 2  # 3 attempts total = initial + 2 retries


@pytest.mark.asyncio
async def test_runner_suite_execution():
    suite = TaskSuite(
        name="Demo Suite",
        tasks=[
            Task(
                id="task_1",
                name="Task 1",
                prompt="p1",
                expected_output="val1",
                evaluators=[EvaluatorConfig(type="exact_match", expected="val1")],
            ),
            Task(
                id="task_2",
                name="Task 2",
                prompt="p2",
                expected_output="val2",
                evaluators=[EvaluatorConfig(type="exact_match", expected="val2")],
            ),
        ],
    )
    agent = MockAgent(responses={"task_1": "val1", "task_2": "wrong_val"})
    runner = BenchmarkRunner()

    report = await runner.run_suite(suite, agent)

    assert report.metrics.total_tasks == 2
    assert report.metrics.passed_tasks == 1
    assert report.metrics.failed_tasks == 1
    assert report.metrics.pass_rate == 50.0
    assert len(report.results) == 2
