"""Suite loaders and validation for YAML and JSON files."""

import json
from pathlib import Path
from typing import Union
import yaml

from agentbench.models.task import TaskSuite


def load_suite(file_path: Union[str, Path]) -> TaskSuite:
    """Load and validate a TaskSuite from a YAML or JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Suite file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if path.suffix.lower() in [".yaml", ".yml"]:
        raw_data = yaml.safe_load(content)
    elif path.suffix.lower() == ".json":
        raw_data = json.loads(content)
    else:
        # Attempt yaml first, fallback to json
        try:
            raw_data = yaml.safe_load(content)
        except Exception:
            raw_data = json.loads(content)

    if not isinstance(raw_data, dict):
        raise ValueError(f"Invalid suite file format in {file_path}. Root must be a dictionary.")

    return TaskSuite.model_validate(raw_data)


def save_suite(suite: TaskSuite, file_path: Union[str, Path]) -> Path:
    """Save a TaskSuite to YAML or JSON based on file extension."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = suite.model_dump(exclude_none=True)

    if path.suffix.lower() in [".yaml", ".yml"]:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return path
