"""Deterministic evaluators for string matching, regex, numbers, and structured data."""

import json
import re
from typing import Any, Optional
from agentbench.evaluators.base import BaseEvaluator, EvaluationContext
from agentbench.models.result import EvaluationResult
from agentbench.models.task import EvaluatorConfig


class ExactMatchEvaluator(BaseEvaluator):
    """Evaluates whether the agent output strictly matches the expected value."""

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        expected = self.config.expected if self.config.expected is not None else context.task.expected_output
        actual = context.output

        strip_ws = self.config.options.get("strip", True)
        case_sensitive = self.config.options.get("case_sensitive", True)

        if expected is None:
            return EvaluationResult(
                evaluator_type="exact_match",
                passed=False,
                score=0.0,
                expected=expected,
                actual=actual,
                reason="No expected output specified for exact match",
            )

        exp_val = expected
        act_val = actual

        if isinstance(exp_val, str) and isinstance(act_val, str):
            if strip_ws:
                exp_val = exp_val.strip()
                act_val = act_val.strip()
            if not case_sensitive:
                exp_val = exp_val.lower()
                act_val = act_val.lower()

        passed = (exp_val == act_val)
        return EvaluationResult(
            evaluator_type="exact_match",
            passed=passed,
            score=1.0 if passed else 0.0,
            expected=expected,
            actual=actual,
            reason="Outputs match exactly" if passed else f"Expected '{expected}', got '{actual}'",
        )


class ContainsEvaluator(BaseEvaluator):
    """Evaluates whether the agent output contains required substring(s) or keywords."""

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        expected = self.config.expected if self.config.expected is not None else context.task.expected_output
        actual = str(context.output or "")
        case_sensitive = self.config.options.get("case_sensitive", False)

        if not case_sensitive:
            actual = actual.lower()

        # Expected can be a single string or a list of required substrings
        targets = [expected] if isinstance(expected, str) else (list(expected) if isinstance(expected, (list, tuple)) else [str(expected)])
        missing = []

        for target in targets:
            tgt_str = str(target)
            check_tgt = tgt_str if case_sensitive else tgt_str.lower()
            if check_tgt not in actual:
                missing.append(tgt_str)

        passed = len(missing) == 0
        total_targets = len(targets)
        score = round((total_targets - len(missing)) / total_targets, 2) if total_targets > 0 else 0.0

        return EvaluationResult(
            evaluator_type="contains",
            passed=passed,
            score=score,
            expected=expected,
            actual=context.output,
            reason="All target substrings found" if passed else f"Missing expected substrings: {missing}",
        )


class RegexEvaluator(BaseEvaluator):
    """Evaluates whether the agent output matches a regular expression pattern."""

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        pattern_str = self.config.options.get("pattern") or str(self.config.expected or "")
        actual = str(context.output or "")

        flags = 0
        if not self.config.options.get("case_sensitive", True):
            flags |= re.IGNORECASE
        if self.config.options.get("dotall", False):
            flags |= re.DOTALL

        try:
            pattern = re.compile(pattern_str, flags)
            match = pattern.search(actual)
            passed = match is not None
            return EvaluationResult(
                evaluator_type="regex",
                passed=passed,
                score=1.0 if passed else 0.0,
                expected=pattern_str,
                actual=context.output,
                reason="Pattern matched" if passed else f"Pattern '{pattern_str}' did not match output",
            )
        except re.error as e:
            return EvaluationResult(
                evaluator_type="regex",
                passed=False,
                score=0.0,
                expected=pattern_str,
                actual=context.output,
                reason=f"Invalid regular expression: {e}",
            )


class JSONSchemaEvaluator(BaseEvaluator):
    """Evaluates whether the agent output parses as JSON and conforms to expected keys/structure."""

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        actual = context.output
        if isinstance(actual, str):
            try:
                actual = json.loads(actual)
            except Exception as e:
                return EvaluationResult(
                    evaluator_type="json_schema",
                    passed=False,
                    score=0.0,
                    expected=self.config.expected,
                    actual=context.output,
                    reason=f"Output is not valid JSON: {e}",
                )

        if not isinstance(actual, dict):
            return EvaluationResult(
                evaluator_type="json_schema",
                passed=False,
                score=0.0,
                expected=self.config.expected,
                actual=actual,
                reason=f"Expected JSON object (dict), received {type(actual).__name__}",
            )

        required_keys = self.config.options.get("required_keys", [])
        if not required_keys and isinstance(self.config.expected, dict):
            required_keys = list(self.config.expected.keys())

        missing_keys = [k for k in required_keys if k not in actual]

        # Check expected field values if provided in expected dict
        mismatched_values = []
        if isinstance(self.config.expected, dict):
            for k, exp_v in self.config.expected.items():
                if k in actual and actual[k] != exp_v:
                    mismatched_values.append(f"{k}: expected {exp_v}, got {actual[k]}")

        passed = (len(missing_keys) == 0 and len(mismatched_values) == 0)
        reasons = []
        if missing_keys:
            reasons.append(f"Missing required keys: {missing_keys}")
        if mismatched_values:
            reasons.append(f"Value mismatches: {'; '.join(mismatched_values)}")

        return EvaluationResult(
            evaluator_type="json_schema",
            passed=passed,
            score=1.0 if passed else 0.0,
            expected=self.config.expected or {"required_keys": required_keys},
            actual=actual,
            reason="JSON structure and values valid" if passed else "; ".join(reasons),
        )


class NumericToleranceEvaluator(BaseEvaluator):
    """Evaluates whether numeric output is within an acceptable absolute/relative tolerance."""

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        expected = self.config.expected if self.config.expected is not None else context.task.expected_output
        actual = context.output
        tolerance = float(self.config.options.get("tolerance", 1e-5))

        try:
            exp_num = float(expected)
            act_num = float(actual)
            diff = abs(exp_num - act_num)
            passed = diff <= tolerance
            return EvaluationResult(
                evaluator_type="numeric_tolerance",
                passed=passed,
                score=1.0 if passed else 0.0,
                expected=exp_num,
                actual=act_num,
                reason=f"Diff {diff:.6f} <= tolerance {tolerance}" if passed else f"Diff {diff:.6f} > tolerance {tolerance}",
            )
        except (ValueError, TypeError) as e:
            return EvaluationResult(
                evaluator_type="numeric_tolerance",
                passed=False,
                score=0.0,
                expected=expected,
                actual=actual,
                reason=f"Could not convert values to numeric floats: {e}",
            )
