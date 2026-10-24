"""Unit tests for agent adapters and execution context."""

import asyncio

import pytest

from agentbench.adapters.base import AgentExecutionContext
from agentbench.adapters.mock import MockAgent
from agentbench.adapters.registry import get_adapter, list_adapters
from agentbench.adapters.scripted import ScriptedAgent
from agentbench.models.event import EventType
from agentbench.models.task import Task


@pytest.mark.asyncio
async def test_mock_agent_basic_run():
    task = Task(id="t1", name="Task 1", prompt="What is 2+2?", expected_output="4")
    agent = MockAgent(default_response="4")
    context = AgentExecutionContext(task=task)

    resp = await agent.run(task, context)

    assert resp.output == "4"
    assert len(context.events) >= 2
    assert any(e.event_type == EventType.THOUGHT for e in context.events)
    assert any(e.event_type == EventType.LLM_CALL for e in context.events)
    assert context.token_usage.total_tokens > 0


@pytest.mark.asyncio
async def test_mock_agent_tool_calls_simulation():
    task = Task(id="tool_task", name="Tool Task", prompt="Search web")
    agent = MockAgent(
        tool_call_plans={
            "tool_task": [
                {
                    "name": "web_search",
                    "input": {"query": "python"},
                    "output": {"results": ["python.org"]},
                }
            ]
        }
    )
    context = AgentExecutionContext(task=task)
    resp = await agent.run(task, context)

    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].tool_name == "web_search"
    assert resp.tool_calls[0].tool_input == {"query": "python"}


@pytest.mark.asyncio
async def test_mock_agent_simulated_error():
    task = Task(id="t_err", name="Err Task", prompt="Fail")
    agent = MockAgent(simulate_error="Server overloaded")
    context = AgentExecutionContext(task=task)

    with pytest.raises(RuntimeError, match="Server overloaded"):
        await agent.run(task, context)


@pytest.mark.asyncio
async def test_scripted_agent():
    task = Task(id="t_custom", name="Custom Script Task", prompt="echo: Custom Message")
    agent = ScriptedAgent()
    context = AgentExecutionContext(task=task)

    resp = await agent.run(task, context)
    assert resp.output == "Custom Message"

    # Test dynamic registered handler
    agent.register_handler("t_custom", lambda t, c: "Dynamic Handled")
    resp2 = await agent.run(task, context)
    assert resp2.output == "Dynamic Handled"


@pytest.mark.asyncio
async def test_scripted_agent_async_handler_preserves_context():
    task = Task(id="t_async", name="Async Script Task", prompt="echo: ignored")
    context = AgentExecutionContext(task=task)

    async def handler(received_task, received_context):
        await asyncio.sleep(0)
        assert received_task is task
        assert received_context is context
        received_context.record_tool_call(
            tool_name="lookup",
            tool_input={"city": "İstanbul"},
            tool_output={"temperature": 20},
        )
        received_context.record_token_usage(prompt_tokens=3, completion_tokens=2)
        return {"temperature": 20}

    agent = ScriptedAgent(handlers={task.id: handler})
    resp = await agent.run(task, context)

    assert resp.output == {"temperature": 20}
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls == context.tool_calls
    assert resp.tool_calls is not context.tool_calls
    assert resp.tool_calls[0].tool_name == "lookup"
    assert resp.tool_calls[0].tool_input == {"city": "İstanbul"}
    assert resp.tool_calls[0].tool_output == {"temperature": 20}
    assert resp.token_usage.prompt_tokens == 3
    assert resp.token_usage.completion_tokens == 2
    assert resp.token_usage.total_tokens == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ('  JsOn: {"message": "İstanbul 🧪"}  ', {"message": "İstanbul 🧪"}),
        ("json: [1, false, null]", [1, False, None]),
        ('  JSON: {"unfinished":  ', '{"unfinished":'),
    ],
    ids=["unicode-object", "array", "invalid-json-fallback"],
)
async def test_scripted_agent_json_heuristic(prompt, expected):
    task = Task(id="t_json", name="JSON Script Task", prompt=prompt)
    context = AgentExecutionContext(task=task)

    resp = await ScriptedAgent().run(task, context)

    assert resp.output == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("expected_output", "expected"),
    [(0, 0), (False, False), ("", ""), ([], []), ({}, {}), (None, "OK")],
    ids=["zero", "false", "empty-string", "empty-list", "empty-dict", "unset"],
)
async def test_scripted_agent_default_preserves_falsy_output(expected_output, expected):
    task = Task(
        id="t_default",
        name="Default Script Task",
        prompt="No scripted heuristic",
        expected_output=expected_output,
    )
    context = AgentExecutionContext(task=task)

    resp = await ScriptedAgent().run(task, context)

    assert resp.output == expected
    assert type(resp.output) is type(expected)


def test_adapter_registry():
    assert "mock" in list_adapters()
    assert "scripted" in list_adapters()
    agent = get_adapter("mock")
    assert isinstance(agent, MockAgent)
