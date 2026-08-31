"""Hardening tests for error paths, edge cases, HTTP adapter mocking, and loader exceptions."""

import io
import json
from pathlib import Path
import tempfile
import urllib.error
from unittest.mock import MagicMock, patch
import pytest

from agentbench.adapters.base import AgentExecutionContext
from agentbench.adapters.http_llm import GenericLLMAgent
from agentbench.adapters.registry import get_adapter
from agentbench.evaluators.custom import CustomEvaluator
from agentbench.evaluators.deterministic import RegexEvaluator, NumericToleranceEvaluator
from agentbench.evaluators.registry import get_evaluator
from agentbench.evaluators.tool_call import ToolArgumentEvaluator, ToolCallCountEvaluator
from agentbench.loader import load_suite, save_suite
from agentbench.models.task import EvaluatorConfig, Task, TaskSuite
from agentbench.models.result import RunStatus
from agentbench.runner.context import RunnerOptions
from agentbench.runner.runner import BenchmarkRunner


@pytest.mark.asyncio
async def test_http_llm_missing_api_key():
    agent = GenericLLMAgent(api_key="")
    task = Task(id="t1", name="Task 1", prompt="Hello")
    context = AgentExecutionContext(task=task)

    with pytest.raises(ValueError, match="Missing API key"):
        await agent.run(task, context)


@pytest.mark.asyncio
async def test_http_llm_mocked_success():
    fake_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Paris",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Paris"}'
                            }
                        }
                    ]
                }
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 5,
            "total_tokens": 20
        }
    }

    mock_resp_bytes = json.dumps(fake_response).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value = io.BytesIO(mock_resp_bytes)

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        agent = GenericLLMAgent(api_key="test-key")
        task = Task(id="t1", name="Task 1", prompt="What's the weather in Paris?")
        context = AgentExecutionContext(task=task)
        resp = await agent.run(task, context)

        assert resp.output == "Paris"
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].tool_name == "get_weather"
        assert resp.token_usage.total_tokens == 20


@pytest.mark.asyncio
async def test_http_llm_mocked_http_error():
    mock_error = urllib.error.HTTPError(
        url="https://api.openai.com/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"error": "Invalid API key"}'),
    )

    with patch("urllib.request.urlopen", side_effect=mock_error):
        agent = GenericLLMAgent(api_key="bad-key")
        task = Task(id="t1", name="Task 1", prompt="Hello")
        context = AgentExecutionContext(task=task)

        with pytest.raises(RuntimeError, match="HTTP Error 401"):
            await agent.run(task, context)


def test_loader_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_suite("non_existent_file.yaml")


def test_loader_invalid_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_file = Path(tmpdir) / "bad.yaml"
        with open(bad_file, "w") as f:
            f.write("- item1\n- item2\n")

        with pytest.raises(ValueError, match="Invalid suite file format"):
            load_suite(bad_file)


def test_evaluator_error_cases():
    # Regex bad pattern
    bad_regex = RegexEvaluator(EvaluatorConfig(type="regex", options={"pattern": "[unclosed"}))
    task = Task(id="t1", name="T", prompt="p")
    ctx = AgentExecutionContext(task=task)
    from agentbench.evaluators.base import EvaluationContext
    eval_ctx = EvaluationContext(task=task, output="test")
    res = bad_regex.evaluate(eval_ctx)
    assert res.passed is False
    assert "Invalid regular expression" in res.reason

    # Numeric tolerance non-number
    num_eval = NumericToleranceEvaluator(EvaluatorConfig(type="numeric_tolerance", expected=10))
    res_num = num_eval.evaluate(EvaluationContext(task=task, output="not-a-number"))
    assert res_num.passed is False


def test_adapter_registry_dotted_import():
    agent = get_adapter("agentbench.adapters.mock.MockAgent")
    assert agent.name == "MockAgent"

    with pytest.raises(KeyError, match="not found"):
        get_adapter("unknown_adapter_name_xyz")


def test_evaluator_registry_dotted_import():
    evaluator = get_evaluator(EvaluatorConfig(type="agentbench.evaluators.deterministic.ExactMatchEvaluator", expected="abc"))
    assert evaluator.config.type == "agentbench.evaluators.deterministic.ExactMatchEvaluator"

    with pytest.raises(KeyError, match="Unknown evaluator type"):
        get_evaluator(EvaluatorConfig(type="non_existent_evaluator_xyz"))
