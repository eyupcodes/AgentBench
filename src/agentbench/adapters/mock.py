"""Mock agent adapter for deterministic testing and simulation."""

import asyncio
from typing import Any, Dict, List, Optional
from agentbench.adapters.base import AgentExecutionContext, AgentResponse, BaseAgent
from agentbench.models.task import Task


class MockAgent(BaseAgent):
    """A configurable mock agent for unit tests, dry-runs, and deterministic benchmarks.

    Attributes:
        default_response: Output returned if no specific task match is found.
        responses: Mapping of task_id or prompt substring to response output.
        tool_call_plans: Mapping of task_id to list of tool calls to simulate.
        delay_seconds: Simulated execution delay.
        simulate_error: If True or error message, raises an exception during run.
        tokens_per_call: Token usage tuple (prompt_tokens, completion_tokens).
    """

    def __init__(
        self,
        name: str = "MockAgent",
        default_response: Any = "Mock response",
        responses: Optional[Dict[str, Any]] = None,
        tool_call_plans: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        delay_seconds: float = 0.0,
        simulate_error: Optional[str] = None,
        tokens_per_call: Optional[Dict[str, int]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(name=name, config=config)
        self.default_response = default_response
        self.responses = responses or {}
        self.tool_call_plans = tool_call_plans or {}
        self.delay_seconds = delay_seconds
        self.simulate_error = simulate_error
        self.tokens_per_call = tokens_per_call or {"prompt_tokens": 100, "completion_tokens": 50}

    async def run(self, task: Task, context: AgentExecutionContext) -> AgentResponse:
        context.record_thought(f"Starting mock execution for task {task.id}")

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.simulate_error:
            raise RuntimeError(f"MockAgent simulated failure: {self.simulate_error}")

        # Simulate tool calls if planned for this task
        simulated_tools = self.tool_call_plans.get(task.id, [])
        for tool_plan in simulated_tools:
            tool_name = tool_plan.get("name", "generic_tool")
            tool_input = tool_plan.get("input", {})
            tool_output = tool_plan.get("output", {"status": "ok"})
            duration = tool_plan.get("duration_ms", 15.0)
            status = tool_plan.get("status", "success")
            err = tool_plan.get("error")

            context.record_thought(f"Executing tool {tool_name}")
            context.record_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                duration_ms=duration,
                status=status,
                error=err,
            )

        # Record simulated token usage
        context.record_token_usage(
            prompt_tokens=self.tokens_per_call.get("prompt_tokens", 100),
            completion_tokens=self.tokens_per_call.get("completion_tokens", 50),
            estimated_cost_usd=self.tokens_per_call.get("cost_usd", 0.0003),
        )

        # Determine output
        output = self.responses.get(task.id, self.default_response)

        # If task has expected output and mock is set to echo expected (helpful for auto-pass testing)
        if output == "__EXPECTED__" and task.expected_output is not None:
            output = task.expected_output

        return AgentResponse(
            output=output,
            tool_calls=list(context.tool_calls),
            token_usage=context.token_usage,
        )
