# Reconciliation: Architecture Documents 04 and 07

## Decision status

**Recommendation: merge the two concepts into one target architecture, using document 04 as the overall workflow architecture and incorporating document 07's evidence-retrieval pattern as a subsystem.** This is a recommendation only. A human product/architecture owner must sign off before either original is edited, merged, renamed, or retired. Both originals remain untouched by this reconciliation.

Current paths, confirmed via `REPO-MAP.md`:

- `01-agent-architecture/04-fintech-governance-risk-agentic-platform.md`
- `01-agent-architecture/07-enterprise-audit-compliance-risk-copilot.md`

Both are conceptual and unimplemented in this repository. No Azure, LangGraph, ServiceNow, enterprise corpus, SQL connector, or deployment evidence was found here.

## Overlap

| Concern | Document 04 | Document 07 | Assessment |
|---|---|---|---|
| Problem | Regulated governance and risk decisions need evidence, policy interpretation, and review. | Audit, compliance, and risk teams need grounded answers across fragmented information. | Same enterprise governance/risk problem family. |
| Core capability | Collect evidence, interpret policy, produce structured risk/control outcomes, route review, synchronize operational state. | Retrieve evidence from documents and structured data, synthesize citation-backed answers for risk, audit, or compliance workflows. | Evidence gathering and defensible decision support overlap directly. |
| Users and workflows | Governance/risk operations; control testing and risk analysis. | Compliance/audit/risk teams; policy answering, incident review, operational investigation. | Substantial user and workflow overlap; specific initial workflow is a product decision. |
| Grounding | Evidence-backed reasoning, citations/justification, structured output. | Hybrid retrieval, citations, source tracing, structured evidence. | Compatible and mutually reinforcing. |
| Human control | Explicit human review and approvals are central. | Explicit review boundaries and human explainability are required. | Same control need, more concretely specified in 04. |
| Auditability | Replayable decisions, traceability, versioned operational record. | Source citations and evidence chain from question to source. | Complementary parts of one audit trail. |
| Enterprise data | Multiple enterprise sources and financial records. | Document corpora, search index, SQL/structured sources. | 07 makes 04's generic evidence-source layer more concrete. |

## Genuine divergence

| Dimension | Document 04 emphasis | Document 07 emphasis |
|---|---|---|
| Primary abstraction | Multi-use-case workflow platform and state machine. | Retrieval and reasoning copilot for evidence discovery. |
| Interaction shape | Routed use cases, branching workflows, review gates, and system synchronization. | Natural-language question to hybrid retrieval to cited answer. |
| Named technology | React, LangGraph, Azure OpenAI, ServiceNow, connectors, audit persistence. | Azure AI Search/vector retrieval, enterprise documents, SQL, LLM grounding. |
| Operational side effects | ServiceNow ticket/workflow update and decision-record persistence are included in the design. | Workflow output is described, but write/update execution is not architecturally specified. |
| Retrieval specificity | Retrieval is present but underspecified. | Vector, keyword/metadata, and structured SQL retrieval are explicit. |

These divergences are architectural layers, not proof of separate product use cases. The repository contains no implementation evidence that validates either technology set or the stated operational value.

## Recommended merged target architecture

1. Provide a bounded intake/router for named governance, audit, compliance, and risk workflows.
2. Use a stateful workflow orchestrator to control evidence acquisition, validation, reasoning, human review, and finalization.
3. Make retrieval an explicit subsystem. Select among document, keyword/metadata, vector, and structured-query sources based on verified source inventory and access policy; do not treat any named vendor as selected without an owner decision and evidence.
4. Require structured outputs that carry source identifiers, citations, provenance, uncertainty, and decision rationale.
5. Route uncertain or high-impact results to a human approval step. Any ticket update or operational write happens only after a defined approval and validation gate.
6. Persist a versioned audit record linking request, retrieved evidence, policy/version, model/configuration, approvals, decision, and any approved side effect.

This architecture retains 04's workflow and approval framing while giving it 07's concrete evidence-retrieval boundary. It does not establish a production-ready design or settle vendor choices.

## Disposition of document 07 if document 04 is the container

No substantive capability from 07 is recommended for removal. Its retrieval modes, evidence traceability, citation requirement, and audit/compliance scenarios should be carried into 04 as the retrieval subsystem. The following items should not survive as independent, duplicative claims in a future merged article:

- A second standalone architecture with its own implied product boundary: duplicate the same governance/risk audience and evidence-grounded workflow described by 04.
- Treating Azure AI Search as a committed platform choice: the repository contains no requirements comparison, pricing, security review, or deployment evidence to support that commitment. Keep it as an unselected candidate until evaluated.
- Unqualified operational-value claims such as reduced effort or increased trust: no user study or benchmark evidence is present. Preserve these only as hypotheses with `EVIDENCE REQUIRED`.

The retrieval capabilities themselves are retained, not dropped. The recommendation is a conceptual consolidation only; no original file has been edited or retired.

## Required human sign-off

Before changing either source article, the product/architecture owner must decide:

- whether governance/risk workflow orchestration is the primary product boundary;
- which initial workflow and user group are in scope;
- which sources and write-capable systems are genuinely required;
- approval authority and permitted side effects;
- whether the separate title/number 07 remains as a component article or is retired after a future approved merge;
- which technology choices have evidence and are approved.

**Status: awaiting human product/architecture owner sign-off.**
