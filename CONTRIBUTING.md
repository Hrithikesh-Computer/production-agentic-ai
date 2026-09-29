# Contributing

This repository holds every contribution — including the maintainer's own — to the standards defined in [`ROADMAP.md`](./ROADMAP.md). Read that file first. This document explains how to act on it.

---

## Before You Start

Confirm your idea passes the Scope Guard:

> If a topic can stand alone without mentioning production Agentic AI, it belongs in another repository.

If your idea is about agent architecture, context engineering, or a failure mode tied to either, it's in scope. If it's a general software engineering, security, infrastructure, or MLOps topic that doesn't specifically explain an Agentic AI decision, it isn't — see [Out of Scope](./ROADMAP.md#out-of-scope) in the roadmap for the current explicit list.

If you're unsure, open an issue describing the idea in two or three sentences before writing anything. This saves both of us time.

---

## What Counts as a Contribution

- A new article following the [Article Template](./ROADMAP.md#article-template)
- An improvement, correction, or benchmark refresh to an existing article
- A new module or fix to the local reference implementation under `04-reference-implementation/`
- A new or updated diagram in `diagrams/`
- A correction to an Architecture Decision Record

Contributions that only add prose — restructuring an explanation, fixing unclear wording — are welcome as small pull requests and are not held to the publishing gate below. Substantive new content is.

---

## The Publishing Gate

This is not optional and applies equally to every contributor, including the maintainer.

A new article is merged only if it includes at least one of:

- a reproducible experiment
- a benchmark
- a debugging story
- a documented production failure
- a measurable trade-off
- a surprising observation

**Opinion alone is not sufficient.** If your draft is a well-reasoned argument with no evidence behind it, it isn't ready yet — turn the argument into a hypothesis, run the experiment that would confirm or deny it, and come back with the result either way. A clearly documented negative result satisfies the gate. An unsupported opinion does not, no matter how well written.

---

## Submitting an Article

1. **Open an issue first** with your proposed hypothesis — what you expect to find and why. This avoids duplicated or out-of-scope work before you invest time in it.
2. **Follow the [Article Template](./ROADMAP.md#article-template) exactly**: Decision Summary, Problem, Motivation, Hypothesis, Background, Why the Obvious Solution Fails, Architecture, Trade-offs, Failure Modes, Reference Implementation, Experiment, Benchmark, Observations, Decision, Interview Questions, Further Reading. If a section genuinely doesn't apply, say so explicitly rather than omitting it.
3. **Write the Decision Summary last.** It's the hardest part to get right and the part most readers will actually read — it should hold up on its own, in three to five sentences, without the rest of the article.
4. **Include a working reference implementation module** if the article makes an architectural claim. The module should demonstrate a measurable before-and-after, not just a working example.
5. **Include real diagrams**, using Mermaid, checked into `diagrams/` and referenced from the article — not pasted as static images.
6. **Open a pull request** referencing the original issue. Fill in the PR checklist below.

---

## Pull Request Checklist

Before requesting review, confirm:

- [ ] The topic passes the Scope Guard
- [ ] The article follows the full Article Template, with no sections silently skipped
- [ ] At least one publishing-gate requirement is met, and it's stated explicitly in the PR description
- [ ] Diagrams are in Mermaid and checked into `diagrams/`
- [ ] Any reference implementation changes include a benchmark showing before-and-after
- [ ] No client code, client architecture, internal prompts, internal metrics, or proprietary workflows appear anywhere in the contribution — see the [Anonymization Policy](./ROADMAP.md#anonymization-policy)
- [ ] Any case study drawn from real experience has been generalized before writing, not edited afterward

A PR missing any of these will be sent back with specific feedback rather than merged with exceptions. The standards apply the same way to every contribution regardless of who submits it.

---

## Architecture Decision Records

If your contribution involves a non-obvious engineering decision in the reference implementation, include an ADR alongside it using the template in [`ROADMAP.md`](./ROADMAP.md#architecture-decision-records): Context, Problem, Options Considered, Decision, Trade-offs, Consequences. ADRs live next to the article and implementation they belong to, not in a separate top-level folder.

---

## Review Process

Every submission is reviewed against the checklist above, not against subjective taste. Common reasons a PR is sent back:

- The claim isn't backed by evidence — a benchmark or experiment is requested before merge.
- The topic is out of scope, or drifts into general software engineering partway through.
- The reference implementation demonstrates a concept but doesn't measure it against anything.
- The Decision Summary doesn't hold up without the rest of the article.

Reviews prioritize whether the standard was met over stylistic preference. Two contributions that meet the standard in different voices are both acceptable.

---

## What Won't Be Accepted

- Framework tutorials with no architectural reasoning behind them
- Topics from the [Out of Scope](./ROADMAP.md#out-of-scope) list, even if well written
- Articles that skip the Hypothesis or Experiment sections
- Client-identifying material of any kind
- New top-level folders or themes — see [Repository Structure](./ROADMAP.md#repository-structure); nothing is added there unless something else is removed

---

## Questions

Open an issue. If it's a question about whether something fits the repository's scope, say so explicitly — those get answered quickly, since a clear scope boundary is what keeps this repository useful.