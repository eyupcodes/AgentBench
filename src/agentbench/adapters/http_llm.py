"""Generic HTTP / OpenAI-compatible LLM agent adapter."""

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from agentbench.adapters.base import AgentExecutionContext, AgentResponse, BaseAgent
from agentbench.models.task import Task


class GenericLLMAgent(BaseAgent):
    """Generic HTTP LLM adapter that speaks OpenAI-compatible chat completion endpoints.

    API key and base URL can be passed in config or loaded from environment variables.
    """

    def __init__(
        self,
        name: str = "GenericLLMAgent",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(name=name, config=config)
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
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
                props = {k: {"type": v.type, "description": v.description} for k, v in tool.parameters.items()}
                required = [k for k, v in tool.parameters.items() if v.required]
                tools_spec.append({
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
                })
            payload["tools"] = tools_spec

        context.record_thought(f"Sending request to {self.base_url}/chat/completions (model={self.model})")

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

        # Extract usage
        usage_info = resp_data.get("usage", {})
        prompt_tokens = usage_info.get("prompt_tokens", 0)
        completion_tokens = usage_info.get("completion_tokens", 0)
        context.record_token_usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

        # Extract choice and tool calls
        choices = resp_data.get("choices", [])
        if not choices:
            return AgentResponse(output="", token_usage=context.token_usage)

        choice_msg = choices[0].get("message", {})
        content = choice_msg.get("content", "")

        # Check for tool calls returned by LLM
        tool_calls_raw = choice_msg.get("tool_calls", [])
        for raw_tc in tool_calls_raw:
            fn = raw_tc.get("function", {})
            fn_name = fn.get("name", "")
            fn_args = {}
            try:
                fn_args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                fn_args = {"raw": fn.get("arguments", "")}

            # If task tool had mock response, attach it
            matched_mock = next((t.mock_response for t in task.tools if t.name == fn_name), None)
            context.record_tool_call(
                tool_name=fn_name,
                tool_input=fn_args,
                tool_output=matched_mock or {"result": "success"},
            )

        return AgentResponse(
            output=content if content else {"tool_calls": len(tool_calls_raw)},
            tool_calls=list(context.tool_calls),
            token_usage=context.token_usage,
        )
