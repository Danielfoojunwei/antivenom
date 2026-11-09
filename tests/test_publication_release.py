"""Archive integrity/privacy boundaries; no models or original inputs touched."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release", ROOT / "analysis/prepare_publication_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class PublicationReleaseTests(unittest.TestCase):
    def test_exact_deterministic_manifest_roundtrip(self):
        members = {"paper/manuscript.md": b"draft", "results/summary.json": b"{}"}
        data, manifest = release.build_bytes(members)
        self.assertEqual(data, release.build_bytes(dict(reversed(list(members.items()))))[0])
        self.assertEqual(release.verify_bytes(data), manifest)
        self.assertFalse(manifest["external_upload_or_submission"])

    def test_sensitive_and_traversal_paths_cannot_be_packed(self):
        for name in ("../secret", "/tmp/secret", ".env", "a/.env", "a/key.pem",
                "data/external/source.json", "results/checkpoints/item.json",
                "data/validation/PRIVATE_admin_only/key.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                release.build_bytes({name: b"sensitive"})

    def repack(self, original, replace=None, extra=None):
        buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as src, zipfile.ZipFile(buffer, "w") as dst:
            for name in src.namelist():
                dst.writestr(name, replace.get(name, src.read(name)) if replace else src.read(name))
            if extra:
                dst.writestr(*extra)
        return buffer.getvalue()

    def test_tampered_member_rejected_before_extraction(self):
        data, _ = release.build_bytes({"paper/draft.md": b"original"})
        with self.assertRaisesRegex(ValueError, "changed"):
            release.verify_bytes(self.repack(data, {"paper/draft.md": b"changed"}))

    def test_undeclared_member_rejected(self):
        data, _ = release.build_bytes({"paper/draft.md": b"original"})
        with self.assertRaisesRegex(ValueError, "extra or missing"):
            release.verify_bytes(self.repack(data, extra=("extra.txt", b"undeclared")))

    def test_duplicate_member_rejected(self):
        data, _ = release.build_bytes({"paper/draft.md": b"original"})
        with self.assertWarns(UserWarning):
            duplicate = self.repack(data, extra=("paper/draft.md", b"duplicate"))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            release.verify_bytes(duplicate)


if __name__ == "__main__":
    unittest.main()
