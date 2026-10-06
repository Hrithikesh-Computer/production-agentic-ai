# Open Owner Decisions

This register tracks decisions required before selecting or piloting a
production response-delivery design. The local reference choices are recorded
in [ADR-005](02-decisions/ADR-005-process-local-state-and-resource-bounds.md);
this register does not silently promote them to production decisions.

No accountable owners have been assigned in the repository. Each row remains
open until the named owner records a decision and its evidence in the relevant
ADR.

| Decision | Current reference disposition | Owner decision and trigger | Owner |
| --- | --- | --- | --- |
| Concurrency | `ReassemblySessionManager` is not thread-safe; callers sharing it serialize access. | Before threaded use, decide whether to retain the serialized single-caller contract or implement atomic per-message-ID updates. | Architecture/runtime owner: unassigned |
| Pilot wire path | No transport has been selected; ADR-001 remains reopened. | Wait for a named client and version. Complete ADR-001 client/payload measurements and the applicable [ADR-004 envelope gates](02-decisions/ADR-004-envelope-versioning.md) before selecting envelope transport. | Product/client and security/architecture owners: unassigned |
| State and isolation | ADR-005 keeps bounded process-local state for the reference only. | For a pilot, either accept its restart and per-process limits, or define durability, acknowledgments, per-principal quotas, isolation, and recovery together. | Product/data and architecture owners: unassigned |

## Related Open Questions

- Whether to accept legacy unversioned envelopes, and for what sunset period.
- Whether multi-key receiver state is scoped by `(key_id, message_id)` rather
  than `message_id` alone.

Both envelope questions are also tracked in [ADR-004](02-decisions/ADR-004-envelope-versioning.md).