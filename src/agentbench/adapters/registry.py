"""Registry for agent adapters."""

from typing import Any, Dict, List, Type
from agentbench.adapters.base import BaseAgent
from agentbench.adapters.mock import MockAgent
from agentbench.adapters.scripted import ScriptedAgent
from agentbench.adapters.http_llm import GenericLLMAgent


_ADAPTER_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "mock": MockAgent,
    "mock_agent": MockAgent,
    "scripted": ScriptedAgent,
    "scripted_agent": ScriptedAgent,
    "generic_llm": GenericLLMAgent,
    "llm": GenericLLMAgent,
    "openai": GenericLLMAgent,
}


def register_adapter(name: str, adapter_cls: Type[BaseAgent]) -> None:
    """Register a new adapter class under the given name."""
    _ADAPTER_REGISTRY[name.lower()] = adapter_cls


def get_adapter(name_or_alias: str, **kwargs: Any) -> BaseAgent:
    """Instantiate an adapter by name or dotted python class path."""
    key = name_or_alias.lower()
    if key in _ADAPTER_REGISTRY:
        cls = _ADAPTER_REGISTRY[key]
        return cls(**kwargs)

    # Support dotted python import: "my_module.MyCustomAgent"
    if "." in name_or_alias:
        import importlib
        module_path, class_name = name_or_alias.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        if not issubclass(cls, BaseAgent):
            raise TypeError(f"Class {cls} must inherit from BaseAgent")
        return cls(**kwargs)

    available = ", ".join(list_adapters())
    raise KeyError(f"Adapter '{name_or_alias}' not found. Available registered adapters: {available}")


def list_adapters() -> List[str]:
    """List unique registered adapter names."""
    return sorted(list(set(_ADAPTER_REGISTRY.keys())))
