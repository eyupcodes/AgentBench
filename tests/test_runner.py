"""Unit tests for BenchmarkRunner, timeout handling, retries, and suite execution."""

import pytest

from agentbench.adapters.mock import MockAgent
from agentbench.evaluators.base import BaseEvaluator
from agentbench.evaluators.registry import register_evaluator
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


class _RaisingEvaluator(BaseEvaluator):
    def evaluate(self, context):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_runner_survives_raising_evaluator():
    register_evaluator("raising_test", _RaisingEvaluator)
    suite = TaskSuite(
        name="Resilience",
        tasks=[
            Task(
                id="bad",
                name="Bad",
                prompt="p",
                evaluators=[EvaluatorConfig(type="raising_test")],
            ),
            Task(
                id="good",
                name="Good",
                prompt="p",
                evaluators=[EvaluatorConfig(type="exact_match", expected="ok")],
            ),
        ],
    )
    report = await BenchmarkRunner().run_suite(
        suite, MockAgent(responses={"bad": "x", "good": "ok"})
    )

    by_id = {r.task_id: r for r in report.results}
    assert by_id["bad"].passed is False
    assert by_id["bad"].status == RunStatus.FAILURE
    assert "RuntimeError: boom" in by_id["bad"].evaluations[0].reason
    assert by_id["good"].passed is True


@pytest.mark.asyncio
async def test_runner_reports_unknown_evaluator_type_as_failure():
    suite = TaskSuite(
        name="Typo",
        tasks=[
            Task(
                id="t",
                name="T",
                prompt="p",
                evaluators=[EvaluatorConfig(type="exact_mtach", expected="ok")],
            )
        ],
    )
    report = await BenchmarkRunner().run_suite(suite, MockAgent(responses={"t": "ok"}))

    result = report.results[0]
    assert result.passed is False
    assert result.evaluations[0].evaluator_type == "setup"
    assert "exact_mtach" in result.evaluations[0].reason


def _failfast_suite() -> TaskSuite:
    return TaskSuite(
        name="Fail Fast",
        tasks=[
            Task(
                id=f"t{i}",
                name=f"Task {i}",
                prompt="p",
                expected_output="ok",
                evaluators=[EvaluatorConfig(type="exact_match", expected="ok")],
            )
            for i in range(1, 5)
        ],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("concurrency", [1, 2])
async def test_runner_stop_on_first_failure_skips_remaining_tasks(concurrency):
    agent = MockAgent(
        responses={"t1": "ok", "t2": "wrong", "t3": "ok", "t4": "ok"},
    )
    runner = BenchmarkRunner(
        RunnerOptions(max_concurrency=concurrency, stop_on_first_failure=True)
    )

    report = await runner.run_suite(_failfast_suite(), agent)

    ids = [r.task_id for r in report.results]
    assert ids[:2] == ["t1", "t2"]
    assert "t4" not in ids
    assert report.metrics.failed_tasks == 1


@pytest.mark.asyncio
async def test_runner_concurrent_runs_all_tasks_without_fail_fast():
    agent = MockAgent(responses={"t1": "ok", "t2": "wrong", "t3": "ok", "t4": "ok"})
    runner = BenchmarkRunner(RunnerOptions(max_concurrency=2))

    report = await runner.run_suite(_failfast_suite(), agent)

    assert [r.task_id for r in report.results] == ["t1", "t2", "t3", "t4"]
    assert report.metrics.failed_tasks == 1


def _weighted_task(w_pass: float, w_fail: float) -> Task:
    return Task(
        id="t_weighted",
        name="Weighted Task",
        prompt="echo",
        evaluators=[
            EvaluatorConfig(type="exact_match", expected="ok", weight=w_pass),
            EvaluatorConfig(type="exact_match", expected="nope", weight=w_fail),
        ],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("w_pass", "w_fail", "expected_score"),
    [(3.0, 1.0, 0.75), (1.0, 1.0, 0.5), (0.0, 0.0, 0.5), (0.0, 2.0, 0.0)],
)
async def test_runner_overall_score_uses_evaluator_weights(
    w_pass, w_fail, expected_score
):
    result = await BenchmarkRunner().run_task(
        _weighted_task(w_pass, w_fail), MockAgent(default_response="ok")
    )

    assert result.overall_score == expected_score
    assert result.passed is False  # every evaluator must still pass


def test_evaluator_weight_must_not_be_negative():
    with pytest.raises(ValueError):
        EvaluatorConfig(type="exact_match", expected="x", weight=-1.0)
