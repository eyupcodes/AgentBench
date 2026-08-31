"""Terminal and Markdown formatters for benchmark results and metrics."""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentbench.models.report import BenchmarkReport
from agentbench.models.result import RunStatus


def print_cli_report(report: BenchmarkReport, console: Optional[Console] = None, show_evals: bool = True) -> None:
    """Render a visually clear summary of the benchmark run using Rich."""
    console = console or Console()

    # Overall Summary Table / Banner
    pass_color = "green" if report.metrics.pass_rate >= 80 else ("yellow" if report.metrics.pass_rate >= 50 else "red")
    
    summary_text = Text()
    summary_text.append(f"Suite: ", style="bold")
    summary_text.append(f"{report.suite_name} (v{report.suite_version})\n")
    summary_text.append(f"Agent: ", style="bold")
    summary_text.append(f"{report.agent_name}\n")
    summary_text.append(f"Pass Rate: ", style="bold")
    summary_text.append(f"{report.metrics.pass_rate}% ", style=f"bold {pass_color}")
    summary_text.append(f"({report.metrics.passed_tasks}/{report.metrics.total_tasks} passed)\n")
    summary_text.append(f"Avg Score: ", style="bold")
    summary_text.append(f"{report.metrics.average_score * 100:.1f}%\n")
    summary_text.append(f"Total Time: ", style="bold")
    summary_text.append(f"{report.metrics.total_execution_time_seconds:.2f}s (avg {report.metrics.average_execution_time_seconds:.2f}s/task)\n")
    summary_text.append(f"Tool Calls: ", style="bold")
    summary_text.append(f"{report.metrics.total_tool_calls} total (avg {report.metrics.average_tool_calls_per_task:.1f}/task)\n")
    summary_text.append(f"Retries: ", style="bold")
    summary_text.append(f"{report.metrics.total_retries}\n")
    summary_text.append(f"Tokens / Cost: ", style="bold")
    summary_text.append(
        f"{report.metrics.token_usage.total_tokens:,} tokens (${report.metrics.token_usage.estimated_cost_usd:.4f})"
    )

    console.print(Panel(summary_text, title="[bold cyan]AgentBench Execution Summary[/bold cyan]", border_style="cyan"))

    # Itemized Tasks Table
    table = Table(title="Task Results", show_lines=True)
    table.add_column("Task ID", style="bold", no_wrap=True)
    table.add_column("Name")
    table.add_column("Status", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("Tools", justify="right")
    table.add_column("Retries", justify="right")
    table.add_column("Error / Notes")

    for r in report.results:
        if r.status == RunStatus.SUCCESS and r.passed:
            status_disp = Text("PASS", style="bold green")
        elif r.status == RunStatus.TIMEOUT:
            status_disp = Text("TIMEOUT", style="bold red")
        elif r.status == RunStatus.ERROR:
            status_disp = Text("ERROR", style="bold magenta")
        else:
            status_disp = Text("FAIL", style="bold red")

        score_disp = f"{r.overall_score * 100:.0f}%"
        notes = r.error if r.error else ("" if r.passed else "; ".join(e.reason for e in r.evaluations if not e.passed and e.reason))

        table.add_row(
            r.task_id,
            r.task_name,
            status_disp,
            score_disp,
            f"{r.execution_time_seconds:.2f}",
            str(len(r.tool_calls)),
            str(r.retry_count),
            notes or "-",
        )

    console.print(table)


def generate_markdown_report(report: BenchmarkReport) -> str:
    """Generate a clean markdown report string."""
    lines = [
        f"# Benchmark Report: {report.suite_name}",
        "",
        f"- **Agent**: `{report.agent_name}`",
        f"- **Suite Version**: `{report.suite_version}`",
        f"- **Timestamp**: `{report.timestamp.isoformat()}`",
        f"- **Pass Rate**: **{report.metrics.pass_rate}%** ({report.metrics.passed_tasks}/{report.metrics.total_tasks})",
        f"- **Average Score**: **{report.metrics.average_score * 100:.1f}%**",
        f"- **Total Time**: {report.metrics.total_execution_time_seconds:.2f}s",
        f"- **Total Tool Calls**: {report.metrics.total_tool_calls}",
        f"- **Total Retries**: {report.metrics.total_retries}",
        f"- **Total Tokens**: {report.metrics.token_usage.total_tokens:,} (${report.metrics.token_usage.estimated_cost_usd:.4f})",
        "",
        "## Task Details",
        "",
        "| Task ID | Task Name | Status | Score | Duration (s) | Tools Used | Retries | Details |",
        "|---|---|:---:|:---:|:---:|:---:|:---:|---|",
    ]

    for r in report.results:
        status_str = "✅ PASS" if (r.status == RunStatus.SUCCESS and r.passed) else f"❌ {r.status.value.upper()}"
        reasons = r.error or ("; ".join(e.reason for e in r.evaluations if not e.passed and e.reason) if not r.passed else "All checks passed")
        lines.append(
            f"| `{r.task_id}` | {r.task_name} | {status_str} | {r.overall_score * 100:.0f}% | {r.execution_time_seconds:.2f} | {len(r.tool_calls)} | {r.retry_count} | {reasons} |"
        )

    lines.append("")
    return "\n".join(lines)
