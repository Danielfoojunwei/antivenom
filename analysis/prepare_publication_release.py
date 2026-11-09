"""Build a deterministic PRIVATE publication review candidate, without models.

No upload or publication occurs. External datasets/weights, reviewer sheets,
private keys, logs and original model checkpoints are deliberately excluded.
The archive reproduces paper tables; full scientific replay needs separately
acquired data and the preserved full local experiment records.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (2026, 11, 4, 0, 0, 0)

README = """# ANTIVENOM publication review candidate

PRIVATE REVIEW CANDIDATE. Not a submitted, accepted or public paper/release.

Start with paper/manuscript.md and docs/PUBLICATION_READINESS.md. The PDF is
output/pdf/antivenom_manuscript_draft.pdf. This package distinguishes completed
local evidence from the untested fresh representation claim. It contains
no native MemMorph results and no completed independent human ratings.

Rebuild evidence tables without models/network, using Python 3.12+:

    python paper/generate_tables.py

That is evidence-table regeneration, not independent scientific replication.
The exact empty-history control's generated answers are included. Full
raw contexts/checkpoints and external data/weights remain in the original
local checkout; their identities are indexed, not copied. Follow the pinned
protocols and THIRD_PARTY_NOTICES.md to obtain external inputs. Do not launch
old completed experiment queues from a review checkout. The new confirmation
study has zero fresh certified local families and no enabled inference run.

MANIFEST.json lists every archive member hash. Verify before extracting:

    python analysis/prepare_publication_release.py --verify ARCHIVE.zip

Human review: use publication_v2 in the full local checkout. Individual
reviewer sheets, private method mappings, attestations and adjudication are
excluded to protect blinding and reviewer identities. V1's adjudication
overwrite defect was found and fixed in separately preserved V2 before any
human work. Historical protocols are retained and may describe superseded
plans; the readiness index and manuscript identify the current scope.

Before public release: author review/consent, authorship/affiliations, an
explicit license for original project code, privacy/path review and third-
party redistribution review remain required. Original license texts and
notices are preserved; this archive invents no project license. Do not infer
permission or publication readiness from the existence of this ZIP.

All work before the 6-8 November 2026 hackathon sprint is preexisting work.
No public upload, submission, outreach or external compute was performed.
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dumps(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False).encode() + b"\n"


def allowed_member(name):
    path = Path(name)
    return (not path.is_absolute() and ".." not in path.parts
        and all(not part.startswith(".") for part in path.parts)
        and not any(part.lower() in {"private_admin_only", "checkpoints", "external", "cache"}
                    for part in path.parts)
        and path.suffix.lower() not in {".pem", ".key", ".env", ".log"})


def collect(root=ROOT):
    root = Path(root).resolve()
    files = set()
    for name in ("README.md", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "uv.lock", "data/README.md",
                 "docs/PUBLICATION_READINESS.md", "output/pdf/antivenom_manuscript_draft.pdf"):
        files.add(name)
    for directory, pattern in (("src", "*.py"), ("experiments", "*.py"),
            ("analysis", "*.py"), ("tests", "*.py"), ("docs", "*.md"), ("paper", "*")):
        files.update(p.relative_to(root).as_posix() for p in (root / directory).rglob(pattern)
            if p.is_file() and "__pycache__" not in p.parts)
    files.add("experiments/memmorph_alignment_plan.json")
    evidence = json.loads((root / "paper/evidence_index.json").read_text())
    files.update(evidence["sources"])
    files.update(p.relative_to(root).as_posix() for p in (root / "results").glob("*manifest*.json"))
    files.update({"results/memform_drop_all_control_v1.jsonl", "results/memform_drop_all_plan_v1.json",
        "results/memform_drop_all_control_v1_integrity.json", "results/publication_power_v1.json",
        "results/publication_confirmation_readiness_v1.json",
        "results/provenance/publication_readiness_v1_pre_review.json",
        "results/memmorph_alignment_status.json", "results/publication_preparation_verification_v1.json",
        "data/validation/publication_v2/review_status.json",
        "data/validation/publication_v2/verification.json",
        "data/validation/publication_v2/review_manifest.json"})
    result = {"PUBLICATION_REVIEW_README.md": README.encode()}
    for name in sorted(files):
        if not allowed_member(name):
            raise ValueError("Excluded or unsafe candidate path: " + name)
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Symlink or outside input: " + name)
        if not path.is_file():
            raise FileNotFoundError("Required candidate input missing: " + name)
        result[name] = path.read_bytes()
    # Preserve identities for complete local raw replay without redistributing
    # benchmark text, source contexts or reviewer information in this candidate.
    raw_names = ["results/incident_memform.jsonl", "results/incident_swarm.jsonl",
        "results/swarm_clean_reference.jsonl", "results/extraction_failure_events.jsonl",
        "results/provenance/e37_original_first70.jsonl"]
    raw_index = {}
    for name in raw_names:
        path = root / name
        if path.is_file():
            raw_index[name] = {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size,
                "included": False, "reason": "source context/data redistribution review required"}
    result["LOCAL_RAW_RECORDS_INDEX.json"] = dumps(raw_index)
    return result


def build_bytes(members):
    if any(not allowed_member(name) or name == "MANIFEST.json" for name in members):
        raise ValueError("Invalid or reserved archive member")
    manifest = {"schema": "antivenom.publication-review-candidate.v1",
        "status": "private_review_candidate_not_public_release",
        "scope": "paper/table reproducibility plus prepared software; not full data replication",
        "members": {name: {"sha256": digest(data), "bytes": len(data)} for name, data in sorted(members.items())},
        "pending": ["fresh independent confirmation", "independent human ratings/adjudication",
            "authorship and consent", "original code license", "public privacy and redistribution review"],
        "new_model_calls": 0, "native_memmorph_cases": 0,
        "external_upload_or_submission": False}
    all_members = {**members, "MANIFEST.json": dumps(manifest)}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(all_members.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue(), manifest


def verify_bytes(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "MANIFEST.json" not in names:
            raise ValueError("Duplicate members or missing manifest")
        if any(not allowed_member(name) for name in names):
            raise ValueError("Unsafe archive member")
        manifest = json.loads(archive.read("MANIFEST.json"))
        if manifest.get("schema") != "antivenom.publication-review-candidate.v1":
            raise ValueError("Unknown manifest schema")
        if set(names) != set(manifest["members"]) | {"MANIFEST.json"}:
            raise ValueError("Archive has extra or missing members")
        for name, binding in manifest["members"].items():
            value = archive.read(name)
            if digest(value) != binding["sha256"] or len(value) != binding["bytes"]:
                raise ValueError("Archive member changed: " + name)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        manifest = verify_bytes(args.verify.read_bytes())
        print(json.dumps({"verified_members": len(manifest["members"]), "status": manifest["status"]}))
        return
    members = collect()
    data, manifest = build_bytes(members)
    verify_bytes(data)
    folder = ROOT / "output/publication"
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "antivenom_publication_review_v1.zip"
    if out.exists() and out.read_bytes() != data:
        raise ValueError("Frozen review candidate differs; preserve it and create a new version")
    out.write_bytes(data)
    sidecar = {"archive": out.name, "archive_sha256": digest(data), **manifest}
    (folder / "antivenom_publication_review_v1_manifest.json").write_bytes(dumps(sidecar))
    print(json.dumps({"archive": str(out), "sha256": digest(data),
        "members": len(members), "bytes": len(data), "status": manifest["status"]}, indent=2))


if __name__ == "__main__":
    main()
