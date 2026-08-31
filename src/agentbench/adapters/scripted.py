"""Scripted rule-based agent for deterministic scenario evaluations."""

from typing import Any, Callable, Dict, Optional
from agentbench.adapters.base import AgentExecutionContext, AgentResponse, BaseAgent
from agentbench.models.task import Task


class ScriptedAgent(BaseAgent):
    """An agent that follows explicit programmable rules or functions per task.

    Can be used for gold-standard oracle baselines or deterministic baseline comparisons.
    """

    def __init__(
        self,
        name: str = "ScriptedAgent",
        handlers: Optional[Dict[str, Callable[[Task, AgentExecutionContext], Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(name=name, config=config)
        self.handlers = handlers or {}

    def register_handler(self, task_id: str, handler: Callable[[Task, AgentExecutionContext], Any]) -> None:
        """Register a dynamic python handler for a specific task ID."""
        self.handlers[task_id] = handler

    async def run(self, task: Task, context: AgentExecutionContext) -> AgentResponse:
        context.record_thought(f"Looking up scripted handler for task {task.id}")

        if task.id in self.handlers:
            handler = self.handlers[task.id]
            result = handler(task, context)
            if hasattr(result, "__await__"):
                result = await result
            return AgentResponse(
                output=result,
                tool_calls=list(context.tool_calls),
                token_usage=context.token_usage,
            )

        # Default handler: parse task prompt or answer basic math/json
        context.record_thought("No specific scripted rule found, falling back to default heuristic")
        prompt = task.prompt.strip()

        # If prompt contains expected format like "Calculate: 2 + 2"
        if prompt.lower().startswith("echo:"):
            output = prompt[5:].strip()
        elif prompt.lower().startswith("json:"):
            import json
            try:
                output = json.loads(prompt[5:].strip())
            except Exception:
                output = prompt[5:].strip()
        else:
            output = task.expected_output if task.expected_output is not None else "OK"

        return AgentResponse(
            output=output,
            tool_calls=list(context.tool_calls),
            token_usage=context.token_usage,
        )
