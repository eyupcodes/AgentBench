"""Hardening tests for error paths, edge cases, HTTP adapter mocking, and loader exceptions."""

import io
import json
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentbench.adapters.base import AgentExecutionContext
from agentbench.adapters.http_llm import GenericLLMAgent
from agentbench.adapters.registry import get_adapter
from agentbench.evaluators.deterministic import (
    NumericToleranceEvaluator,
    RegexEvaluator,
)
from agentbench.evaluators.registry import get_evaluator
from agentbench.loader import load_suite
from agentbench.models.task import EvaluatorConfig, Task


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
                                "arguments": '{"city": "Paris"}',
                            }
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20},
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
    bad_regex = RegexEvaluator(
        EvaluatorConfig(type="regex", options={"pattern": "[unclosed"})
    )
    task = Task(id="t1", name="T", prompt="p")
    from agentbench.evaluators.base import EvaluationContext

    eval_ctx = EvaluationContext(task=task, output="test")
    res = bad_regex.evaluate(eval_ctx)
    assert res.passed is False
    assert "Invalid regular expression" in res.reason

    # Numeric tolerance non-number
    num_eval = NumericToleranceEvaluator(
        EvaluatorConfig(type="numeric_tolerance", expected=10)
    )
    res_num = num_eval.evaluate(EvaluationContext(task=task, output="not-a-number"))
    assert res_num.passed is False


def test_adapter_registry_dotted_import():
    agent = get_adapter("agentbench.adapters.mock.MockAgent")
    assert agent.name == "MockAgent"

    with pytest.raises(KeyError, match="not found"):
        get_adapter("unknown_adapter_name_xyz")


def test_evaluator_registry_dotted_import():
    evaluator = get_evaluator(
        EvaluatorConfig(
            type="agentbench.evaluators.deterministic.ExactMatchEvaluator",
            expected="abc",
        )
    )
    assert (
        evaluator.config.type
        == "agentbench.evaluators.deterministic.ExactMatchEvaluator"
    )

    with pytest.raises(KeyError, match="Unknown evaluator type"):
        get_evaluator(EvaluatorConfig(type="non_existent_evaluator_xyz"))


async def _run_http_llm(reply):
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value = io.BytesIO(json.dumps(reply).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        agent = GenericLLMAgent(api_key="test-key")
        task = Task(id="t1", name="Task 1", prompt="Hello")
        context = AgentExecutionContext(task=task)
        return await agent.run(task, context)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reply",
    [
        {"choices": [{"message": {"content": "hi", "tool_calls": None}}]},
        {"choices": [{"message": {"content": "hi"}}], "usage": None},
        {"choices": [{"message": None}]},
        {"choices": None},
        {
            "choices": [{"message": {"content": "hi"}}],
            "usage": {"prompt_tokens": None, "completion_tokens": None},
        },
    ],
)
async def test_http_llm_tolerates_null_fields(reply):
    resp = await _run_http_llm(reply)

    assert resp.token_usage.total_tokens == 0
    assert resp.tool_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("arguments", ["[1, 2]", "42", "not json"])
async def test_http_llm_keeps_non_object_tool_arguments_raw(arguments):
    reply = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {"function": {"name": "lookup", "arguments": arguments}}
                    ],
                }
            }
        ]
    }

    resp = await _run_http_llm(reply)

    assert resp.output == {"tool_calls": 1}
    assert resp.tool_calls[0].tool_name == "lookup"
    assert resp.tool_calls[0].tool_input == {"raw": arguments}


@pytest.mark.asyncio
async def test_http_llm_missing_tool_arguments_default_to_empty_object():
    reply = {
        "choices": [
            {
                "message": {
                    "tool_calls": [{"function": {"name": "ping", "arguments": None}}]
                }
            }
        ]
    }

    resp = await _run_http_llm(reply)

    assert resp.tool_calls[0].tool_input == {}


async def _capture_http_llm_request(task):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["req"] = req
        captured["timeout"] = timeout
        body = {"choices": [{"message": {"content": "ok"}}]}
        response = MagicMock()
        response.__enter__.return_value = io.BytesIO(json.dumps(body).encode("utf-8"))
        return response

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        agent = GenericLLMAgent(
            api_key="test-key", base_url="https://llm.example/v1/", model="m1"
        )
        await agent.run(task, AgentExecutionContext(task=task))
    return captured


@pytest.mark.asyncio
async def test_http_llm_request_includes_system_prompt_and_auth():
    task = Task(
        id="t1",
        name="Task 1",
        prompt="Hello",
        system_prompt="Be brief.",
        timeout_seconds=7,
    )

    captured = await _capture_http_llm_request(task)

    req = captured["req"]
    payload = json.loads(req.data.decode("utf-8"))
    assert req.full_url == "https://llm.example/v1/chat/completions"
    assert req.get_header("Authorization") == "Bearer test-key"
    assert captured["timeout"] == 7
    assert payload["model"] == "m1"
    assert payload["messages"] == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Hello"},
    ]
    assert "tools" not in payload


@pytest.mark.asyncio
async def test_http_llm_request_describes_task_tools():
    task = Task.model_validate(
        {
            "id": "t1",
            "name": "Task 1",
            "prompt": "Weather?",
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Look up the weather",
                    "parameters": {
                        "city": {
                            "type": "string",
                            "description": "City name",
                            "required": True,
                        },
                        "days": {"type": "integer"},
                    },
                }
            ],
        }
    )

    captured = await _capture_http_llm_request(task)

    payload = json.loads(captured["req"].data.decode("utf-8"))
    assert payload["messages"] == [{"role": "user", "content": "Weather?"}]
    assert payload["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Look up the weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"},
                        "days": {"type": "integer", "description": ""},
                    },
                    "required": ["city"],
                },
            },
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", [[], ["x"], "text", 42, None])
async def test_http_llm_rejects_non_object_json_reply(reply):
    with pytest.raises(RuntimeError, match="expected a JSON object"):
        await _run_http_llm(reply)


def test_http_llm_base_url_resolution(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert GenericLLMAgent().base_url == "https://api.openai.com/v1"

    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example/v1/")
    assert GenericLLMAgent().base_url == "https://env.example/v1"
    assert (
        GenericLLMAgent(base_url="https://arg.example/v1/").base_url
        == "https://arg.example/v1"
    )

    # An empty variable falls back to the default instead of an empty URL.
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    assert GenericLLMAgent().base_url == "https://api.openai.com/v1"
