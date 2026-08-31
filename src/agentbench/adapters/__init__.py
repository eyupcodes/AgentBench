"""Agent adapters module."""

from agentbench.adapters.base import AgentExecutionContext, AgentResponse, BaseAgent
from agentbench.adapters.mock import MockAgent
from agentbench.adapters.scripted import ScriptedAgent
from agentbench.adapters.http_llm import GenericLLMAgent
from agentbench.adapters.registry import get_adapter, list_adapters, register_adapter

__all__ = [
    "BaseAgent",
    "AgentExecutionContext",
    "AgentResponse",
    "MockAgent",
    "ScriptedAgent",
    "GenericLLMAgent",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
