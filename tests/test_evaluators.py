"""Unit tests for deterministic and tool-call evaluators."""

from agentbench.evaluators.base import EvaluationContext
from agentbench.evaluators.custom import CustomEvaluator
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
from agentbench.models.event import ToolCallEvent
from agentbench.models.task import EvaluatorConfig, Task


def _make_context(output, tool_calls=None, expected=None):
    task = Task(id="test", name="Test", prompt="prompt", expected_output=expected)
    return EvaluationContext(
        task=task,
        output=output,
        tool_calls=tool_calls or [],
    )


def test_exact_match_evaluator():
    evaluator = ExactMatchEvaluator(
        EvaluatorConfig(type="exact_match", expected="hello world")
    )

    # Success
    res1 = evaluator.evaluate(_make_context("hello world"))
    assert res1.passed is True
    assert res1.score == 1.0

    # Whitespace strip
    res2 = evaluator.evaluate(_make_context("  hello world \n"))
    assert res2.passed is True

    # Failure
    res3 = evaluator.evaluate(_make_context("different"))
    assert res3.passed is False
    assert res3.score == 0.0


def test_contains_evaluator():
    evaluator = ContainsEvaluator(
        EvaluatorConfig(type="contains", expected=["Paris", "France"])
    )

    res1 = evaluator.evaluate(_make_context("The capital of France is Paris."))
    assert res1.passed is True

    res2 = evaluator.evaluate(_make_context("The capital of Spain is Madrid."))
    assert res2.passed is False
    assert res2.score == 0.0

    # Partial match
    res3 = evaluator.evaluate(_make_context("France is in Europe."))
    assert res3.passed is False
    assert res3.score == 0.5


def test_regex_evaluator():
    evaluator = RegexEvaluator(
        EvaluatorConfig(type="regex", options={"pattern": r"\b\d{3}-\d{4}\b"})
    )
    res1 = evaluator.evaluate(_make_context("Phone: 555-1234"))
    assert res1.passed is True

    res2 = evaluator.evaluate(_make_context("No phone here"))
    assert res2.passed is False


def test_json_schema_evaluator():
    evaluator = JSONSchemaEvaluator(
        EvaluatorConfig(
            type="json_schema",
            expected={"name": "Alice", "age": 30},
            options={"required_keys": ["name", "age"]},
        )
    )

    res1 = evaluator.evaluate(
        _make_context('{"name": "Alice", "age": 30, "extra": true}')
    )
    assert res1.passed is True

    res2 = evaluator.evaluate(_make_context('{"name": "Alice", "age": 35}'))
    assert res2.passed is False
    assert "Value mismatches" in res2.reason

    res3 = evaluator.evaluate(_make_context("invalid json"))
    assert res3.passed is False


def test_numeric_tolerance_evaluator():
    evaluator = NumericToleranceEvaluator(
        EvaluatorConfig(
            type="numeric_tolerance", expected=3.14159, options={"tolerance": 0.001}
        )
    )
    assert evaluator.evaluate(_make_context(3.1419)).passed is True
    assert evaluator.evaluate(_make_context(3.1500)).passed is False


def test_tool_call_evaluators():
    tools = [
        ToolCallEvent(tool_name="search", tool_input={"query": "weather"}),
        ToolCallEvent(tool_name="calculator", tool_input={"expr": "10+5"}),
    ]

    # Count evaluator
    cnt_eval = ToolCallCountEvaluator(
        EvaluatorConfig(type="tool_call_count", options={"exact_calls": 2})
    )
    assert cnt_eval.evaluate(_make_context("done", tool_calls=tools)).passed is True

    # Sequence evaluator
    seq_eval = ToolCallSequenceEvaluator(
        EvaluatorConfig(
            type="tool_call_sequence", options={"sequence": ["search", "calculator"]}
        )
    )
    assert seq_eval.evaluate(_make_context("done", tool_calls=tools)).passed is True

    # Argument evaluator
    arg_eval = ToolArgumentEvaluator(
        EvaluatorConfig(
            type="tool_argument",
            options={"tool_name": "search", "expected_args": {"query": "weather"}},
        )
    )
    assert arg_eval.evaluate(_make_context("done", tool_calls=tools)).passed is True


