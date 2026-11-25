"""Verify staged external artifacts against the tracked manifest (R-02-14).

    py tools/verify_models.py [--require-staged]

Checks every manifest entry whose payload is present: the bytes on disk
must hash to the pinned digest. Missing payloads are reported, never
treated as matching. Exit 1 on any digest mismatch (or on missing payloads
with --require-staged); exit 0 otherwise.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "src" / "models"
MANIFEST = MODELS / "manifest.json"


def digest_of(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(manifest_path=MANIFEST, *, require_staged=False):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    base = Path(manifest_path).resolve().parent
    report = []
    for artifact in manifest["artifacts"]:
        location = base / artifact["location"]
        entry = dict(id=artifact["id"], location=artifact["location"],
                     staged=location.is_file(), digest_match=None)
        if entry["staged"]:
            entry["digest_match"] = digest_of(location) == artifact["digest_sha256"]
        elif require_staged:
            entry["digest_match"] = False
        report.append(entry)
    return report


def main(argv=None, manifest_path=MANIFEST):
    args = sys.argv[1:] if argv is None else argv
    report = verify_manifest(manifest_path, require_staged="--require-staged" in args)
    for entry in report:
        print(f"{entry['id']}: staged={entry['staged']} digest_match={entry['digest_match']}")
    mismatched = [e for e in report if e["digest_match"] is False]
    if mismatched:
        raise SystemExit(f"digest mismatch for {[e['id'] for e in mismatched]}; refusing")
    return report


if __name__ == "__main__":
    main()
