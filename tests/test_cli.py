"""Integration tests for Typer CLI commands."""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentbench.adapters.mock import MockAgent
from agentbench.adapters.registry import _ADAPTER_REGISTRY
from agentbench.cli import app
from agentbench.loader import save_suite
from agentbench.models.task import EvaluatorConfig, Task, TaskSuite

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AgentBench version" in result.stdout


def test_cli_list_commands():
    res_adapters = runner.invoke(app, ["list-adapters"])
    assert res_adapters.exit_code == 0
    assert "mock" in res_adapters.stdout

    res_evals = runner.invoke(app, ["list-evaluators"])
    assert res_evals.exit_code == 0
    assert "exact_match" in res_evals.stdout


def test_cli_init_and_validate():
    with tempfile.TemporaryDirectory() as tmpdir:
        res_init = runner.invoke(app, ["init", "--dir", tmpdir])
        assert res_init.exit_code == 0

        suite_path = Path(tmpdir) / "sample_suite.yaml"
        assert suite_path.exists()

        res_validate = runner.invoke(app, ["validate", str(suite_path)])
        assert res_validate.exit_code == 0
        assert "Suite is valid!" in res_validate.stdout


def test_cli_run_suite():
    with tempfile.TemporaryDirectory() as tmpdir:
        suite = TaskSuite(
            name="CLI Test Suite",
            tasks=[
                Task(
                    id="t1",
                    name="CLI Task 1",
                    prompt="echo: Hello",
                    expected_output="Hello",
                    evaluators=[EvaluatorConfig(type="exact_match", expected="Hello")],
                )
            ],
        )
        suite_path = Path(tmpdir) / "test_suite.yaml"
        save_suite(suite, suite_path)
        out_json = Path(tmpdir) / "report.json"
        out_md = Path(tmpdir) / "report.md"

        res_run = runner.invoke(
            app,
            [
                "run",
                "--suite",
                str(suite_path),
                "--agent",
                "scripted",
                "--output",
                str(out_json),
                "--export-md",
                str(out_md),
            ],
        )

        assert res_run.exit_code == 0
        assert out_json.exists()
        assert out_md.exists()

        # Test viewing saved report
        res_report = runner.invoke(app, ["report", str(out_json)])
        assert res_report.exit_code == 0
        assert "AgentBench Execution Summary" in res_report.stdout


def _write_suite(directory: Path) -> Path:
    suite = TaskSuite(
        name="Option Suite",
        tasks=[
            Task(
                id="t1",
                name="Task 1",
                prompt="echo: Hello",
                evaluators=[EvaluatorConfig(type="exact_match", expected="Hello")],
            )
        ],
    )
    path = directory / "suite.yaml"
    save_suite(suite, path)
    return path


@pytest.mark.parametrize(
    "option",
    [
        ["--concurrency", "0"],
        ["--concurrency", "-2"],
        ["--timeout", "0"],
        ["--timeout", "-5"],
        ["--retries", "-1"],
    ],
)
def test_cli_run_rejects_invalid_numeric_options(tmp_path, option):
    suite_path = _write_suite(tmp_path)

    result = runner.invoke(
        app, ["run", "--suite", str(suite_path), "--agent", "scripted", *option]
    )

    assert result.exit_code == 2
    assert "Running suite" not in result.output


def test_cli_run_accepts_zero_retries(tmp_path):
    suite_path = _write_suite(tmp_path)

    result = runner.invoke(
        app,
        ["run", "-s", str(suite_path), "-a", "scripted", "--retries", "0"],
    )

    assert result.exit_code == 0