def test_custom_evaluator():
    def my_eval_fn(ctx):
        return len(str(ctx.output)) > 5

    custom_eval = CustomEvaluator(fn=my_eval_fn)
    assert custom_eval.evaluate(_make_context("123456")).passed is True
    assert custom_eval.evaluate(_make_context("123")).passed is False


def _custom_from_path(path):
    return CustomEvaluator(EvaluatorConfig(type="custom", options={"function": path}))


def test_custom_evaluator_import_path_resolves():
    result = _custom_from_path("builtins.bool").evaluate(_make_context("x"))
    assert result.passed is True


def test_custom_evaluator_missing_module_fails_cleanly():
    result = _custom_from_path("no_such_module_xyz.check").evaluate(_make_context("x"))
    assert result.passed is False
    assert result.score == 0.0
    assert "no_such_module_xyz.check" in result.reason


def test_custom_evaluator_missing_attribute_fails_cleanly():
    result = _custom_from_path("os.path.no_such_function").evaluate(_make_context("x"))
    assert result.passed is False
    assert "Cannot load custom function 'os.path.no_such_function'" in result.reason


def test_custom_evaluator_non_callable_target_fails_cleanly():
    result = _custom_from_path("os.sep").evaluate(_make_context("x"))
    assert result.passed is False
    assert "not callable" in result.reason


_TOOLS = [
    ToolCallEvent(tool_name="search", tool_input={"query": "weather"}),
    ToolCallEvent(tool_name="calculator", tool_input={"expr": "10+5"}),
]


def test_tool_call_count_reports_each_violated_bound():
    config = EvaluatorConfig(
        type="tool_call_count", options={"min_calls": 3, "max_calls": 1}
    )
    res = ToolCallCountEvaluator(config).evaluate(
        _make_context("done", tool_calls=_TOOLS)
    )
    assert res.passed is False
    assert res.score == 0.0
    assert "at least 3" in res.reason
    assert "at most 1" in res.reason


def test_tool_call_count_filters_by_tool_name():
    config = EvaluatorConfig(
        type="tool_call_count", options={"tool_name": "search", "exact_calls": 2}
    )
    res = ToolCallCountEvaluator(config).evaluate(
        _make_context("done", tool_calls=_TOOLS)
    )
    assert res.passed is False
    assert res.actual == {"count": 1, "target": "tool 'search'"}
    assert "exactly 2" in res.reason


def test_tool_call_sequence_out_of_order_fails():
    config = EvaluatorConfig(
        type="tool_call_sequence", options={"sequence": ["calculator", "search"]}
    )
    res = ToolCallSequenceEvaluator(config).evaluate(
        _make_context("done", tool_calls=_TOOLS)
    )
    assert res.passed is False
    assert res.actual == ["search", "calculator"]


def test_tool_call_sequence_strict_requires_exact_match():
    config = EvaluatorConfig(
        type="tool_call_sequence", options={"sequence": ["search"], "strict": True}
    )
    res = ToolCallSequenceEvaluator(config).evaluate(
        _make_context("done", tool_calls=_TOOLS)
    )
    assert res.passed is False
    assert "Expected sequence" in res.reason


def test_tool_argument_mismatch_lists_actual_inputs():
    config = EvaluatorConfig(
        type="tool_argument",
        options={"tool_name": "search", "expected_args": {"query": "news"}},
    )
    res = ToolArgumentEvaluator(config).evaluate(
        _make_context("done", tool_calls=_TOOLS)
    )
    assert res.passed is False
    assert res.actual == [{"query": "weather"}]


def test_tool_argument_without_tool_name_matches_any_call():
    config = EvaluatorConfig(
        type="tool_argument", options={"expected_args": {"expr": "10+5"}}
    )
    res = ToolArgumentEvaluator(config).evaluate(
        _make_context("done", tool_calls=_TOOLS)
    )
    assert res.passed is True
