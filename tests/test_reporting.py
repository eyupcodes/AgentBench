"""Unit tests for reporting and serialization."""

import tempfile
from pathlib import Path

from agentbench.models.event import TokenUsage, ToolCallEvent
from agentbench.models.report import BenchmarkReport
from agentbench.models.result import RunStatus, TaskRunResult
from agentbench.reporting.formatter import generate_markdown_report
from agentbench.reporting.json_report import load_report_json, save_report_json


def test_json_report_serialization():
    r1 = TaskRunResult(
        task_id="t1",
        task_name="Task 1",
        agent_name="MockAgent",
        status=RunStatus.SUCCESS,
        passed=True,
        overall_score=1.0,
        output="42",
    )
    report = BenchmarkReport.from_results(
        suite_name="MathSuite",
        agent_name="MockAgent",
        results=[r1],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = Path(tmpdir) / "report.json"
        saved = save_report_json(report, json_file)
        assert saved.exists()

        loaded = load_report_json(json_file)
        assert loaded.suite_name == "MathSuite"
        assert loaded.metrics.passed_tasks == 1
        assert loaded.results[0].output == "42"


def test_markdown_report_generation():
    r1 = TaskRunResult(
        task_id="t1",
        task_name="Task 1",
        agent_name="MockAgent",
        status=RunStatus.SUCCESS,
        passed=True,
        overall_score=1.0,
    )
    report = BenchmarkReport.from_results("DemoSuite", "MockAgent", [r1])
    md = generate_markdown_report(report)

    assert "# Benchmark Report: DemoSuite" in md
    assert "**100.0%**" in md
    assert "| `t1` | Task 1 | ✅ PASS |" in md


def test_mixed_results_metrics_survive_json_round_trip(tmp_path):
    results = [
        TaskRunResult(
            task_id=f"t{index}",
            task_name=f"Task {index}",
            agent_name="TestAgent",
            status=status,
            passed=passed,
            overall_score=score,
            execution_time_seconds=index / 10,
            retry_count=index - 1,
            tool_calls=[ToolCallEvent(tool_name="search" if passed else "lookup")],
            token_usage=TokenUsage(
                prompt_tokens=index * 10,
                completion_tokens=index,
                total_tokens=index * 11,
                estimated_cost_usd=index * 0.001,
            ),
        )
        for index, (status, passed, score) in enumerate(
            [
                (RunStatus.SUCCESS, True, 1.0),
                (RunStatus.SUCCESS, False, 0.5),
                (RunStatus.FAILURE, False, 0.25),
                (RunStatus.TIMEOUT, False, 0.0),
                (RunStatus.ERROR, False, 0.0),
            ],
            start=1,
        )
    ]
    report = BenchmarkReport.from_results("MixedSuite", "TestAgent", results)

    metrics = report.metrics
    assert metrics.total_tasks == 5
    assert metrics.passed_tasks == 1
    assert metrics.failed_tasks == 2
    assert metrics.timeout_tasks == 1
    assert metrics.error_tasks == 1
    assert metrics.pass_rate == 20.0
    assert metrics.average_score == 0.35
    assert metrics.total_execution_time_seconds == 1.5
    assert metrics.average_execution_time_seconds == 0.3
    assert metrics.total_tool_calls == 5
    assert metrics.average_tool_calls_per_task == 1.0
    assert metrics.total_retries == 10
    assert metrics.token_usage == TokenUsage(
        prompt_tokens=150,
        completion_tokens=15,
        total_tokens=165,
        estimated_cost_usd=0.015,
    )
    assert metrics.tool_usage_breakdown == {"search": 1, "lookup": 4}

    path = tmp_path / "nested" / "report.json"
    assert save_report_json(report, path) == path
    assert load_report_json(path) == report


def test_load_report_json_accepts_utf8_bom(tmp_path):
    report = BenchmarkReport.from_results("S", "Agent", [])
    path = tmp_path / "report.json"
    path.write_bytes(b"\xef\xbb\xbf" + report.model_dump_json().encode("utf-8"))

    assert load_report_json(path) == report


def test_empty_report_json_round_trip(tmp_path):
    report = BenchmarkReport.from_results("EmptySuite", "TestAgent", [])
    metrics = report.metrics
    assert metrics.total_tasks == 0
    assert metrics.pass_rate == 0.0
    assert metrics.average_score == 0.0
    assert metrics.average_execution_time_seconds == 0.0
    assert metrics.average_tool_calls_per_task == 0.0
    assert metrics.token_usage == TokenUsage()
    assert metrics.tool_usage_breakdown == {}

    path = tmp_path / "empty.json"
    save_report_json(report, path)
    assert load_report_json(path) == report
