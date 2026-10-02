# Architecture & Presales Evaluation Prompt

Use this prompt when evaluating the repository (or any architecture derived from it) for technical soundness and customer-facing safety.

## Core Rule

Separate what actually exists from what is only described, intended, or hypothesized.

Never convert:
- design intent → proven capability
- research → production capability
- conceptual architecture → implemented architecture
- illustrative benchmark → production SLA
- theoretical scalability → demonstrated scalability
- security principle → implemented security control
- architecture diagram → deployed architecture
- documented claim → independently verified result

## Evidence Classifications

Classify every significant claim with the most accurate label:

| Classification | Meaning |
|---|---|
| **PROVEN** | Directly demonstrated by repository code, executable tests, measured benchmark, CI result, or other concrete repository evidence. |
| **DOCUMENTED CAPABILITY** | Explicitly described in repository documentation but not independently verified through implementation or measurement. |
| **IMPLEMENTED** | Present in executable code, but not necessarily production-validated. |
| **VERIFIED** | Implemented and supported by tests, benchmarks, CI, or other concrete validation evidence. |
| **DESIGN INTENT** | A proposed architectural principle, desired behavior, research direction, or intended future capability. |
| **HYPOTHESIS** | A technically plausible expectation that requires implementation or measurement to validate. |
| **NOT IMPLEMENTED** | The repository explicitly indicates that the capability does not exist, or the reviewed evidence demonstrates it is not implemented. |
| **NOT IN REPOSITORY** | The referenced artifact, service, pipeline, configuration, or implementation cannot be found in the reviewed repository. |
| **NOT DOCUMENTED** | The repository provides insufficient documentation to establish the claim. |
| **NOT VERIFIED** | The capability may exist, but the reviewed evidence does not demonstrate that it works as claimed. |
| **EXTERNALLY DEPENDENT** | Depends on systems, repositories, infrastructure, cloud services, datasets, or production environments outside the reviewed repository and therefore cannot be independently verified. |
| **PROVEN ABSENT** | Use only when repository evidence **explicitly** establishes that the capability does not exist. |

### Mandatory distinction

**NOT IN REPOSITORY** must never be treated as **PROVEN ABSENT**.

Correct wording examples:
- "The reviewed repository does not contain the referenced EMR pipeline."
- "The existence and implementation of this pipeline cannot be verified from the reviewed repository."

Incorrect wording:
- "The system does not have an EMR pipeline."

## Customer Claim Safety

Classify important presales claims as:

- **FACT** — Directly measurable or demonstrable from the repository.
- **DOCUMENTED CAPABILITY** — Explicitly specified but not independently verified.
- **DESIGN INTENT** — An intended architectural outcome.
- **HYPOTHESIS** — An expected result requiring validation.
- **CUSTOMER COMMITMENT RISK** — Must not be presented as a customer commitment until sufficient evidence exists.

## Architecture Classification

Clearly distinguish:

- **Existing implementation** — Actually present in executable code.
- **Reference implementation** — A narrow working implementation demonstrating a concept.
- **Architecture pattern** — Reusable architectural guidance.
- **Conceptual architecture** — A proposed or illustrative system design.
- **Production architecture** — Supported by implementation, deployment, operations, security, reliability, and evidence.

Do not call a conceptual architecture a production architecture.  
Do not call a research article a deployed capability.  
Do not infer a complete platform from multiple independent architecture sketches unless the repository explicitly defines their integration.

## Special Handling: EMR / Spark / PostgreSQL / RDS / Airflow / etc.

If detailed material references scripts or pipelines that are not present:

1. Preserve the documented optimization reasoning.
2. Identify the referenced artifacts as **NOT IN REPOSITORY**.
3. Do not claim the pipeline is implemented.
4. Do not invent missing architecture.
5. Treat optimization recommendations as **HYPOTHESIS** until actual code/configuration/runtime evidence is available.

## Performance Claims

Distinguish:
- local benchmark
- synthetic benchmark
- illustrative example
- unit/integration test measurement
- controlled environment measurement
- production measurement
- production SLA/SLO

Never present an illustrative or local result as a production latency guarantee or SLA.

## Security & Reliability

A security principle or architecture recommendation is **not** an implemented security control.  
A reliability recommendation is **not** evidence of production resilience.

## AI / Agentic AI Claims

Distinguish:
- conceptual reasoning
- implemented workflow
- model integration
- retrieval implementation
- evaluation framework
- measured AI quality
- tool-call success
- hallucination/error measurement
- cost measurement
- production monitoring
- human review

Do not infer effectiveness merely from the presence of RAG, agents, LangGraph, guardrails, citations, tool calling, context engineering, or authority models.

## Required Report Structure

Every evaluation must contain:

1. **Executive Summary** — What the repository actually represents.
2. **Repository Evidence Boundary** — Summary of proven / implemented / verified / documented / conceptual / not implemented / not in repository / not verified / externally dependent / proven absent.
3. **Architecture Assessment** — Using the evidence classifications above.
4. **Performance Evidence** — Measured vs hypothesis.
5. **AI / Agent Evaluation** — Design principles vs implemented/evaluated capabilities.
6. **Security / Reliability Assessment** — Controls that exist vs recommended controls.
7. **Presales Claim Safety** table:

   | Claim | Evidence | Classification | Customer-safe? | Missing evidence |
   | ----- | -------- | -------------- | -------------- | ---------------- |

   "Customer-safe?" values:
   - Supported by evidence
   - Supported but not independently verified
   - Requires validation
   - Not supported by reviewed evidence

8. **Customer Questions** the current repository cannot answer.
9. **Evidence Needed Before Customer Commitment**.
10. **Prioritized Actions** (factual impact only; no arbitrary scores).

## Language Rules

Prefer:
- "The repository demonstrates..."
- "The documentation describes..."
- "The reviewed code implements..."
- "The repository does not provide evidence for..."
- "This appears to be a design proposal..."
- "This is a hypothesis requiring validation..."
- "Cannot determine from the reviewed repository."

Avoid absolute claims unless the repository contains sufficient evidence.

## Scope Constraint

This is an evaluation-methodology improvement.  
Do not redesign the repository, rewrite research articles, invent missing systems, or add frameworks.
