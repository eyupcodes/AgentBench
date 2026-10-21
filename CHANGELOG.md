# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- JSON suites with missing or unrecognized extensions now preserve escaped Unicode characters outside the BMP (such as emoji); regression tests also cover YAML/JSON round trips and invalid input validation.
- `tool_call_count` without `min_calls`/`max_calls`/`exact_calls` and `tool_call_sequence` without a `sequence` now fail with a reason naming the missing option instead of passing for any trace; `tool_argument` no longer reports tool `'None'` when no tool was called (#15).
- `agentbench run` rejects `--concurrency` below 1, non-positive `--timeout` and negative `--retries` as usage errors, and reports an unwritable `--output` or `--export-md` path with a one-line error and exit code 1 instead of a traceback (#13).
- A custom evaluator whose `function` path cannot be imported now yields a failed result naming the path, instead of raising (#10).
- `BenchmarkRunner` records a failed evaluation when an evaluator cannot be built or raises, so one bad task no longer aborts the whole suite (#10).

## [0.1.1] - 2026-10-17

### Added
- `ruff format --check` and `ruff check` steps in CI, with the existing findings fixed (#5).

### Fixed
- `pytest-cov` is now part of the `dev` extra so `pytest --cov=agentbench` works as documented; CI enforces an 80% coverage gate (#3).

## [0.1.0] - 2026-08-31

### Added
- Core Agent Adapter interface (`BaseAgent`, `AgentExecutionContext`, `AgentResponse`).
- Built-in adapters: `MockAgent`, `ScriptedAgent`, and `GenericLLMAgent` (OpenAI-compatible HTTP client).
- Dynamic adapter registry (`get_adapter`, `register_adapter`, `list_adapters`).
- Deterministic evaluators:
  - `ExactMatchEvaluator`
  - `ContainsEvaluator`
  - `RegexEvaluator`
  - `JSONSchemaEvaluator`
  - `NumericToleranceEvaluator`
  - `ToolCallCountEvaluator`
  - `ToolCallSequenceEvaluator`
  - `ToolArgumentEvaluator`
  - `CustomEvaluator`
- Asynchronous task runner (`BenchmarkRunner`) with timeout handling (`asyncio.wait_for`) and retry accounting.
- Structured event logging system (`AgentEvent`, `EventType`, `ToolCallEvent`, `TokenUsage`).
- Metric computation (`SuiteMetrics`, `BenchmarkReport`) with token cost estimation and tool breakdown.
- Multi-format reporting: Rich CLI terminal tables, JSON export/import, and Markdown summaries.
- Typer-based CLI with commands: `run`, `validate`, `list-adapters`, `list-evaluators`, `report`, `init`, `version`.
- YAML and JSON task suite loader and validator (`load_suite`, `save_suite`).
- Comprehensive test suite covering models, adapters, evaluators, runner, reporting, and CLI commands.
- GitHub Actions CI workflow for Python 3.10, 3.11, and 3.12.
