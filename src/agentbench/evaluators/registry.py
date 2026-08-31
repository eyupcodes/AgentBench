"""Evaluator registry and factory."""

from typing import Dict, List, Type
from agentbench.evaluators.base import BaseEvaluator
from agentbench.evaluators.deterministic import (
    ContainsEvaluator,
    ExactMatchEvaluator,
    JSONSchemaEvaluator,
    NumericToleranceEvaluator,
    RegexEvaluator,
)
from agentbench.evaluators.tool_call import (
    ToolArgumentEvaluator,
    ToolCallCountEvaluator,
    ToolCallSequenceEvaluator,
)
from agentbench.evaluators.custom import CustomEvaluator
from agentbench.models.task import EvaluatorConfig, Task


_EVALUATOR_REGISTRY: Dict[str, Type[BaseEvaluator]] = {
    "exact_match": ExactMatchEvaluator,
    "contains": ContainsEvaluator,
    "regex": RegexEvaluator,
    "json_schema": JSONSchemaEvaluator,
    "numeric_tolerance": NumericToleranceEvaluator,
    "tool_call_count": ToolCallCountEvaluator,
    "tool_call_sequence": ToolCallSequenceEvaluator,
    "tool_argument": ToolArgumentEvaluator,
    "custom": CustomEvaluator,
}


def register_evaluator(name: str, evaluator_cls: Type[BaseEvaluator]) -> None:
    """Register a custom evaluator class."""
    _EVALUATOR_REGISTRY[name.lower()] = evaluator_cls


def get_evaluator(config: EvaluatorConfig) -> BaseEvaluator:
    """Instantiate an evaluator from configuration."""
    eval_type = config.type.lower()
    if eval_type in _EVALUATOR_REGISTRY:
        cls = _EVALUATOR_REGISTRY[eval_type]
        return cls(config=config)

    # Support dotted class path
    if "." in config.type:
        import importlib
        module_path, class_name = config.type.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        if not issubclass(cls, BaseEvaluator):
            raise TypeError(f"Class {cls} must inherit from BaseEvaluator")
        return cls(config=config)

    available = ", ".join(list_evaluators())
    raise KeyError(f"Unknown evaluator type: '{config.type}'. Available types: {available}")


def list_evaluators() -> List[str]:
    """List available registered evaluator types."""
    return sorted(list(_EVALUATOR_REGISTRY.keys()))


def build_evaluators_for_task(task: Task) -> List[BaseEvaluator]:
    """Construct all configured evaluators for a task.

    If task has no explicit evaluators but has expected_output, defaults to ExactMatchEvaluator.
    """
    evaluators = [get_evaluator(cfg) for cfg in task.evaluators]

    if not evaluators and task.expected_output is not None:
        evaluators.append(
            ExactMatchEvaluator(
                config=EvaluatorConfig(
                    type="exact_match",
                    expected=task.expected_output,
                    description="Default exact match against task expected_output",
                )
            )
        )

    return evaluators
