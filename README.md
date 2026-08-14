# Production Agentic AI

Building reliable agentic AI systems through engineering investigation, architecture decision-making, and production evidence.

This repository documents how production AI systems fail, what alternatives exist, and how teams decide under real constraints. The focus is on engineering judgment rather than tutorial-style demos.

## What this repository covers

- production lessons from agentic systems
- architecture decisions and trade-offs
- context, memory, and retrieval challenges
- response delivery and latency investigations
- reference implementations that accompany the writing

## Recommended reading path

1. [03-production-lessons/](./03-production-lessons/) for production investigations and lessons learned
2. [01-agent-architecture/](./01-agent-architecture/) for architectural patterns and design trade-offs
3. [02-context-and-memory/](./02-context-and-memory/) for context budgeting and memory-related systems work
4. [04-reference-implementation/](./04-reference-implementation/) for the accompanying implementation examples

## Featured article

- [03-production-lessons/01-adaptive-response-delivery.md](./03-production-lessons/01-adaptive-response-delivery.md) — Large Response Delivery in Agentic AI: A Production Investigation

## Repository structure

- [README.md](./README.md) — short overview and entry point
- [ROADMAP.md](./ROADMAP.md) — repository scope, standards, and publishing approach
- [CONTRIBUTING.md](./CONTRIBUTING.md) — contribution process
- [03-production-lessons/](./03-production-lessons/) — production investigations and engineering case studies
- [04-reference-implementation/](./04-reference-implementation/) — code that supports the articles

## How to use this repository

If you are evaluating a production design decision, start with the article that matches the problem you are facing. If you are looking for implementation detail, read the corresponding reference module alongside the article.

## License

See [LICENSE](./LICENSE).
