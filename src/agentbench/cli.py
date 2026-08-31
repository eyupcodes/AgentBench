"""Typer CLI interface for AgentBench."""

import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from agentbench import __version__
from agentbench.adapters.registry import get_adapter, list_adapters
from agentbench.evaluators.registry import list_evaluators
from agentbench.loader import load_suite, save_suite
from agentbench.models.task import EvaluatorConfig, Task, TaskSuite, ToolDefinition, ToolParameter
from agentbench.reporting.formatter import generate_markdown_report, print_cli_report
from agentbench.reporting.json_report import load_report_json, save_report_json
from agentbench.runner.context import RunnerOptions
from agentbench.runner.runner import BenchmarkRunner

app = typer.Typer(
    name="agentbench",
    help="AgentBench: Clean, deterministic benchmarking & evaluation harness for AI agents and tool workflows.",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    suite: Path = typer.Option(..., "--suite", "-s", help="Path to benchmark suite file (YAML or JSON)."),
    agent: str = typer.Option("mock", "--agent", "-a", help="Agent adapter name or dotted python class path."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="File path to save JSON report."),
    export_md: Optional[Path] = typer.Option(None, "--export-md", help="File path to export Markdown summary."),
    concurrency: int = typer.Option(1, "--concurrency", "-c", help="Number of tasks to execute concurrently."),
    timeout: Optional[float] = typer.Option(None, "--timeout", "-t", help="Override task timeout in seconds."),
    retries: Optional[int] = typer.Option(None, "--retries", "-r", help="Override max retry attempts."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show live execution event traces."),
) -> None:
    """Run a benchmark suite against an agent adapter."""
    try:
        task_suite = load_suite(suite)
    except Exception as e:
        console.print(f"[bold red]Failed to load suite:[/] {e}")
        raise typer.Exit(code=1)

    if timeout is not None:
        for t in task_suite.tasks:
            t.timeout_seconds = timeout

    if retries is not None:
        for t in task_suite.tasks:
            t.max_retries = retries

    try:
        agent_instance = get_adapter(agent)
    except Exception as e:
        console.print(f"[bold red]Failed to instantiate agent adapter '{agent}':[/] {e}")
        raise typer.Exit(code=1)

    console.print(
        f"[bold blue]AgentBench[/] Running suite '[bold cyan]{task_suite.name}[/]' "
        f"({len(task_suite.tasks)} tasks) against '[bold green]{agent_instance.name}[/]'"
    )

    def _event_logger(ev):
        if verbose:
            msg = ev.message or f"Event: {ev.event_type.value}"
            console.print(f"  [dim]• {ev.timestamp.strftime('%H:%M:%S')} [{ev.event_type.value}][/dim] {msg}")

    options = RunnerOptions(
        max_concurrency=concurrency,
        verbose=verbose,
    )
    runner = BenchmarkRunner(options=options, on_event=_event_logger if verbose else None)

    report = asyncio.run(runner.run_suite(task_suite, agent_instance))

    print_cli_report(report, console=console)

    if output:
        out_path = save_report_json(report, output)
        console.print(f"[bold green]Saved JSON report to:[/] {out_path}")

    if export_md:
        md_content = generate_markdown_report(report)
        export_md_path = Path(export_md)
        export_md_path.parent.mkdir(parents=True, exist_ok=True)
        with open(export_md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        console.print(f"[bold green]Saved Markdown summary to:[/] {export_md_path}")

    if report.metrics.pass_rate < 100.0 and report.metrics.failed_tasks > 0:
        # Exit with non-zero if tasks failed
        raise typer.Exit(code=1)


@app.command()
def validate(
    suite: Path = typer.Argument(..., help="Path to benchmark suite file (YAML or JSON) to validate."),
) -> None:
    """Validate suite syntax, task schema, and evaluators without executing."""
    try:
        task_suite = load_suite(suite)
        console.print(f"[bold green]Suite is valid![/]")
        console.print(f"  Name: [bold]{task_suite.name}[/]")
        console.print(f"  Version: {task_suite.version}")
        console.print(f"  Tasks: {len(task_suite.tasks)}")
        for t in task_suite.tasks:
            eval_names = [e.type for e in t.evaluators] or (["exact_match (default)"] if t.expected_output else ["none"])
            console.print(f"    - [cyan]{t.id}[/]: {t.name} (Evaluators: {', '.join(eval_names)})")
    except Exception as e:
        console.print(f"[bold red]Validation error:[/] {e}")
        raise typer.Exit(code=1)


@app.command(name="list-adapters")
def list_adapters_cmd() -> None:
    """List all registered agent adapters."""
    table = Table(title="Registered Agent Adapters")
    table.add_column("Adapter Name", style="bold green")
    table.add_column("Type", style="cyan")

    for name in list_adapters():
        table.add_row(name, "Built-in / Registered")

    console.print(table)


@app.command(name="list-evaluators")
def list_evaluators_cmd() -> None:
    """List all available deterministic evaluator hooks."""
    table = Table(title="Available Evaluators")
    table.add_column("Evaluator Type", style="bold cyan")
    table.add_column("Description")

    descs = {
        "exact_match": "Strict or normalized equality check against expected output",
        "contains": "Check presence of target substring(s) or key phrases",
        "regex": "Regular expression pattern match",
        "json_schema": "JSON structural and field value verification",
        "numeric_tolerance": "Float comparison within absolute/relative epsilon",
        "tool_call_count": "Assert tool invocation counts (min, max, exact)",
        "tool_call_sequence": "Assert sequence of tool calls in execution trace",
        "tool_argument": "Verify tool call arguments match expectations",
        "custom": "Execute a user-defined custom Python evaluation callable",
    }

    for name in list_evaluators():
        table.add_row(name, descs.get(name, "Custom / Registered Evaluator"))

    console.print(table)


@app.command()
def report(
    report_file: Path = typer.Argument(..., help="Path to saved JSON benchmark report."),
    md: bool = typer.Option(False, "--md", help="Output as Markdown instead of terminal table."),
) -> None:
    """Display an existing JSON benchmark report."""
    try:
        rep = load_report_json(report_file)
    except Exception as e:
        console.print(f"[bold red]Failed to load report:[/] {e}")
        raise typer.Exit(code=1)

    if md:
        console.print(generate_markdown_report(rep))
    else:
        print_cli_report(rep, console=console)


@app.command()
def init(
    target_dir: Path = typer.Option(Path("."), "--dir", "-d", help="Directory to initialize sample suite."),
) -> None:
    """Generate a starter benchmark suite YAML file and directory structure."""
    target_dir.mkdir(parents=True, exist_ok=True)
    sample_suite_file = target_dir / "sample_suite.yaml"

    if sample_suite_file.exists():
        console.print(f"[yellow]File {sample_suite_file} already exists. Skipping creation.[/yellow]")
        return

    sample_suite = TaskSuite(
        name="starter-suite",
        version="1.0",
        description="A starter benchmark suite showcasing deterministic evaluations and tool-calling checks.",
        tasks=[
            Task(
                id="task-math-01",
                name="Basic Arithmetic",
                prompt="Calculate the sum of 124 and 568.",
                expected_output="692",
                evaluators=[
                    EvaluatorConfig(type="exact_match", expected="692"),
                ],
            ),
            Task(
                id="task-tool-01",
                name="Weather Query with Tool Use",
                prompt="What is the weather in Berlin?",
                tools=[
                    ToolDefinition(
                        name="get_weather",
                        description="Fetch real-time weather information for a city",
                        parameters={"city": ToolParameter(type="string", required=True)},
                        mock_response={"city": "Berlin", "temperature": 18, "condition": "Sunny"},
                    )
                ],
                evaluators=[
                    EvaluatorConfig(
                        type="tool_call_count",
                        options={"tool_name": "get_weather", "min_calls": 1},
                    ),
                    EvaluatorConfig(
                        type="contains",
                        expected=["Berlin", "Sunny"],
                    ),
                ],
            ),
            Task(
                id="task-json-01",
                name="Structured JSON Output",
                prompt="Extract user details: Alice, age 30, city London",
                evaluators=[
                    EvaluatorConfig(
                        type="json_schema",
                        expected={"name": "Alice", "age": 30, "city": "London"},
                    )
                ],
            ),
        ],
    )

    save_suite(sample_suite, sample_suite_file)
    console.print(f"[bold green]Initialized sample suite:[/] {sample_suite_file}")
    console.print("Run it with:")
    console.print(f"  [cyan]agentbench run --suite {sample_suite_file} --agent mock[/cyan]")


@app.command()
def version() -> None:
    """Show AgentBench version."""
    console.print(f"AgentBench version: [bold green]{__version__}[/]")


if __name__ == "__main__":
    app()
