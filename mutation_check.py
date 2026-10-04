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
    "agg: skip per-action checks": ('        if decision.effect == "deny":\n            return decision\n\n    for constraint', "        pass\n\n    for constraint"),
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
    "session: refer becomes allow": ('    return decision\n', '    return Decision("allow", "session allowed")\n'),
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
    "workflow: ignore referral handling": ('        if decision.effect == "refer":\n', '        if False:\n'),
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
    "no poison on error": ("        except Exception:\n            self._fail()\n            raise", "        except Exception:\n            raise"),
    "feed ignores failed flag": ('        if self._failed:\n            raise DecoderFailedError("decoder failed; discard the response and retry")\n        if self._finished:\n            raise ValueError("decoder is finished")', '        if self._finished:\n            raise ValueError("decoder is finished")'),
    "finish ignores failed flag": ('        if self._failed:\n            raise DecoderFailedError("decoder failed; discard the response and retry")\n        if self._finished:\n            return', "        if self._finished:\n            return"),
    "no max when no newline": ('                    if len(self._pending) > self._max:\n                        raise RecordTooLargeError("record exceeds size limit")\n', ""),
    "no max on complete record": ('                if delimiter > self._max:\n                    raise RecordTooLargeError("record exceeds size limit")\n', ""),
    "limit off by one (>=)": ("                    if len(self._pending) > self._max:", "                    if len(self._pending) >= self._max:"),
    "accept non-object": ('                if not isinstance(value, dict):\n                    raise NDJSONError("NDJSON records must be JSON objects")\n', ""),
    "decode errors=ignore": ('line.decode("utf-8")', 'line.decode("utf-8", errors="ignore")'),
    "drop pending between feeds": ("self._pending.extend(data)", "self._pending = bytearray(data)"),
    "finish ignores partial": ('        if self._pending:\n            self._fail()\n            raise IncompleteRecordError("stream ended inside an NDJSON record")\n', "        pass\n"),
    "discard does not poison": ("        self._fail()\n        self._finished = True\n\n\ndef encode_record", "        self._finished = True\n\n\ndef encode_record"),
    "blank lines not skipped": ("                if not line.strip():\n                    continue\n", ""),
    "ensure_ascii on": ("ensure_ascii=False", "ensure_ascii=True"),
    "no failed-state lock": ('        if self._failed:\n            raise DecoderFailedError("decoder failed; discard the response and retry")\n        if self._finished:\n            raise ValueError("decoder is finished")', '        if self._finished:\n            raise ValueError("decoder is finished")'),
}


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
    for label, (old, new) in mutants.items():
        if old not in source:
            skipped.append(label)
            continue
        work = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(tests, work / "tests")
            (work / "impl").mkdir()
            for sibling in ("authority_policy.py", "ndjson_stream.py"):
                if (impl / sibling).exists():
                    shutil.copy(impl / sibling, work / "impl" / sibling)
            test_paths = [str(work / "tests")]
            python_paths = [str(work / "impl")]
            if source_dir is not None:
                copied_source_dir = work / source_dir
                copied_source_dir.mkdir(parents=True, exist_ok=True)
                for support_file in support_files:
                    shutil.copy(source_dir / support_file, copied_source_dir / support_file)
                for extra_test in extra_tests:
                    shutil.copy(source_dir / extra_test, copied_source_dir / extra_test)
                    test_paths.append(str(copied_source_dir / extra_test))
                python_paths.append(str(copied_source_dir))
                target = copied_source_dir / name
            else:
                target = work / "impl" / name
            target.write_text(
                source.replace(old, new, 1),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-x",
                    "-p",
                    "no:cacheprovider",
                    *test_paths,
                    *pytest_args,
                ],
                cwd=work,
                capture_output=True,
                text=True,
                env=os.environ | {"PYTHONPATH": os.pathsep.join(python_paths)},
            )
            if result.returncode != 0:
                killed.append(label)
            else:
                survived.append(label)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    total = len(mutants) - len(skipped)
    print(f"{name}: killed {len(killed)}/{total}")
    for label in survived:
        print(f"   SURVIVED: {label}")
    for label in skipped:
        print(f"   NOT APPLICABLE (source changed): {label}")
    return len(survived)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--impl", type=Path, default=Path("04-reference-implementation"))
    parser.add_argument("--tests", type=Path, default=Path("tests"))
    parser.add_argument("--workflow-deselect", action="append", default=[])
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

    survivors = run_module(args.impl, args.tests, "authority_policy.py", AUTH)
    survivors += run_module(args.impl, args.tests, "ndjson_stream.py", NDJSON)
    survivors += run_module(
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
    raise SystemExit(1 if survivors else 0)


if __name__ == "__main__":
    main()
