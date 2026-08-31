"""Core Benchmark Runner for executing agent tasks with timeouts, retries, and evaluations."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional

from agentbench.adapters.base import AgentExecutionContext, AgentResponse, BaseAgent
from agentbench.evaluators.base import EvaluationContext
from agentbench.evaluators.registry import build_evaluators_for_task
from agentbench.models.event import AgentEvent, EventType, TokenUsage
from agentbench.models.report import BenchmarkReport
from agentbench.models.result import EvaluationResult, RunStatus, TaskRunResult
from agentbench.models.task import Task, TaskSuite
from agentbench.runner.context import RunnerOptions


class BenchmarkRunner:
    """Orchestrates benchmark runs across tasks and agent adapters."""

    def __init__(
        self,
        options: Optional[RunnerOptions] = None,
        on_event: Optional[Callable[[AgentEvent], None]] = None,
        on_task_start: Optional[Callable[[Task], None]] = None,
        on_task_complete: Optional[Callable[[TaskRunResult], None]] = None,
    ) -> None:
        self.options = options or RunnerOptions()
        self.on_event = on_event
        self.on_task_start = on_task_start
        self.on_task_complete = on_task_complete

    async def run_task(self, task: Task, agent: BaseAgent) -> TaskRunResult:
        """Execute a single task against an agent with retry and timeout accounting."""
        if self.on_task_start:
            self.on_task_start(task)

        start_wall_time = time.perf_counter()
        started_at = datetime.now(timezone.utc)

        max_attempts = max(1, task.max_retries)
        timeout_sec = task.timeout_seconds if task.timeout_seconds > 0 else self.options.default_timeout_seconds

        all_events: List[AgentEvent] = []
        all_tool_calls = []
        cumulative_tokens = TokenUsage()
        retry_count = 0

        last_error: Optional[str] = None
        last_status = RunStatus.ERROR
        agent_response: Optional[AgentResponse] = None

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                retry_count += 1
                retry_ev = AgentEvent(
                    event_type=EventType.RETRY,
                    retry_attempt=attempt,
                    message=f"Retrying task {task.id} (attempt {attempt}/{max_attempts})",
                )
                all_events.append(retry_ev)
                if self.on_event:
                    self.on_event(retry_ev)
                if self.options.retry_delay_seconds > 0:
                    await asyncio.sleep(self.options.retry_delay_seconds)

            # Create fresh context for this attempt
            def _event_handler(ev: AgentEvent) -> None:
                all_events.append(ev)
                if self.on_event:
                    self.on_event(ev)

            context = AgentExecutionContext(task=task, event_callback=_event_handler)
            start_ev = AgentEvent(
                event_type=EventType.TASK_START,
                message=f"Starting task {task.id} attempt {attempt}",
            )
            context.emit(start_ev)

            try:
                # Execute agent with strict timeout
                resp = await asyncio.wait_for(
                    agent.run(task, context),
                    timeout=timeout_sec,
                )
                agent_response = resp
                all_tool_calls.extend(context.tool_calls)
                cumulative_tokens = cumulative_tokens.add(context.token_usage)
                last_status = RunStatus.SUCCESS
                last_error = None
                break  # Successful execution (we will evaluate below)

            except asyncio.TimeoutError:
                last_status = RunStatus.TIMEOUT
                last_error = f"Task exceeded timeout of {timeout_sec}s"
                all_tool_calls.extend(context.tool_calls)
                cumulative_tokens = cumulative_tokens.add(context.token_usage)
                err_ev = AgentEvent(
                    event_type=EventType.ERROR,
                    message=last_error,
                )
                all_events.append(err_ev)
                if self.on_event:
                    self.on_event(err_ev)

            except Exception as e:
                last_status = RunStatus.ERROR
                last_error = f"{type(e).__name__}: {str(e)}"
                all_tool_calls.extend(context.tool_calls)
                cumulative_tokens = cumulative_tokens.add(context.token_usage)
                err_ev = AgentEvent(
                    event_type=EventType.ERROR,
                    message=last_error,
                )
                all_events.append(err_ev)
                if self.on_event:
                    self.on_event(err_ev)

        execution_time = round(time.perf_counter() - start_wall_time, 4)
        completed_at = datetime.now(timezone.utc)

        # Run evaluators if we got an agent response
        evaluations: List[EvaluationResult] = []
        overall_passed = False
        overall_score = 0.0

        raw_output = agent_response.output if agent_response else None

        if last_status == RunStatus.SUCCESS and agent_response is not None:
            eval_ctx = EvaluationContext(
                task=task,
                output=raw_output,
                tool_calls=all_tool_calls,
                events=all_events,
                execution_time_seconds=execution_time,
                error=last_error,
                retry_count=retry_count,
            )

            evaluators = build_evaluators_for_task(task)
            if evaluators:
                for evaluator in evaluators:
                    res = evaluator.evaluate(eval_ctx)
                    evaluations.append(res)

                overall_passed = all(ev.passed for ev in evaluations)
                overall_score = round(
                    sum(ev.score for ev in evaluations) / len(evaluations), 4
                )
            else:
                # If no evaluators configured, execution success counts as passed
                overall_passed = True
                overall_score = 1.0

            if not overall_passed:
                last_status = RunStatus.FAILURE

        result = TaskRunResult(
            task_id=task.id,
            task_name=task.name,
            agent_name=agent.name,
            status=last_status,
            output=raw_output,
            error=last_error,
            execution_time_seconds=execution_time,
            retry_count=retry_count,
            tool_calls=all_tool_calls,
            events=all_events,
            token_usage=cumulative_tokens,
            evaluations=evaluations,
            passed=overall_passed,
            overall_score=overall_score,
            started_at=started_at,
            completed_at=completed_at,
        )

        if self.on_task_complete:
            self.on_task_complete(result)

        return result

    async def run_suite(self, suite: TaskSuite, agent: BaseAgent) -> BenchmarkReport:
        """Run all tasks in a TaskSuite against the specified agent adapter."""
        results: List[TaskRunResult] = []

        if self.options.max_concurrency <= 1:
            for task in suite.tasks:
                res = await self.run_task(task, agent)
                results.append(res)
                if self.options.stop_on_first_failure and not res.passed:
                    break
        else:
            semaphore = asyncio.Semaphore(self.options.max_concurrency)

            async def _run_bounded(t: Task) -> TaskRunResult:
                async with semaphore:
                    return await self.run_task(t, agent)

            results = await asyncio.gather(*[_run_bounded(t) for t in suite.tasks])

        return BenchmarkReport.from_results(
            suite_name=suite.name,
            agent_name=agent.name,
            results=results,
            suite_version=suite.version,
            metadata=suite.metadata,
        )
