"""Unit tests for agent adapters and execution context."""

import pytest
from agentbench.adapters.base import AgentExecutionContext
from agentbench.adapters.mock import MockAgent
from agentbench.adapters.scripted import ScriptedAgent
from agentbench.adapters.registry import get_adapter, list_adapters, register_adapter
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
                {"name": "web_search", "input": {"query": "python"}, "output": {"results": ["python.org"]}}
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


def test_adapter_registry():
    assert "mock" in list_adapters()
    assert "scripted" in list_adapters()
    agent = get_adapter("mock")
    assert isinstance(agent, MockAgent)
