"""Benchmark report models for aggregated metrics and serialization."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agentbench.models.result import RunStatus, TaskRunResult
from agentbench.models.event import TokenUsage


class SuiteMetrics(BaseModel):
    """Aggregated numerical and statistical metrics across a benchmark suite."""
    total_tasks: int = 0
    passed_tasks: int = 0
    failed_tasks: int = 0
    timeout_tasks: int = 0
    error_tasks: int = 0
    pass_rate: float = 0.0
    average_score: float = 0.0
    total_execution_time_seconds: float = 0.0
    average_execution_time_seconds: float = 0.0
    total_tool_calls: int = 0
    average_tool_calls_per_task: float = 0.0
    total_retries: int = 0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    tool_usage_breakdown: Dict[str, int] = Field(default_factory=dict)


class BenchmarkReport(BaseModel):
    """Complete benchmark report containing suite configuration, metrics, and itemized results."""
    suite_name: str
    suite_version: str = "1.0"
    agent_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: SuiteMetrics = Field(default_factory=SuiteMetrics)
    results: List[TaskRunResult] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_results(
        cls,
        suite_name: str,
        agent_name: str,
        results: List[TaskRunResult],
        suite_version: str = "1.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "BenchmarkReport":
        """Compute aggregate metrics and construct a BenchmarkReport."""
        total = len(results)
        passed = sum(1 for r in results if r.status == RunStatus.SUCCESS and r.passed)
        failed = sum(1 for r in results if r.status == RunStatus.FAILURE or (r.status == RunStatus.SUCCESS and not r.passed))
        timeouts = sum(1 for r in results if r.status == RunStatus.TIMEOUT)
        errors = sum(1 for r in results if r.status == RunStatus.ERROR)

        pass_rate = round((passed / total) * 100.0, 2) if total > 0 else 0.0
        avg_score = round(sum(r.overall_score for r in results) / total, 4) if total > 0 else 0.0
        total_time = round(sum(r.execution_time_seconds for r in results), 3)
        avg_time = round(total_time / total, 3) if total > 0 else 0.0

        total_tool_calls = sum(len(r.tool_calls) for r in results)
        avg_tool_calls = round(total_tool_calls / total, 2) if total > 0 else 0.0
        total_retries = sum(r.retry_count for r in results)

        agg_tokens = TokenUsage()
        tool_counts: Dict[str, int] = {}
        for r in results:
            agg_tokens = agg_tokens.add(r.token_usage)
            for tc in r.tool_calls:
                tool_counts[tc.tool_name] = tool_counts.get(tc.tool_name, 0) + 1

        metrics = SuiteMetrics(
            total_tasks=total,
            passed_tasks=passed,
            failed_tasks=failed,
            timeout_tasks=timeouts,
            error_tasks=errors,
            pass_rate=pass_rate,
            average_score=avg_score,
            total_execution_time_seconds=total_time,
            average_execution_time_seconds=avg_time,
            total_tool_calls=total_tool_calls,
            average_tool_calls_per_task=avg_tool_calls,
            total_retries=total_retries,
            token_usage=agg_tokens,
            tool_usage_breakdown=tool_counts,
        )

        return cls(
            suite_name=suite_name,
            suite_version=suite_version,
            agent_name=agent_name,
            metrics=metrics,
            results=results,
            metadata=metadata or {},
        )
