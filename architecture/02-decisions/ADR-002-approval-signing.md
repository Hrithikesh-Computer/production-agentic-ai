# ADR-002: Approval Evidence and Signing

- **Status:** Proposed
- **Date:** 2026-10-03
- **Decision owner:** Security and architecture owners to be assigned

## Context

The authority reference uses an in-memory `Ticket` as evidence of a past allow decision and re-evaluates current grant state when the ticket is used. The response-envelope reference uses a caller-supplied shared HMAC-SHA256 key to authenticate chunk fields. Neither mechanism is integrated with the CRM mock, an enterprise identity provider, durable approval workflow, or production key management.

The target workflow requires a human to approve an exact CRM action. A model-proposed action or a prior approval must not independently grant execution authority after policy, identity, record state, or approval status changes.

## Options

1. **Shared-key HMAC:** compact and suitable when a small trusted service set shares managed secret material. Every verifier holding the key can also forge valid MACs; rotation and distribution must be designed.
2. **Asymmetric signature:** a signing service holds the private key and independent services verify with public keys. This separates signing and verification authority but adds signing-key lifecycle, algorithm, rotation, and revocation responsibilities.
3. **No portable signed approval token:** store an approval record server-side, bind it to the proposal and record version, and re-evaluate current identity/policy at execution. Use authenticated service channels and audit events; avoid treating a bearer artifact as authority.

## Decision

For the proposed CRM workflow, use **server-side, one-action approval state with a live policy recheck at execution**. Do not make a reusable HMAC or asymmetric-signed approval token the authority to write. Approval must bind the actor, reviewer, action, target record, proposed values, relevant record version, and expiry; the gateway must verify current approval state and current policy before invoking the CRM.

If later requirements demand portable approval evidence across independently operated trust domains, perform a separate key-management review. Prefer asymmetric signatures for a verifier population that must validate without receiving signing authority; choose HMAC only where shared-key trust and distribution are explicitly acceptable. This selection is provisional and requires customer security review.

## Consequences

- A persistent approval store, atomic state transition, replay protection, expiry, and concurrency behavior are required; none is implemented in the repository.
- A changed target record or changed proposed values invalidate the approval and require review again.
- The CRM connector must not accept a model-originated action without the gateway's current execution authorization.
- Audit records need an integrity/retention design. This ADR does not claim that ordinary append-only storage is tamper-proof.
- The existing HMAC envelope remains a local protocol example, not the selected approval mechanism.

## Evidence and gaps

- [Authority policy reference](../../04-reference-implementation/authority_policy.py).
- [Envelope threat boundary and key-management gaps](../../04-reference-implementation/adaptive-response-filter/EVIDENCE.md).
- Customer identity mapping, CRM conditional writes, approval rules, signing requirements, key service, audit retention, and separation-of-duties policy: **not found in repo; discovery required**.
