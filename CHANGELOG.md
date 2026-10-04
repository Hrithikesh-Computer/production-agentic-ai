# Changelog

## Unreleased

- Identical duplicate response chunks no longer refresh a reassembly session's
  idle TTL; only a chunk that adds a new sequence refreshes activity.