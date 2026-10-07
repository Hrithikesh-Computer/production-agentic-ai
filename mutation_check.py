# ruff: noqa: E501  (mutant table lines are intentionally exact source strings)
"""Mutation check for authority, NDJSON, and approval-workflow behavior.

Usage (from the repository root):
    python mutation_check.py --impl 04-reference-implementation --tests tests

Each mutant makes one small change to the implementation. A mutant counts as
KILLED when the test suite then fails, SURVIVED when it still passes.
A mutant whose target text no longer exists is reported NOT APPLICABLE: that
means the source changed, so review the mutant (or add a new one) by hand.
Exit code is 1 if any mutant survived.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DENY_NO_GRANT = '    if grant is None:\n        return Decision("deny", "no grant")\n'
AUTH = {
    "drop not_before": ('    if at < grant.not_before:\n        return Decision("deny", "grant not yet valid")\n', ""),
    "not_before <=": ("if at < grant.not_before:", "if at <= grant.not_before:"),
    "drop no-grant": (DENY_NO_GRANT, "    assert grant is not None\n"),
    "expiry >": ("if at >= grant.expires_at:", "if at > grant.expires_at:"),
    "revocation >": ("and at >= grant.revoked_at", "and at > grant.revoked_at"),
    "drop revocation": ('    if grant.revoked_at is not None and at >= grant.revoked_at:\n        return Decision("deny", "grant revoked")\n', ""),
    "tie: allow wins": ('if "deny" in winning_effects:', 'if "deny" in winning_effects and len(winning_effects) == 1:'),
    "refer: deny loses tie": ('if "deny" in winning_effects:', 'if "deny" in winning_effects and "refer" not in winning_effects:'),
    "refer: ignored": ('if "refer" in winning_effects:', 'if False:'),
    "refer: allow wins tie": ('if "refer" in winning_effects:', 'if "refer" in winning_effects and "allow" not in winning_effects:'),
    "priority min": ("highest_priority = max(", "highest_priority = min("),
    "no policy -> allow": ('return Decision("deny", "no applicable policy")', 'return Decision("allow", "no applicable policy")'),
    "ignore principal": ('    if grant.principal != principal:\n        return Decision("deny", "principal mismatch")\n', ""),
    "ignore action": ('    if grant.action != action:\n        return Decision("deny", "action mismatch")\n', ""),
    "rules unfiltered": ("applicable = [rule for rule in rules if rule.action == action]", "applicable = list(rules)"),
    "agg: skip constraints": ("        if constraint.actions.issubset(actions):", "        if False:"),
    "agg: intersect not subset": ("constraint.actions.issubset(actions)", "bool(constraint.actions & actions)"),
    "agg: skip per-action checks": (
        '        if decision.effect == "deny":\n            return decision\n',
        '        if False:\n            return decision\n',
    ),
    "agg: empty allowed": ('    if not actions:\n        return Decision("deny", "no actions requested")\n', ""),
    "agg: drop refer propagation": ('    if referral is not None:\n        return referral\n', '    if False:\n        return referral\n'),
    "ticket: no re-eval at use": ("    current_decision = evaluate_authority(\n        grant=current_grant, principal=principal, action=action, at=at, rules=rules\n    )\n    if current_decision.effect == \"deny\":\n        return current_decision\n    if at >= ticket.expires_at:\n        return Decision(\"deny\", \"ticket expired\")\n    return current_decision", '    if at >= ticket.expires_at:\n        return Decision("deny", "ticket expired")\n    return Decision("allow", "ticket valid")'),
    "ticket: stale-check bug": ("    current_decision = evaluate_authority(\n        grant=current_grant, principal=principal, action=action, at=at, rules=rules\n    )", "    current_decision = evaluate_authority(\n        grant=current_grant, principal=principal, action=action, at=ticket.issued_at, rules=rules\n    )"),
    "ticket: revocation before expiry": ('    if current_decision.effect == "deny":\n        return current_decision\n    if at >= ticket.expires_at:\n        return Decision("deny", "ticket expired")\n', '    if at >= ticket.expires_at:\n        return Decision("deny", "ticket expired")\n    if current_decision.effect == "deny":\n        return current_decision\n'),
    "ticket: skip before-issue": ('    if at < ticket.issued_at:\n        return Decision("deny", "ticket used before issue time")\n', ""),
    "ticket: skip binding": ('    if ticket.principal != principal or ticket.action != action:\n        return Decision("deny", "ticket does not match request")\n', ""),
    "ticket: bind principal only": ("ticket.principal != principal or ticket.action != action", "ticket.principal != principal"),
    "ticket: bind action only": ("ticket.principal != principal or ticket.action != action", "ticket.action != action"),
    "ticket: skip expiry": ('    if at >= ticket.expires_at:\n        return Decision("deny", "ticket expired")\n', ""),
    "ticket: expiry boundary >": ("if at >= ticket.expires_at:", "if at > ticket.expires_at:"),
    "ticket: refer issues ticket": ('if decision.effect != "allow":', 'if decision.effect == "deny":'),
    "ticket: ttl guard removed": ('    if ttl <= 0:\n        raise ValueError("ttl must be positive")\n', ""),
    "session: ignore prior": ("combined = prior_actions | {action}", "combined = frozenset({action})"),
    "session: skip constraint": ("        if action in constraint.actions and constraint.actions <= combined:", "        if False:"),
    "session: any-member match": ("constraint.actions <= combined", "bool(constraint.actions & combined)"),
    "session: drop individual denial": ('    if decision.effect == "deny":\n        return decision\n    combined', "    combined"),
    "session: refer becomes allow": (
        "    for constraint in aggregation_constraints:\n        if action in constraint.actions and constraint.actions <= combined:\n            return Decision(\"deny\", constraint.reason)\n    return decision\n",
        "    for constraint in aggregation_constraints:\n        if action in constraint.actions and constraint.actions <= combined:\n            return Decision(\"deny\", constraint.reason)\n    return Decision(\"allow\", \"session allowed\")\n",
    ),
    "ticket: use refer becomes allow": ('    return current_decision\n\n\ndef evaluate_in_session', '    return Decision("allow", "ticket valid")\n\n\ndef evaluate_in_session'),
}
WORKFLOW = {
    "workflow: accept disallowed proposal field": (
        '        current = self._now(at)\n        if field not in ALLOWED_UPDATE_FIELDS:\n            raise ValueError(f"Field \'{field}\' cannot be updated by this prototype.")\n',
        '        current = self._now(at)\n        if False:\n            raise ValueError(f"Field \'{field}\' cannot be updated by this prototype.")\n',
    ),
    "connector: accept disallowed approved field": (
        '        if reviewer_decision.effect != "allow":\n            raise PermissionError("reviewer approval authority is no longer valid")\n        if field not in ALLOWED_UPDATE_FIELDS:\n            raise ValueError(f"Field \'{field}\' cannot be updated by this prototype.")\n',
        '        if reviewer_decision.effect != "allow":\n            raise PermissionError("reviewer approval authority is no longer valid")\n        if False:\n            raise ValueError(f"Field \'{field}\' cannot be updated by this prototype.")\n',
    ),
    "workflow: skip actor binding": ('        if actor != proposal.requester:\n', '        if False:\n'),
    "workflow: skip approved-state check": ('        if record.status != "approved":\n', '        if False:\n'),
    "workflow: ignore referral handling": (
        '            raise PermissionError(decision.reason)\n        if decision.effect == "refer":\n',
        '            raise PermissionError(decision.reason)\n        if False:\n',
    ),
    "workflow: skip reviewer recheck": ('            if reviewer_decision.effect != "allow":\n', '            if False:\n'),
    "workflow: skip execution expiry": (
        '        if current >= proposal.expires_at:\n            record.status = "expired"\n            self._audit(\n                "proposal_expired", actor=actor, proposal=proposal, at=current\n',
        '        if False:\n            record.status = "expired"\n            self._audit(\n                "proposal_expired", actor=actor, proposal=proposal, at=current\n',
    ),
    "workflow: skip stale-record check": (
        '        if (\n            self.crm.record_version(proposal.customer_id)\n            != proposal.expected_record_version\n        ):\n',
        '        if False:\n',
    ),
    "workflow: skip connector record binding": (
        '            or proposal.customer_id != customer_id\n',
        '',
    ),
    "workflow: skip connector field binding": (
        '            or proposal.field != field\n',
        '',
    ),
    "workflow: skip connector value binding": (
        '            or proposal.proposed_value != value\n',
        '',
    ),
    "workflow: allow replay after execution": (
        '        if record.status != "approved":\n',
        '        if record.status not in {"approved", "executed"}:\n',
    ),
    "workflow: omit execution-started audit": (
        '        self._audit("execution_started", actor=actor, proposal=proposal, at=current)\n',
        '        pass\n',
    ),
    "workflow: mislabel execution-started audit": (
        'self._audit("execution_started", actor=actor, proposal=proposal, at=current)',
        'self._audit("execution_succeeded", actor=actor, proposal=proposal, at=current)',
    ),
    "workflow: skip connector version check": (
        '        if self._versions[customer_id] != expected_version:\n',
        '        if False:\n',
    ),
}
NDJSON = {
    "no poison on error": (
        "        except Exception:\n            self._poison()\n            raise",
        "        except Exception:\n            raise",
    ),
    "feed ignores failed flag": ('        if self._failed:\n            raise DecoderFailedError("decoder failed; discard the response and retry")\n        if self._finished:\n            raise ValueError("decoder is finished")', '        if self._finished:\n            raise ValueError("decoder is finished")'),
    "finish ignores failed flag": ('        if self._failed:\n            raise DecoderFailedError("decoder failed; discard the response and retry")\n        if self._finished:\n            return', "        if self._finished:\n            return"),
    "no max when no newline": (
        '                if delimiter < 0:\n                    fragment = data[offset:]\n                    if len(fragment) > self._max - len(self._pending):\n                        raise RecordTooLargeError("record exceeds size limit")\n',
        '                if delimiter < 0:\n                    fragment = data[offset:]\n',
    ),
    "no max on complete record": (
        '                fragment = data[offset:delimiter]\n                if len(fragment) > self._max - len(self._pending):\n                    raise RecordTooLargeError("record exceeds size limit")\n',
        '                fragment = data[offset:delimiter]\n',
    ),
    "limit off by one (>=)": (
        '                fragment = data[offset:delimiter]\n                if len(fragment) > self._max - len(self._pending):\n',
        '                fragment = data[offset:delimiter]\n                if len(fragment) >= self._max - len(self._pending):\n',
    ),
    "accept non-object": ('                if not isinstance(value, dict):\n                    raise NDJSONError("NDJSON records must be JSON objects")\n', ""),
    "decode errors=ignore": ('line.decode("utf-8")', 'line.decode("utf-8", errors="ignore")'),
    "drop pending between feeds": (
        '                self._pending.extend(fragment)\n                line = bytes(self._pending)',
        '                self._pending = bytearray(fragment)\n                line = bytes(self._pending)',
    ),
    "finish ignores partial": (
        '        if self._pending:\n            self._poison()\n            raise IncompleteRecordError("stream ended inside an NDJSON record")\n',
        '        if self._pending:\n            raise IncompleteRecordError("stream ended inside an NDJSON record")\n',
    ),
    "discard does not poison": ("        self._fail()\n        self._finished = True\n\n\ndef encode_record", "        self._finished = True\n\n\ndef encode_record"),
    "blank lines not skipped": ("                if not line.strip():\n                    continue\n", ""),
    "ensure_ascii on": ("ensure_ascii=False", "ensure_ascii=True"),
    "no failed-state lock": ('        if self._failed:\n            raise DecoderFailedError("decoder failed; discard the response and retry")\n        if self._finished:\n            raise ValueError("decoder is finished")', '        if self._finished:\n            raise ValueError("decoder is finished")'),
}
PROTOCOL_ENVELOPE = {
    "envelope: drop message_id from HMAC": ('        "message_id": message_id,\n', ""),
}
PROTOCOL_POLICY = {
    "policy: threshold equality uses >": (
        "return len(payload) >= self.threshold_bytes",
        "return len(payload) > self.threshold_bytes",
    ),
}
PROTOCOL_REASSEMBLER = {
    "manager: duplicate refreshes idle TTL": (
        "elif not duplicate:",
        "else:",
    ),
    "manager: TTL boundary is strict": (
        "if now - last_activity >= self.session_ttl_seconds",
        "if now - last_activity > self.session_ttl_seconds",
    ),
    "reassembler: remove message_id consistency check": (
        '        if self.message_id is not None and envelope.message_id != self.message_id:\n            raise ValueError("message_id cannot change during reassembly")\n',
        "",
    ),
    "reassembler: remove conflicting-duplicate rejection": (
        '            if existing != payload:\n                raise ValueError(f"conflicting duplicate chunk {sequence}")\n',
        "",
    ),
    "reassembler: remove post-completion rejection": (
        '        if self._completed:\n            raise ValueError(\n                "a Reassembler instance handles one message; create a new instance"\n            )\n\n',
        "",
    ),
    "reassembler: skip CRC check": (
        '        if checksum(payload) != envelope.checksum.lower():\n            emit_receiver_outcome(ReceiverOutcome.ENVELOPE_INTEGRITY_REJECTED)\n            raise ValueError(f"checksum mismatch on chunk {sequence}")\n',
        "",
    ),
    "manager: skip aggregate byte cap": (
        "        if (\n            active_memory_bytes + added_bytes + chunk_overhead_bytes\n            > self.max_total_bytes\n        ):\n",
        "        if False:\n",
    ),
    "manager: drop overhead from aggregate total": (
        "active_memory_bytes + added_bytes + chunk_overhead_bytes",
        "active_memory_bytes + added_bytes",
    ),
    "manager: overhead constant is zero": (
        "OVERHEAD_PER_CHUNK = 96",
        "OVERHEAD_PER_CHUNK = 0",
    ),
    "manager: charge identical duplicate overhead": (
        "chunk_overhead_bytes = 0 if duplicate else OVERHEAD_PER_CHUNK",
        "chunk_overhead_bytes = OVERHEAD_PER_CHUNK",
    ),
    "manager: skip overhead for zero-byte chunk": (
        "chunk_overhead_bytes = 0 if duplicate else OVERHEAD_PER_CHUNK",
        "chunk_overhead_bytes = 0 if duplicate or not added_bytes else OVERHEAD_PER_CHUNK",
    ),
    "manager: retain completed session overhead": (
        "            if session.reassembler.completed:\n                self.sessions.pop(envelope.message_id, None)\n                self._session_activity.pop(envelope.message_id, None)\n",
        "            if session.reassembler.completed:\n                self._session_activity.pop(envelope.message_id, None)\n",
    ),
    "reassembler: double-count identical duplicate": (
        "            return envelope, payload, 0, True\n",
        "            return envelope, payload, len(payload), True\n",
    ),
    "receiver: skip session-cap outcome": (
        "            emit_receiver_outcome(ReceiverOutcome.SESSION_CAP_REJECTED)\n",
        "",
    ),
    "receiver: wrong outcome for bad authentication tag": (
        "emit_receiver_outcome(ReceiverOutcome.AUTHENTICATION_REJECTED)",
        "emit_receiver_outcome(ReceiverOutcome.ENVELOPE_INTEGRITY_REJECTED)",
    ),
    "receiver: report eviction for tombstoned replay": (
        "            raise ValueError(\"message_id is tombstoned; replay rejected\")\n",
        "            emit_receiver_outcome(ReceiverOutcome.TOMBSTONE_EVICTED)\n            raise ValueError(\"message_id is tombstoned; replay rejected\")\n",
    ),
}
PROTOCOL_KEY = {
    "key: remove 16-byte minimum": (
        "or len(authentication_key) < MIN_AUTHENTICATION_KEY_BYTES",
        "or not authentication_key",
    ),
}
NDJSON_STRICT = {
    "ndjson: poison outcome for rejected non-bytes input": (
        '        if not isinstance(data, bytes):\n            raise TypeError("data must be bytes")\n',
        '        if not isinstance(data, bytes):\n            emit_receiver_outcome(ReceiverOutcome.NDJSON_DECODER_POISONED)\n            raise TypeError("data must be bytes")\n',
    ),
    "ndjson: accept duplicate object names": (
        '        if key in result:\n            raise NDJSONError(f"duplicate JSON object name: {key!r}")\n',
        '        if False:\n            raise NDJSONError(f"duplicate JSON object name: {key!r}")\n',
    ),
    "ndjson: accept nonstandard constants": (
        "                    parse_constant=_reject_nonstandard_json_constant,\n",
        "",
    ),
    "ndjson: leak RecursionError": (
        '        except RecursionError as error:\n            self._poison()\n            raise NDJSONError("JSON nesting exceeds decoder capacity") from error\n',
        '        except RecursionError:\n            self._poison()\n            raise\n',
    ),
}
RECEIVER_OUTCOMES = {
    "receiver outcomes: guard removed": (
        "    try:\n        sink(ReceiverOutcomeEvent(outcome).as_dict())\n    except Exception:\n        pass\n",
        "    sink(ReceiverOutcomeEvent(outcome).as_dict())\n",
    ),
    "receiver outcomes: guard widened to BaseException": (
        "    except Exception:\n",
        "    except BaseException:\n",
    ),
}
CRM_APPROVALS = {
    "crm claim: ignore approved state": (
        "  AND state = 'APPROVED'\n  AND expires_at > ?;",
        "  AND expires_at > ?;",
    ),
    "crm claim: allow expiry boundary": (
        "  AND expires_at > ?;",
        "  AND expires_at >= ?;",
    ),
    "crm claim: drop expiry predicate": (
        "  AND expires_at > ?;",
        ";",
    ),
}
CRM_STORE = {
    "crm write: ignore approved record version": (
        "WHERE customer_id = ? AND field_name = ? AND record_version = ?;",
        "WHERE customer_id = ? AND field_name = ? AND (record_version = ? OR 1 = 1);",
    ),
    "crm write: skip execution ledger": (
        "            self.connection.execute(\n"
        "                \"\"\"INSERT INTO execution_ledger\n"
        "(execution_id, approval_id, customer_id, record_version, field_name,\n"
        " field_value, updated_at)\n"
        "VALUES (?, ?, ?, ?, ?, ?, ?);\"\"\",\n"
        "                (\n"
        "                    execution_id,\n"
        "                    approval_id,\n"
        "                    customer_id,\n"
        "                    record.record_version,\n"
        "                    field_name,\n"
        "                    proposed_value,\n"
        "                    at,\n"
        "                ),\n"
        "            )\n",
        "",
    ),
}
CRM_IDENTITY = {
    "crm identity: ignore scheduled revocation": (
        "identity.revoked_at is not None and current >= identity.revoked_at",
        "identity.revoked_at is not None and False",
    ),
}
CRM_POLICY_SNAPSHOT = {
    "crm policy hash: hash only rules": (


        "    payload = policy_snapshot_payload(\n"
        "        action=action,\n"
        "        requester_grant=requester_grant,\n"
        "        reviewer_grant=reviewer_grant,\n"
        "        rules=rules,\n"
        "        aggregation_constraints=aggregation_constraints,\n"
        "    )\n",
        "    payload = {\n"
        "        \"rules\": [\n"
        "            {\"action\": rule.action, \"effect\": rule.effect, \"priority\": rule.priority}\n"
        "            for rule in rules\n"
        "        ]\n"
        "    }\n",
    ),
    "crm policy hash: ignore rule effect": (
        '"effect": rule.effect,',
        '"effect": "allow",',
    ),
    "crm policy hash: ignore aggregation reason": (
        '"reason": constraint.reason',
        '"reason": "ignored"',
    ),
}
CRM_EXECUTION = {
    "crm execute: ignore live identity scopes": (
        "if not requester_identity.allowed or not reviewer_identity.allowed:",
        "if False:",
    ),
    "crm execute: ignore approval expiry": (
        "if approval.expires_at <= at:",
        "if False:",
    ),
    "crm execute: ignore policy drift": (
        "if current_hash != approval.policy_hash:",
        "if False:",
    ),
    "crm review: change denial on audit failure": (
        '"rejected" if not approve else "unresolved",',
        '"unresolved",',
    ),
}
CRM_MUTATION_GROUPS = {
    "approvals_store.py": CRM_APPROVALS,
    "crm_store.py": CRM_STORE,
    "identity_provider.py": CRM_IDENTITY,
    "policy_snapshot.py": CRM_POLICY_SNAPSHOT,
    "execution_service.py": CRM_EXECUTION,
}
def classify_mutant_result(returncode: int | None, output: str) -> str:
    if returncode is None or returncode >= 2 or returncode == 5:
        return "harness error"
    if "ERROR collecting" in output or "ImportError" in output or "ModuleNotFoundError" in output:
        return "harness error"
    if returncode == 0:
        return "survived"
    if returncode == 1 and ("FAILED " in output or "ERROR " in output):
        return "killed"
    return "harness error"


def run_module(
    impl: Path,
    tests: Path,
    name: str,
    mutants: dict[str, tuple[str, str]],
    *,
    source_dir: Path | None = None,
    extra_tests: tuple[Path, ...] = (),
    support_files: tuple[Path, ...] = (),
    pytest_args: tuple[str, ...] = (),
) -> int:
    source_root = impl if source_dir is None else source_dir
    source = (source_root / name).read_text(encoding="utf-8").replace("\r\n", "\n")
    killed: list[str] = []
    survived: list[str] = []
    skipped: list[str] = []
    harness_errors: list[str] = []
    harness_reasons: dict[str, str] = {}
    killing_tests: dict[str, str] = {}
    for label, (old, new) in mutants.items():
        if source.count(old) != 1:
            skipped.append(label)
            continue
        work = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(tests, work / "tests")
            repo_root = Path.cwd()
            crm_prototype = repo_root / "prototypes" / "crm_operational_copilot"
            copied_crm_prototype = (
                work / "prototypes" / "crm_operational_copilot"
            )
            copied_crm_prototype.mkdir(parents=True, exist_ok=True)
            for prototype_file in crm_prototype.glob("*.py"):
                shutil.copy2(
                    prototype_file, copied_crm_prototype / prototype_file.name
                )
            scripts_dir = repo_root / "scripts"
            copied_scripts_dir = work / "scripts"
            copied_scripts_dir.mkdir(parents=True, exist_ok=True)
            crm_evidence_checker = scripts_dir / "check_crm_validation_evidence.py"
            if crm_evidence_checker.is_file():
                shutil.copy2(crm_evidence_checker, copied_scripts_dir)
            for config_name in ("pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"):
                config = repo_root / config_name
                if config.is_file():
                    shutil.copy2(config, work / config_name)
            test_paths = [str(work / "tests")]
            python_paths: list[str] = []
            copied_impl = work / impl
            if impl.is_dir() and copied_impl != work / "impl":
                shutil.copytree(impl, copied_impl, dirs_exist_ok=True)
                python_paths.append(str(copied_impl))
                shutil.copy2(
                    Path(__file__).resolve(), copied_impl / "mutation_check.py"
                )
            if source_dir is not None:
                copied_source_dir = work / source_dir
                shutil.copytree(source_dir, copied_source_dir, dirs_exist_ok=True)
                for support_file in support_files:
                    shutil.copy(source_dir / support_file, copied_source_dir / support_file)
                for index, extra_test in enumerate(extra_tests):
                    copied_test = extra_test.with_name(
                        f"mutation_extra_{index}_{extra_test.name}"
                    )
                    shutil.copy(
                        source_dir / extra_test,
                        copied_source_dir / copied_test,
                    )
                    test_paths.append(str(copied_source_dir / copied_test))
                python_paths.append(str(copied_source_dir))
                target = copied_source_dir / name
            else:
                target = copied_impl / name
            pytest_command = [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-x",
                "-p",
                "no:cacheprovider",
                "-m",
                "not slow",
                *test_paths,
                *pytest_args,
            ]
            baseline = subprocess.run(
                pytest_command,
                cwd=work,
                capture_output=True,
                text=True,
                env=os.environ | {"PYTHONPATH": os.pathsep.join(python_paths)},
                timeout=120,
            )
            if baseline.returncode != 0:
                harness_errors.append(label)
                harness_reasons[label] = (baseline.stdout + baseline.stderr)[-800:].strip()
                continue
            for cache_dir in work.rglob("__pycache__"):
                shutil.rmtree(cache_dir, ignore_errors=True)
            target.write_text(
                source.replace(old, new, 1),
                encoding="utf-8",
            )
            result = subprocess.run(
                pytest_command,
                cwd=work,
                capture_output=True,
                text=True,
                env=os.environ | {"PYTHONPATH": os.pathsep.join(python_paths)},
                timeout=120,
            )
            outcome = classify_mutant_result(
                result.returncode, result.stdout + result.stderr
            )
            if outcome == "survived":
                survived.append(label)
            elif outcome == "killed":
                killed.append(label)
                failure_lines = [
                    line
                    for line in (result.stdout + result.stderr).splitlines()
                    if line.startswith("FAILED ")
                ]
                if failure_lines:
                    killing_tests[label] = failure_lines[-1]
            else:
                harness_errors.append(label)
                harness_reasons[label] = (result.stdout + result.stderr)[-800:].strip()
        except subprocess.TimeoutExpired:
            harness_errors.append(label)
            harness_reasons[label] = "pytest subprocess timed out after 120 seconds"
        finally:
            shutil.rmtree(work, ignore_errors=True)
    total = len(mutants)
    applicable = total - len(skipped)
    print(
        f"{name}: applicable={applicable}/{total}, killed={len(killed)}, "
        f"survived={len(survived)}, not_applicable={len(skipped)}, "
        f"harness_errors={len(harness_errors)}"
    )
    for label in survived:
        print(f"   SURVIVED: {label}")
    for label in skipped:
        print(f"   NOT APPLICABLE (source changed): {label}")
    for label in harness_errors:
        print(f"   HARNESS ERROR: {label}")
        reason = harness_reasons.get(label, "")
        if reason:
            print(f"   HARNESS REASON: {label}: {reason}")
    for label, test in killing_tests.items():
        print(f"   KILLING TEST: {label}: {test}")
    return len(survived) + len(skipped) + len(harness_errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--impl", type=Path, default=Path("04-reference-implementation"))
    parser.add_argument("--tests", type=Path, default=Path("tests"))
    parser.add_argument("--workflow-deselect", action="append", default=[])
    parser.add_argument(
        "--crm-module",
        action="append",
        choices=tuple(CRM_MUTATION_GROUPS),
        help="Run only the selected CRM mutation module group (repeatable).",
    )
    args = parser.parse_args()

    workflow_dir = Path("prototypes/crm_operational_copilot")
    workflow_test = Path("test_approval_workflow.py")
    workflow_base = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(workflow_dir / workflow_test)],
        capture_output=True,
        text=True,
        env=os.environ | {"PYTHONPATH": os.pathsep.join([str(args.impl), str(workflow_dir)])},
    )
    if workflow_base.returncode != 0:
        print("Workflow baseline tests fail; fix them before mutation testing.\n" + workflow_base.stdout[-800:])
        raise SystemExit(2)

    base = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            str(args.tests),
        ],
        env=os.environ | {"PYTHONPATH": str(args.impl)},
        capture_output=True,
        text=True,
    )
    if base.returncode != 0:
        print("Baseline tests fail; fix them before mutation testing.\n" + base.stdout[-800:])
        raise SystemExit(2)

    failures = 0
    if args.crm_module is None:
        failures += run_module(args.impl, args.tests, "authority_policy.py", AUTH)
        failures += run_module(args.impl, args.tests, "ndjson_stream.py", NDJSON)
    protocol_dir = args.impl / "adaptive-response-filter"
    protocol_tests = tuple(
        Path(name)
        for name in (
            "test_chunker.py",
            "test_envelope.py",
            "test_reassembler.py",
            "test_reassembly_session.py",
            "test_receiver_observability.py",
        )
    )
    protocol_support = tuple(
        Path(name)
        for name in (
            "chunker.py",
            "filter.py",
            "middleware.py",
            "metrics.py",
            "policy.py",
            "reassembler.py",
            "envelope.py",
        )
    )
    if args.crm_module is None:
        failures += run_module(
            args.impl,
            args.tests,
            "envelope.py",
            PROTOCOL_ENVELOPE,
            source_dir=protocol_dir,
            extra_tests=protocol_tests,
            support_files=protocol_support,
        )
        failures += run_module(
            args.impl,
            args.tests,
            "policy.py",
            PROTOCOL_POLICY,
            source_dir=protocol_dir,
            extra_tests=protocol_tests,
            support_files=protocol_support,
        )
        failures += run_module(
            args.impl,
            args.tests,
            "reassembler.py",
            PROTOCOL_REASSEMBLER,
            source_dir=protocol_dir,
            extra_tests=protocol_tests,
            support_files=protocol_support,
        )
        failures += run_module(
            args.impl,
            args.tests,
            "envelope.py",
            PROTOCOL_KEY,
            source_dir=protocol_dir,
            extra_tests=protocol_tests,
            support_files=protocol_support,
        )
        failures += run_module(
            args.impl,
            args.tests,
            "ndjson_stream.py",
            NDJSON_STRICT,
        )
        failures += run_module(
            args.impl,
            protocol_dir,
            "receiver_outcomes.py",
            RECEIVER_OUTCOMES,
            pytest_args=("tests/test_receiver_observability.py",),
        )
        failures += run_module(
            args.impl,
            args.tests,
            "approval_workflow.py",
            WORKFLOW,
            source_dir=workflow_dir,
            extra_tests=(workflow_test,),
            support_files=(Path("crm_copilot.py"),),
            pytest_args=(
                ("-k", " and ".join(f"not {name}" for name in args.workflow_deselect))
                if args.workflow_deselect
                else ()
            ),
        )

    crm_dir = Path("prototypes/crm_operational_copilot")
    crm_test_files = (
        Path("test_approvals_store.py"),
        Path("test_crm_store.py"),
        Path("test_crm_failure_recovery.py"),
        Path("test_execution_service.py"),
        Path("test_identity_provider.py"),
        Path("test_policy_snapshot.py"),
    )
    selected_crm_modules = args.crm_module or tuple(CRM_MUTATION_GROUPS)
    for module_name in selected_crm_modules:
        failures += run_module(
            args.impl,
            args.tests,
            module_name,
            CRM_MUTATION_GROUPS[module_name],
            source_dir=crm_dir,
            extra_tests=crm_test_files,
        )
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
