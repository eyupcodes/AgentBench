"""Tests for suite file formats, round trips, and invalid input."""

import json

import pytest
import yaml
from pydantic import ValidationError

from agentbench.loader import load_suite, save_suite
from agentbench.models.task import TaskSuite


@pytest.fixture
def suite_data():
    return {
        "name": "Multilingual suite 🌍",
        "version": "2.0",
        "description": "Unicode and nested configuration",
        "default_timeout_seconds": 12.5,
        "default_max_retries": 0,
        "metadata": {"language": "日本語"},
        "tasks": [
            {
                "id": "weather-01",
                "name": "Weather lookup",
                "prompt": "Fetch the weather for Zürich",
                "tools": [
                    {
                        "name": "get_weather",
                        "description": "Retrieve weather by city",
                        "parameters": {"city": {"type": "string", "required": True}},
                        "mock_response": {"city": "Zürich", "temperature": 8},
                    }
                ],
                "evaluators": [
                    {
                        "type": "tool_argument",
                        "options": {
                            "tool_name": "get_weather",
                            "expected_args": {"city": "Zürich"},
                        },
                    }
                ],
                "expected_output": {"city": "Zürich", "temperature": 8},
                "timeout_seconds": 5.5,
                "max_retries": 0,
                "metadata": {"tags": ["weather", "unicode"], "enabled": True},
            }
        ],
    }


@pytest.mark.parametrize(
    ("filename", "serialize"),
    [
        ("suite.yaml", yaml.safe_dump),
        ("suite.yml", yaml.safe_dump),
        ("suite.YAML", yaml.safe_dump),
        ("suite.json", json.dumps),
        ("suite.JSON", json.dumps),
        ("yaml_suite", yaml.safe_dump),
        ("json_suite", json.dumps),
        ("yaml_suite.txt", yaml.safe_dump),
        ("json_suite.txt", json.dumps),
    ],
)
def test_load_suite_supported_formats(tmp_path, suite_data, filename, serialize):
    path = tmp_path / filename
    path.write_text(serialize(suite_data), encoding="utf-8")

    assert load_suite(str(path)) == TaskSuite.model_validate(suite_data)


@pytest.mark.parametrize(
    ("filename", "serialize"),
    [("suite.yaml", yaml.safe_dump), ("suite.json", json.dumps), ("suite", json.dumps)],
)
def test_load_suite_accepts_utf8_bom(tmp_path, suite_data, filename, serialize):
    path = tmp_path / filename
    path.write_bytes(b"\xef\xbb\xbf" + serialize(suite_data).encode("utf-8"))

    assert load_suite(path) == TaskSuite.model_validate(suite_data)


@pytest.mark.parametrize("suffix", [".yaml", ".yml", ".YAML", ".json", ".JSON", ""])
def test_save_suite_round_trip(tmp_path, suite_data, suffix):
    suite = TaskSuite.model_validate(suite_data)
    path = tmp_path / "nested" / "output" / f"suite{suffix}"

    assert save_suite(suite, path) == path
    content = path.read_text(encoding="utf-8")
    assert "Zürich" in content
    assert "日本語" in content
    if suffix.lower() in (".yaml", ".yml"):
        saved_data = yaml.safe_load(content)
    else:
        saved_data = json.loads(content)
    assert saved_data == suite.model_dump(exclude_none=True)
    assert "description" not in saved_data["tasks"][0]
    assert load_suite(path) == suite


@pytest.mark.parametrize("content", ["", "null", "[]", '"not a suite"', "42"])
def test_load_suite_rejects_non_mapping_root(tmp_path, content):
    path = tmp_path / "invalid.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Root must be a dictionary"):
        load_suite(path)


@pytest.mark.parametrize(
    ("suffix", "content", "error"),
    [
        (".yaml", "tasks: [", yaml.YAMLError),
        (".json", '{"tasks": [', json.JSONDecodeError),
    ],
)
def test_load_suite_rejects_malformed_content(tmp_path, suffix, content, error):
    path = tmp_path / f"invalid{suffix}"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(error):
        load_suite(path)


def test_load_suite_validates_nested_tasks(tmp_path, suite_data):
    del suite_data["tasks"][0]["prompt"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(suite_data), encoding="utf-8")

    with pytest.raises(ValidationError) as exc_info:
        load_suite(path)

    assert exc_info.value.errors()[0]["loc"] == ("tasks", 0, "prompt")
    assert exc_info.value.errors()[0]["type"] == "missing"


def _write_yaml(tmp_path, text):
    path = tmp_path / "suite.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_tasks_inherit_suite_defaults(tmp_path):
    path = _write_yaml(
        tmp_path,
        "name: s\n"
        "default_timeout_seconds: 120\n"
        "default_max_retries: 3\n"
        "tasks:\n"
        "  - {id: a, name: A, prompt: p}\n",
    )

    task = load_suite(path).tasks[0]

    assert task.timeout_seconds == 120
    assert task.max_retries == 3


def test_explicit_task_values_beat_suite_defaults(tmp_path):
    path = _write_yaml(
        tmp_path,
        "name: s\n"
        "default_timeout_seconds: 120\n"
        "default_max_retries: 3\n"
        "tasks:\n"
        "  - {id: a, name: A, prompt: p, timeout_seconds: 5, max_retries: 1}\n"
        "  - {id: b, name: B, prompt: p, timeout_seconds: 30.0}\n",
    )

    first, second = load_suite(path).tasks

    assert (first.timeout_seconds, first.max_retries) == (5, 1)
    # An explicit value equal to the model default is still explicit.
    assert (second.timeout_seconds, second.max_retries) == (30.0, 3)


def test_suite_without_defaults_keeps_task_defaults(tmp_path):
    path = _write_yaml(tmp_path, "name: s\ntasks:\n  - {id: a, name: A, prompt: p}\n")

    task = load_suite(path).tasks[0]

    assert (task.timeout_seconds, task.max_retries) == (30.0, 1)