@pytest.mark.parametrize("flag", ["--output", "--export-md"])
def test_cli_run_reports_unwritable_output(tmp_path, flag):
    suite_path = _write_suite(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")

    result = runner.invoke(
        app,
        ["run", "-s", str(suite_path), "-a", "scripted", flag, str(blocker / "r.out")],
    )

    assert result.exit_code == 1
    assert "Failed to write report" in result.output
    assert not isinstance(result.exception, OSError)


def test_cli_run_fail_fast_skips_tasks_after_first_failure(tmp_path):
    suite = TaskSuite(
        name="Fail Fast Suite",
        tasks=[
            Task(
                id=f"t{i}",
                name=f"Task {i}",
                prompt="echo: nope",
                evaluators=[EvaluatorConfig(type="exact_match", expected="Hello")],
            )
            for i in range(1, 4)
        ],
    )
    suite_path = tmp_path / "suite.yaml"
    save_suite(suite, suite_path)
    out_json = tmp_path / "report.json"

    result = runner.invoke(
        app,
        [
            "run",
            "-s",
            str(suite_path),
            "-a",
            "scripted",
            "--fail-fast",
            "-o",
            str(out_json),
        ],
    )

    assert result.exit_code == 1
    report = json.loads(out_json.read_text(encoding="utf-8"))
    assert [r["task_id"] for r in report["results"]] == ["t1"]


def test_cli_run_fails_cleanly_for_missing_suite(tmp_path):
    result = runner.invoke(app, ["run", "-s", str(tmp_path / "missing.yaml")])

    assert result.exit_code == 1
    assert "Failed to load suite" in result.output
    assert "Traceback" not in result.output


def test_cli_run_fails_cleanly_for_unknown_agent(tmp_path):
    suite_path = _write_suite(tmp_path)

    result = runner.invoke(
        app, ["run", "-s", str(suite_path), "-a", "no_such_module.NoAgent"]
    )

    assert result.exit_code == 1
    assert "Failed to instantiate agent adapter" in result.output


def test_cli_run_verbose_prints_events(tmp_path):
    suite_path = _write_suite(tmp_path)

    result = runner.invoke(app, ["run", "-s", str(suite_path), "-a", "scripted", "-v"])

    assert result.exit_code == 0
    assert "[task_start]" in result.output


def test_cli_validate_rejects_invalid_suite(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: broken\ntasks: not-a-list\n", encoding="utf-8")

    result = runner.invoke(app, ["validate", str(bad)])

    assert result.exit_code == 1
    assert "Validation error" in result.output


def test_cli_init_does_not_overwrite_existing_suite(tmp_path):
    existing = tmp_path / "sample_suite.yaml"
    existing.write_text("keep: me\n", encoding="utf-8")

    result = runner.invoke(app, ["init", "--dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "already exists" in result.output
    assert existing.read_text(encoding="utf-8") == "keep: me\n"


def test_cli_report_renders_saved_report_as_table_and_markdown(tmp_path):
    suite_path = _write_suite(tmp_path)
    out_json = tmp_path / "report.json"
    run_result = runner.invoke(
        app, ["run", "-s", str(suite_path), "-a", "scripted", "-o", str(out_json)]
    )
    assert run_result.exit_code == 0

    table = runner.invoke(app, ["report", str(out_json)])
    markdown = runner.invoke(app, ["report", str(out_json), "--md"])

    assert table.exit_code == 0
    assert "Task 1" in table.output
    assert markdown.exit_code == 0
    assert "Option Suite" in markdown.output


def test_cli_report_fails_cleanly_for_unreadable_report(tmp_path):
    broken = tmp_path / "report.json"
    broken.write_text("{not json", encoding="utf-8")

    result = runner.invoke(app, ["report", str(broken)])

    assert result.exit_code == 1
    assert "Failed to load report" in result.output


def test_cli_run_survives_markup_like_text_in_task_errors(tmp_path):
    suite = TaskSuite(
        name="Brackets [/x]",
        tasks=[
            Task(
                id="t1",
                name="Task [bold]",
                prompt="echo: nope",
                expected_output="ok",
                evaluators=[EvaluatorConfig(type="exact_match", expected="ok")],
            )
        ],
    )
    suite_path = tmp_path / "suite.yaml"
    save_suite(suite, suite_path)

    result = runner.invoke(app, ["run", "-s", str(suite_path), "-a", "scripted", "-v"])

    assert result.exit_code == 1  # the task fails; the report must still render
    assert "Traceback" not in result.output
    assert "Brackets [/x]" in result.output


class _SlowAgent(MockAgent):
    def __init__(self, **kwargs):
        super().__init__(name="slow", delay_seconds=1.0, **kwargs)


class _BrokenAgent(MockAgent):
    def __init__(self, **kwargs):
        super().__init__(name="broken", simulate_error="boom", **kwargs)


@pytest.mark.parametrize(
    ("agent_cls", "extra_args"),
    [(_SlowAgent, ["--timeout", "0.05"]), (_BrokenAgent, [])],
    ids=["timeout", "error"],
)
def test_cli_run_exits_nonzero_on_timeout_or_error(
    tmp_path, monkeypatch, agent_cls, extra_args
):
    monkeypatch.setitem(_ADAPTER_REGISTRY, "flaky", agent_cls)
    suite_path = _write_suite(tmp_path)

    result = runner.invoke(
        app,
        ["run", "-s", str(suite_path), "-a", "flaky", "--retries", "0", *extra_args],
    )

    assert result.exit_code == 1


def _write_half_passing_suite(tmp_path):
    suite = TaskSuite(
        name="Half Suite",
        tasks=[
            Task(
                id=task_id,
                name=task_id,
                prompt=f"echo: {expected}",
                evaluators=[EvaluatorConfig(type="exact_match", expected="ok")],
            )
            for task_id, expected in (("pass", "ok"), ("fail", "nope"))
        ],
    )
    suite_path = tmp_path / "half.yaml"
    save_suite(suite, suite_path)
    return suite_path


def test_cli_run_min_pass_rate_met_exits_zero_despite_failures(tmp_path):
    suite_path = _write_half_passing_suite(tmp_path)

    result = runner.invoke(
        app,
        ["run", "-s", str(suite_path), "-a", "scripted", "--min-pass-rate", "50"],
    )

    assert result.exit_code == 0, result.output


def test_cli_run_min_pass_rate_not_met_exits_one(tmp_path):
    suite_path = _write_half_passing_suite(tmp_path)

    result = runner.invoke(
        app,
        ["run", "-s", str(suite_path), "-a", "scripted", "--min-pass-rate", "51"],
    )

    assert result.exit_code == 1
    assert "below the required 51" in result.output


@pytest.mark.parametrize("value", ["-1", "100.5"])
def test_cli_run_min_pass_rate_rejects_out_of_range(tmp_path, value):
    suite_path = _write_half_passing_suite(tmp_path)

    result = runner.invoke(
        app, ["run", "-s", str(suite_path), "--min-pass-rate", value]
    )

    assert result.exit_code == 2
