# Benchmark Prompt

Use this to design a benchmark for `templates/benchmark-template.md`. Fill in the bracketed values before use.

---

You are designing a reproducible benchmark to support a production Agentic AI article. The benchmark must produce a real, defensible number — not an illustrative or hypothetical one.

Claim being tested: [CLAIM]
System or component under test: [COMPONENT]
Available environment/tooling: [ENVIRONMENT]

Design a benchmark that includes:

- **Objective**: the single question this benchmark answers.
- **Environment**: exact versions, hardware or infrastructure assumptions, and anything that would need to be held constant to reproduce this.
- **Workload**: what is actually being run against the system — real or realistic synthetic data, request volume, concurrency, and why this workload was chosen over alternatives.
- **Metrics**: the specific, named metrics being measured (e.g., p50/p95 latency, token count, cost per request, accuracy against a labeled set) — not vague terms like "performance."
- **Method**: the exact steps to run this benchmark, in enough detail that someone else could reproduce it without asking a follow-up question.

Treat checked-in code and configuration as the source of truth for the component under test. Do not assume a benchmark runner, server, client, telemetry backend, or production dependency exists unless it is present. Do not fabricate results. If this prompt is being used before the benchmark has actually been run, output only the design (Objective through Method) and stop — Results, Analysis, Trade-offs, and Conclusion are filled in afterward from real output, never generated in advance.
