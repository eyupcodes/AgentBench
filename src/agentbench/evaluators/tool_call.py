"""Evaluators for checking agent tool usage, call frequency, sequence, and arguments."""

from typing import Any, Dict, List
from agentbench.evaluators.base import BaseEvaluator, EvaluationContext
from agentbench.models.result import EvaluationResult


class ToolCallCountEvaluator(BaseEvaluator):
    """Evaluates whether the agent made the expected number of tool calls."""

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        min_calls = self.config.options.get("min_calls")
        max_calls = self.config.options.get("max_calls")
        exact_calls = self.config.options.get("exact_calls")
        specific_tool = self.config.options.get("tool_name")

        if specific_tool:
            actual_count = sum(1 for tc in context.tool_calls if tc.tool_name == specific_tool)
        else:
            actual_count = len(context.tool_calls)

        passed = True
        reasons = []

        if exact_calls is not None and actual_count != exact_calls:
            passed = False
            reasons.append(f"Expected exactly {exact_calls} calls, got {actual_count}")
        if min_calls is not None and actual_count < min_calls:
            passed = False
            reasons.append(f"Expected at least {min_calls} calls, got {actual_count}")
        if max_calls is not None and actual_count > max_calls:
            passed = False
            reasons.append(f"Expected at most {max_calls} calls, got {actual_count}")

        target_desc = f"tool '{specific_tool}'" if specific_tool else "all tools"
        return EvaluationResult(
            evaluator_type="tool_call_count",
            passed=passed,
            score=1.0 if passed else 0.0,
            expected=self.config.options,
            actual={"count": actual_count, "target": target_desc},
            reason="Tool call count criteria met" if passed else "; ".join(reasons),
        )


class ToolCallSequenceEvaluator(BaseEvaluator):
    """Evaluates whether specific tools were invoked in an expected sequential order."""

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        expected_sequence: List[str] = self.config.options.get("sequence") or (
            list(self.config.expected) if isinstance(self.config.expected, list) else []
        )
        actual_sequence = [tc.tool_name for tc in context.tool_calls]
        strict = self.config.options.get("strict", False)

        if strict:
            passed = (actual_sequence == expected_sequence)
            reason = "Exact sequence matched" if passed else f"Expected sequence {expected_sequence}, got {actual_sequence}"
        else:
            # Subsequence match: expected tools appear in order within actual sequence
            it = iter(actual_sequence)
            passed = all(tool in it for tool in expected_sequence)
            reason = "Expected tool sequence contained in trace" if passed else f"Tools not called in order {expected_sequence} (actual: {actual_sequence})"

        return EvaluationResult(
            evaluator_type="tool_call_sequence",
            passed=passed,
            score=1.0 if passed else 0.0,
            expected=expected_sequence,
            actual=actual_sequence,
            reason=reason,
        )


class ToolArgumentEvaluator(BaseEvaluator):
    """Evaluates whether a specific tool was called with expected arguments."""

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        tool_name = self.config.options.get("tool_name")
        expected_args = self.config.options.get("expected_args", {})

        matching_calls = [tc for tc in context.tool_calls if tc.tool_name == tool_name] if tool_name else context.tool_calls

        if not matching_calls:
            return EvaluationResult(
                evaluator_type="tool_argument",
                passed=False,
                score=0.0,
                expected={"tool_name": tool_name, "args": expected_args},
                actual=None,
                reason=f"Tool '{tool_name}' was never called",
            )

        # Look for at least one call that satisfies all expected args
        for tc in matching_calls:
            all_match = True
            for k, v in expected_args.items():
                if k not in tc.tool_input or tc.tool_input[k] != v:
                    all_match = False
                    break
            if all_match:
                return EvaluationResult(
                    evaluator_type="tool_argument",
                    passed=True,
                    score=1.0,
                    expected=expected_args,
                    actual=tc.tool_input,
                    reason=f"Found matching call for tool '{tool_name}' with expected arguments",
                )

        return EvaluationResult(
            evaluator_type="tool_argument",
            passed=False,
            score=0.0,
            expected=expected_args,
            actual=[tc.tool_input for tc in matching_calls],
            reason=f"No call to '{tool_name}' matched expected arguments {expected_args}",
        )
