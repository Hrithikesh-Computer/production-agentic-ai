# Changelog

## Unreleased

- Receiver outcome events use a fixed vocabulary and contain no payloads, IDs,
  keys, tags, limits, or callback text.
- Receiver outcome sink failures are now discarded without changing protocol
  control flow; original exceptions and retained state continue unchanged.
- The manager's aggregate active-memory cap now includes a conservative
  96-byte charge for each retained chunk; per-message payload limits are
  unchanged.
- Identical duplicate response chunks no longer refresh a reassembly session's
  idle TTL; only a chunk that adds a new sequence refreshes activity.