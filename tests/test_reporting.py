"""Unit tests for reporting and serialization."""

from pathlib import Path
import tempfile
from agentbench.models.report import BenchmarkReport
from agentbench.models.result import RunStatus, TaskRunResult
from agentbench.reporting.formatter import generate_markdown_report, print_cli_report
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
