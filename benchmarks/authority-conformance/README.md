# Authority conformance harness

This benchmark is a lightweight conformance harness for the repository's authority / intent model.

## Scenarios covered

- delegated authority with revocation before execution
- conflicting policies
- semantic mismatch under valid permissions
- runtime state change during execution
- multi-hop aggregation producing an unauthorized result

## Interpretation

These tests are living documentation of the repository's authority model. They are intentionally narrow and deterministic. They validate the logic of the model, not a full runtime security stack or production authorization system.

## How to run

```bash
python -m pytest benchmarks/authority-conformance/test_authority_conformance.py -q
```
