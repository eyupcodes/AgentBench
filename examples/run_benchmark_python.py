"""Example demonstrating how to use AgentBench programmatically in Python."""

import asyncio
from agentbench import (
    BenchmarkRunner,
    EvaluatorConfig,
    MockAgent,
    Task,
    TaskSuite,
    generate_markdown_report,
    print_cli_report,
)


async def main():
    # 1. Define a benchmark suite
    suite = TaskSuite(
        name="SDK Demo Benchmark",
        description="Demonstrating programmatic task evaluation in Python",
        tasks=[
            Task(
                id="sdk-task-1",
                name="Sentiment Analysis",
                prompt="Analyze sentiment of: 'The benchmark runner works wonderfully!'",
                expected_output="positive",
                evaluators=[
                    EvaluatorConfig(type="exact_match", expected="positive")
                ],
            ),
            Task(
                id="sdk-task-2",
                name="Tool Sequence Simulation",
                prompt="Retrieve records and calculate average",
                evaluators=[
                    EvaluatorConfig(type="tool_call_count", options={"min_calls": 1}),
                ],
            ),
        ],
    )

    # 2. Configure an agent adapter
    agent = MockAgent(
        name="CustomAssistantAgent",
        responses={"sdk-task-1": "positive"},
        tool_call_plans={
            "sdk-task-2": [
                {"name": "fetch_records", "input": {"limit": 10}, "output": [10, 20, 30]}
            ]
        },
    )

    # 3. Execute the benchmark
    runner = BenchmarkRunner()
    report = await runner.run_suite(suite, agent)

    # 4. Display results in terminal
    print_cli_report(report)

    # 5. Output Markdown summary
    print("\n--- Generated Markdown ---")
    print(generate_markdown_report(report))


if __name__ == "__main__":
    asyncio.run(main())
