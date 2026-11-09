"""Audit native saved inputs and pin preparation software; never run a model.

Exit 2 means native artifacts or review are missing/invalid. Exit 0 means only
the saved-fixture contract was reviewed and verified, NOT empirical efficacy.
No native harness, downloaded script, tool or attack generator is executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from antivenom.memmorph_eval import ContractError, validate_fixture_bundle, verify_input_files

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("native_bundle.json", "native_harness_manifest.json", "reference_baseline.json", "provenance_review.json")
SOURCES = (
    "docs/MEMMORPH_ALIGNMENT_PROTOCOL.md", "experiments/memmorph_alignment_plan.json",
    "experiments/prepare_memmorph.py", "analysis/memmorph_score.py",
    "src/antivenom/memmorph_eval.py", "src/antivenom/tool_policy_signature.py",
    "tests/test_memmorph_eval.py", "tests/test_tool_policy_signature.py",
    "tests/test_memmorph_readiness.py",
)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def inspect_artifacts(native_dir: Path) -> dict:
    """Review declarations and immutable bindings, not author authenticity."""
    report = {
        "status": "blocked_native_artifacts_missing", "native_empirical_validation": False,
        "model_calls": 0, "native_harness_executed": False,
        "missing": [name for name in REQUIRED if not (native_dir / name).is_file()],
        "errors": [], "verified_files": {},
        "provenance_note": "Review declarations need independent human verification; flags alone do not authenticate an author release.",
    }
    if report["missing"]:
        return report
    try:
        bundle = validate_fixture_bundle(json.loads((native_dir / "native_bundle.json").read_text()))
        report["verified_files"] = verify_input_files(bundle, native_dir)
        review = json.loads((native_dir / "provenance_review.json").read_text())
        for name in ("reviewer", "reviewed_utc", "author_linkage_evidence", "native_prompt_and_scorer_review",
                     "campaign_independence_review"):
            if not isinstance(review.get(name), str) or not review[name].strip():
                raise ContractError(f"Missing independent review field: {name}")
        if review.get("classification") not in {"author_verified_native_export", "author_validated_local_port"}:
            raise ContractError("Review must distinguish native export from author-validated local port")
        expected_kind = {"author_verified_native_export": "author_verified_native",
                         "author_validated_local_port": "author_validated_local_port"}[review["classification"]]
        if bundle["provenance"]["kind"] != expected_kind:
            raise ContractError("Review classification does not match bundle provenance kind")
        for name in REQUIRED[:-1]:
            if review.get("bound_files", {}).get(name) != sha_file(native_dir / name):
                raise ContractError(f"Review is not bound to exact input: {name}")
        for name in ("native_harness_manifest.json", "reference_baseline.json"):
            if not isinstance(json.loads((native_dir / name).read_text()), dict):
                raise ContractError(f"{name} must be a reviewed JSON object")
        report.update(status="saved_contract_verified_native_integration_pending",
                      classification=review["classification"],
                      planned_campaigns=len(bundle["campaigns"]),
                      planned_tasks=sum(len(c["cases"]) for c in bundle["campaigns"]))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        report.update(status="blocked_native_artifacts_invalid")
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    return report


def freeze_software(path: Path, root: Path = ROOT) -> dict:
    payload = {"scope": "Preparation software only; no native scientific execution freeze or efficacy result",
               "inputs": {name: sha_file(root / name) for name in SOURCES}}
    if path.exists():
        if json.loads(path.read_text()) != payload:
            raise ContractError("Preparation software changed after pinning; preserve old freeze and disclose a versioned amendment")
    else:
        save(path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-dir", type=Path, default=ROOT / "data/external/memmorph")
    parser.add_argument("--freeze-software", action="store_true")
    args = parser.parse_args()
    manifest = ROOT / "results/memmorph_alignment_software_manifest.json"
    if args.freeze_software or manifest.exists():
        freeze_software(manifest)
    report = inspect_artifacts(args.native_dir)
    report.update(checked_utc=datetime.now(timezone.utc).isoformat(),
                  native_directory=str(args.native_dir),
                  plan="experiments/memmorph_alignment_plan.json",
                  software_manifest=str(manifest) if manifest.exists() else None,
                  empirical_result="No native MemMorph result; no cure or clean-utility claim")
    save(ROOT / "results/memmorph_alignment_status.json", report)
    print(json.dumps(report, indent=2))
    return 2 if report["status"].startswith("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
