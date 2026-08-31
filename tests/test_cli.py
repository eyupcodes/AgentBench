"""Integration tests for Typer CLI commands."""

from pathlib import Path
import tempfile
from typer.testing import CliRunner
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
                "--suite", str(suite_path),
                "--agent", "scripted",
                "--output", str(out_json),
                "--export-md", str(out_md),
            ],
        )

        assert res_run.exit_code == 0
        assert out_json.exists()
        assert out_md.exists()

        # Test viewing saved report
        res_report = runner.invoke(app, ["report", str(out_json)])
        assert res_report.exit_code == 0
        assert "AgentBench Execution Summary" in res_report.stdout
