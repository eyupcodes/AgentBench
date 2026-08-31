"""Custom Python function evaluator hook."""

from typing import Any, Callable, Optional
from agentbench.evaluators.base import BaseEvaluator, EvaluationContext
from agentbench.models.result import EvaluationResult
from agentbench.models.task import EvaluatorConfig


class CustomEvaluator(BaseEvaluator):
    """Evaluates task execution using a custom user-defined Python function or callable."""

    def __init__(
        self,
        config: Optional[EvaluatorConfig] = None,
        fn: Optional[Callable[[EvaluationContext], Any]] = None,
    ) -> None:
        super().__init__(config=config)
        self.fn = fn

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        fn_to_call = self.fn
        if fn_to_call is None and self.config and "function" in self.config.options:
            fn_path = self.config.options["function"]
            if isinstance(fn_path, str) and "." in fn_path:
                import importlib
                module_path, fn_name = fn_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                fn_to_call = getattr(module, fn_name)

        if fn_to_call is None:
            return EvaluationResult(
                evaluator_type="custom",
                passed=False,
                score=0.0,
                reason="No custom function callable or import path provided",
            )

        try:
            res = fn_to_call(context)
            if isinstance(res, EvaluationResult):
                return res
            if isinstance(res, bool):
                return EvaluationResult(
                    evaluator_type="custom",
                    passed=res,
                    score=1.0 if res else 0.0,
                    actual=context.output,
                    reason="Custom function passed" if res else "Custom function returned False",
                )
            if isinstance(res, (int, float)):
                passed = res >= 1.0
                return EvaluationResult(
                    evaluator_type="custom",
                    passed=passed,
                    score=float(min(1.0, max(0.0, res))),
                    actual=context.output,
                    reason=f"Custom function returned score {res}",
                )
            return EvaluationResult(
                evaluator_type="custom",
                passed=bool(res),
                score=1.0 if res else 0.0,
                actual=res,
                reason=f"Custom function completed with value: {res}",
            )
        except Exception as e:
            return EvaluationResult(
                evaluator_type="custom",
                passed=False,
                score=0.0,
                reason=f"Error executing custom evaluator function: {e}",
            )
