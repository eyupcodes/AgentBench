# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
