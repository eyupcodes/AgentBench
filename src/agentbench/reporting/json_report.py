"""JSON serialization and deserialization for benchmark reports."""

import json
from pathlib import Path
from typing import Union
from agentbench.models.report import BenchmarkReport


def save_report_json(report: BenchmarkReport, file_path: Union[str, Path], indent: int = 2) -> Path:
    """Serialize a BenchmarkReport to a JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=indent))
    return path


def load_report_json(file_path: Union[str, Path]) -> BenchmarkReport:
    """Deserialize a BenchmarkReport from a JSON file."""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BenchmarkReport.model_validate(data)
