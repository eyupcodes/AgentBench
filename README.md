# AgentBench 🤖📊

[![CI](https://github.com/eyupcodes/AgentBench/actions/workflows/ci.yml/badge.svg)](https://github.com/eyupcodes/AgentBench/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> A deterministic evaluation and benchmarking harness for AI agents and tool-calling workflows.

---

## 1. What is AgentBench?
**AgentBench** is a lightweight, local-first benchmarking framework designed to evaluate AI agent performance across real-world tasks. Unlike simple prompt eval tools that only inspect final text strings, AgentBench accounts for the entire agent execution lifecycle:
- **Tool-call event traces & sequence ordering**
- **Timeout and retry accounting**
- **Token consumption and cost estimation**
- **Deterministic verification hooks** (exact match, regex, JSON schema, numeric tolerance, tool call assertions)
- **Structured JSON & terminal reporting**

---

## 2. Why Use AgentBench?
Agent quality is more than just final text output. Measuring agentic systems requires answering:
- *Did the agent call the right tool with valid arguments?*
- *Did it follow the expected execution sequence without getting stuck in retry loops?*
- *How much wall-clock time and token cost did the task consume?*

AgentBench provides a clean abstraction between **Tasks/Suites**, **Agent Adapters**, and **Deterministic Evaluators**, allowing you to benchmark and compare local mock agents, scripted rules, or live LLM endpoints reproducibly.

---

## 3. Installation

### From PyPI / Source
```bash
# Clone repository
git clone https://github.com/eyupcodes/AgentBench.git
cd AgentBench

# Install in editable mode
pip install -e .

# Or install with development & testing dependencies
pip install -e ".[dev]"
```

---

## 4. Quick Start (30-Second Walkthrough)

### 1. Initialize a Starter Benchmark Suite
```bash
agentbench init
```
This generates `sample_suite.yaml` with ready-to-run tasks.

### 2. Validate Suite Syntax
```bash
agentbench validate sample_suite.yaml
```

### 3. Run the Benchmark
```bash
agentbench run --suite sample_suite.yaml --agent mock --verbose
```

### 4. Sample Terminal Output

```text
┌─────────────────────── AgentBench Execution Summary ────────────────────────┐
│ Suite: starter-suite (v1.0)                                                 │
│ Agent: MockAgent                                                            │
│ Pass Rate: 100.0% (3/3 passed)                                              │
│ Avg Score: 100.0%                                                           │
│ Total Time: 0.02s (avg 0.01s/task)                                          │
│ Tool Calls: 1 total (avg 0.3/task)                                          │
│ Retries: 0                                                                  │
│ Tokens / Cost: 300 tokens ($0.0006)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                 Task Results                                  
┌──────────────┬─────────────────────────┬────────┬───────┬──────────┬───────┬─────────┬─────────┐
│ Task ID      │ Name                    │ Status │ Score │ Time (s) │ Tools │ Retries │ Notes   │
├──────────────┼─────────────────────────┼────────┼───────┼──────────┼───────┼─────────┼─────────┤
│ task-math-01 │ Basic Arithmetic        │  PASS  │  100% │     0.00 │     0 │       0 │ -       │
│ task-tool-01 │ Weather Query with Tool │  PASS  │  100% │     0.01 │     1 │       0 │ -       │
│ task-json-01 │ Structured JSON Output  │  PASS  │  100% │     0.01 │     0 │       0 │ -       │
└──────────────┴─────────────────────────┴────────┴───────┴──────────┴───────┴─────────┴─────────┘
```

---

## 📐 Architecture & Core Concepts

```
┌──────────────────────────────────────────────────────────────┐
│                        Task Suite                            │
│  (YAML/JSON: Prompt, Tools Available, Evaluator Configs)     │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     Benchmark Runner                         │
│  - Timeout Guard (asyncio.wait_for)                          │
│  - Retry Accounting & Delay Policy                           │
│  - Event Logger (Tool Calls, Thoughts, LLM Usage)            │
└──────────────┬───────────────────────────────┬───────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│       Agent Adapter          │ │   Deterministic Evaluators  │
│  - MockAgent                 │ │  - exact_match              │
│  - ScriptedAgent             │ │  - contains / regex         │
│  - GenericLLMAgent           │ │  - json_schema              │
│  - Custom BaseAgent subclass │ │  - tool_call sequence/args  │
└──────────────────────────────┘ └─────────────┬───────────────┘
                                               │
                                               ▼
                                 ┌─────────────────────────────┐
                                 │   Report (JSON / Markdown)  │
                                 └─────────────────────────────┘
```

---

## 📝 Example Task Suite Definition (`suite.yaml`)

```yaml
name: agent-production-suite
version: "1.0"
description: "Core tool verification and reasoning suite."

tasks:
  - id: weather-01
    name: "Weather Tool Verification"
    prompt: "Fetch the weather for London"
    tools:
      - name: get_weather
        description: "Retrieve weather report for city"
        parameters:
          city:
            type: string
            required: true
    evaluators:
      - type: tool_call_count
        options:
          tool_name: get_weather
          exact_calls: 1
      - type: tool_argument
        options:
          tool_name: get_weather
          expected_args:
            city: London

  - id: extraction-02
    name: "Customer Order JSON Extraction"
    prompt: "Extract: John Doe, Order #8821, Amount $45.00"
    evaluators:
      - type: json_schema
        expected:
          name: "John Doe"
          order_id: 8821
          amount: 45.0
```

---

## 💻 Python SDK Usage

```python
import asyncio
from agentbench import (
    BenchmarkRunner,
    MockAgent,
    Task,
    TaskSuite,
    EvaluatorConfig,
    print_cli_report,
)

async def run():
    suite = TaskSuite(
        name="SDK Suite",
        tasks=[
            Task(
                id="task-1",
                name="Greeting Check",
                prompt="Say 'Welcome to AgentBench'",
                expected_output="Welcome to AgentBench",
                evaluators=[EvaluatorConfig(type="exact_match", expected="Welcome to AgentBench")],
            )
        ]
    )

    agent = MockAgent(default_response="Welcome to AgentBench")
    runner = BenchmarkRunner()
    report = await runner.run_suite(suite, agent)
    print_cli_report(report)

asyncio.run(run())
```

---

## 🛠️ CLI Reference

| Command | Description |
|---|---|
| `agentbench run -s <suite> -a <agent>` | Execute benchmark suite against agent adapter |
| `agentbench validate <suite>` | Validate suite schema and evaluators without execution |
| `agentbench list-adapters` | List all built-in and registered agent adapters |
| `agentbench list-evaluators` | List all supported deterministic evaluation hooks |
| `agentbench report <report.json>` | View or convert a saved benchmark report |
| `agentbench init` | Generate a starter suite file (`sample_suite.yaml`) |
| `agentbench version` | Print current AgentBench version |

### CLI Options for `agentbench run`
- `-s, --suite`: Path to suite file (`.yaml`, `.yml`, or `.json`).
- `-a, --agent`: Adapter name (`mock`, `scripted`, `generic_llm`) or dotted python class path (`my_module.MyAgent`).
- `-o, --output`: Save structured execution report to JSON.
- `--export-md`: Save markdown summary report.
- `-c, --concurrency`: Number of concurrent tasks (default: `1`).
- `-t, --timeout`: Override task timeout in seconds.
- `-r, --retries`: Override max retries per task.
- `-v, --verbose`: Show live step-by-step event trace.

---

## 🧪 Running Tests

AgentBench includes unit, adapter, evaluator, runner, and CLI integration tests:

```bash
# Run test suite
pytest -v

# Run with test coverage
pytest --cov=agentbench tests/
```

---

## 🔒 Security & Privacy
- **Local-First & Offline**: Deterministic evaluations run entirely in-process without contacting external services unless explicitly configured via HTTP LLM adapters.
- **Credential Safety**: No API keys are stored in repositories or log outputs. All keys are resolved dynamically from environment variables (`OPENAI_API_KEY`, etc.).

---

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.
