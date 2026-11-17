"""Generic HTTP / OpenAI-compatible LLM agent adapter."""

import json
import os
import urllib.error
import urllib.request
from typing import Any

from agentbench.adapters.base import AgentExecutionContext, AgentResponse, BaseAgent
from agentbench.models.task import Task


def _token_count(usage: dict[str, Any], key: str) -> int:
    """Return a usage counter, or 0 when it is missing, null or not a count."""
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _message_text(content: Any) -> str:
    """Return message text; typed parts ``[{"type": "text", "text": ...}]`` are joined."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part["text"]
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    return ""


def _error_detail(resp_data: dict[str, Any]) -> str | None:
    """The server's error text when a reply carries an ``error`` instead of choices."""
    error = resp_data.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error)
    if isinstance(error, str) and error:
        return error
    return None


class GenericLLMAgent(BaseAgent):
    """Generic HTTP LLM adapter that speaks OpenAI-compatible chat completion endpoints.

    API key and base URL can be passed in config or loaded from environment variables.
    """

    def __init__(
        self,
        name: str = "GenericLLMAgent",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, config=config)
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        resolved_base_url: str = (
            base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        )
        self.base_url = resolved_base_url.rstrip("/")
        self.temperature = temperature

    async def run(self, task: Task, context: AgentExecutionContext) -> AgentResponse:
        if not self.api_key:
            raise ValueError(
                f"Missing API key for {self.name}. Please set OPENAI_API_KEY environment variable."
            )

        messages = []
        if task.system_prompt:
            messages.append({"role": "system", "content": task.system_prompt})
        messages.append({"role": "user", "content": task.prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        # Format tools if provided in task
        if task.tools:
            tools_spec = []
            for tool in task.tools:
                props = {
                    k: {"type": v.type, "description": v.description}
                    for k, v in tool.parameters.items()
                }
                required = [k for k, v in tool.parameters.items() if v.required]
                tools_spec.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                "type": "object",
                                "properties": props,
                                "required": required,
                            },
                        },
                    }
                )
            payload["tools"] = tools_spec

        context.record_thought(
            f"Sending request to {self.base_url}/chat/completions (model={self.model})"
        )

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=task.timeout_seconds) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"HTTP Error {e.code}: {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to query LLM endpoint: {e}") from e

        if not isinstance(resp_data, dict):
            raise RuntimeError(
                "Unexpected response from LLM endpoint: expected a JSON object, "
                f"got {type(resp_data).__name__}"
            )

        # Extract usage
        # Servers may send explicit nulls or odd types, so only trust real counts.
        usage_info = resp_data.get("usage")
        if not isinstance(usage_info, dict):
            usage_info = {}
        context.record_token_usage(
            prompt_tokens=_token_count(usage_info, "prompt_tokens"),
            completion_tokens=_token_count(usage_info, "completion_tokens"),
        )

        # Extract choice and tool calls
        choices = resp_data.get("choices") or []
        if not isinstance(choices, list):
            raise RuntimeError(
                "Unexpected response from LLM endpoint: 'choices' must be a list, "
                f"got {type(choices).__name__}"
            )
        if not choices:
            detail = _error_detail(resp_data)
            if detail:
                raise RuntimeError(f"LLM endpoint returned an error: {detail}")
            return AgentResponse(output="", token_usage=context.token_usage)

        if not isinstance(choices[0], dict):
            raise RuntimeError(
                "Unexpected response from LLM endpoint: a choice must be an object, "
                f"got {type(choices[0]).__name__}"
            )
        choice_msg = choices[0].get("message") or {}
        if not isinstance(choice_msg, dict):
            raise RuntimeError(
                "Unexpected response from LLM endpoint: 'message' must be an object, "
                f"got {type(choice_msg).__name__}"
            )
        content = _message_text(choice_msg.get("content"))

        # Check for tool calls returned by LLM
        tool_calls_raw = choice_msg.get("tool_calls") or []
        if not isinstance(tool_calls_raw, list):
            raise RuntimeError(
                "Unexpected response from LLM endpoint: 'tool_calls' must be a list, "
                f"got {type(tool_calls_raw).__name__}"
            )
        for raw_tc in tool_calls_raw:
            fn = raw_tc.get("function") if isinstance(raw_tc, dict) else None
            if not isinstance(fn, dict):
                continue
            fn_name = fn.get("name") or ""
            raw_args = fn.get("arguments") or "{}"
            if isinstance(raw_args, dict):
                fn_args: Any = raw_args
            else:
                try:
                    fn_args = json.loads(raw_args)
                except Exception:
                    fn_args = None
            if not isinstance(fn_args, dict):
                # Tool input must be an object; keep what the model sent.
                fn_args = {"raw": raw_args}

            # If task tool had mock response, attach it
            matched_mock = next(
                (t.mock_response for t in task.tools if t.name == fn_name), None
            )
            context.record_tool_call(
                tool_name=fn_name,
                tool_input=fn_args,
                tool_output=matched_mock or {"result": "success"},
            )

        return AgentResponse(
            output=content if content else {"tool_calls": len(context.tool_calls)},
            tool_calls=list(context.tool_calls),
            token_usage=context.token_usage,
        )
