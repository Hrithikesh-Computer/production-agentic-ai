# Implementation Prompt

Use this to build or extend a module in `production-agent-reference`. Fill in the bracketed values before use.

---

You are implementing a module for the repository's single evolving reference project, `production-agent-reference`. This is an educational implementation, not a product — it exists to make a specific engineering lesson concrete and measurable.

Engineering lesson this module demonstrates: [LESSON]
Production problem it solves: [PROBLEM]
Stack constraints: Python, FastAPI, LangGraph (where appropriate), Pydantic, Redis, PostgreSQL, OpenTelemetry, Docker, GitHub Actions.

Requirements:

- The module must solve one documented production problem — not demonstrate a concept in the abstract. If you can't state the specific before-and-after this module makes measurable, stop and clarify the lesson first.
- Use Pydantic models for any structured data crossing a boundary (agent-to-agent, tool call, API request/response). Do not use unstructured free text where a schema would catch a real class of failure.
- Include OpenTelemetry instrumentation sufficient to produce the benchmark this module is meant to support — do not add observability as an afterthought.
- Write production-grade folder structure and error handling, not a single-file script. No client-specific logic, credentials, or naming of any kind.
- Document every non-obvious design decision inline as a comment, and flag any decision significant enough to warrant its own ADR using `templates/adr-template.md`.
- Include a minimal but real test that exercises the failure mode this module addresses — not just a happy-path test.
- Do not silently expand scope: if implementing this well requires infrastructure choices well outside the stated stack, note the trade-off rather than substituting a different stack.

Implement the module now, and note explicitly which parts of this module correspond to which section of the matching article.
