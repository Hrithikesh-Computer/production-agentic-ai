# Enterprise CRM & Operational Copilot (Salesforce / Agentforce PoC)

> Status: Conceptual design with a bounded local reference prototype.
> Evidence boundary: The repository includes a mock-data, read-only CRM reference prototype at `prototypes/crm_operational_copilot/`. It has no Salesforce, Agentforce, live CRM/REST integration, or LLM runtime; see the prototype's `EVIDENCE.md` for measured local behavior and evidence gaps.

## 1. Problem and context

Many enterprises want to add a natural-language interface to operational systems, but the real challenge is not generating text. It is safely translating user intent into trusted business actions such as reading CRM records, surfacing summaries, and updating workflow state.

This architecture is intentionally lightweight but operationally realistic. It demonstrates how a business-facing copilot can query and act on CRM systems using tool boundaries and controlled execution patterns.

## 2. Architecture

```text
User query
  ↓
Agent orchestration layer
  ↓
MCP tool network / service adapters
  ↓
CRM and REST integration layer
  ↓
Model reasoning and action selection
  ↓
Execution + workflow update
```

## 3. Design pattern

The key idea is bounded action.

The agent is allowed to:

- retrieve customer and opportunity context,
- summarize account history,
- suggest next actions,
- trigger validated workflows when appropriate.

The tool boundary is explicit. That is important because a CRM is not a neutral sandbox; it contains live operational records and business workflows. Safe execution depends on well-defined connectors, access controls, and validation rules.

## 4. Why this pattern matters

This is often the first realistic enterprise use case for agentic AI: a natural-language layer over business systems. It is useful because it reduces friction without requiring a massive platform transformation. It can start as a focused prototype and mature into a governed production system.

## 5. Operational value

- Speeds up CRM lookup and summarization workflows
- Makes operational actions accessible through natural language
- Reduces manual context switching for sales and account teams
- Creates a path from prototype to governed enterprise deployment

## 6. Architectural lessons

- Tool boundaries must be small, explicit, and permission-aware.
- CRM actions require strong validation and authorization checks.
- A prototype should be designed so it can evolve into a governed workflow rather than a brittle demo.
- The best early use cases are narrow and operationally valuable.

## 7. Best-fit scenarios

This is best used in:

- sales operations,
- account management support,
- customer lifecycle coordination,
- lightweight operational copilots for business software.

## 8. Summary

This pattern shows how enterprise copilots can become useful without first building a massive architecture. The key is not “agentic everything.” The key is safe, bounded action with well-defined tool contracts and clear criteria for approval or escalation.
