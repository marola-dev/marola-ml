"""publish_hf: upload one packaged marola-gpt release to its Hugging Face model repository.

    python3 sea/publish_hf.py --version 0.1.0                # dry run: say what would be uploaded
    python3 sea/publish_hf.py --version 0.1.0 --yes          # upload (HF_TOKEN, or a prior login)
    python3 sea/publish_hf.py --self-test

The repository is h0ffmann/marola-gpt for now (the owner, 14 October 2026), created public when it
does not exist: marola-gpt is MIT, distributed openly (--private creates it private instead). The upload is one commit
named "marola-gpt <version>" and tagged v<version>; an upload cannot be taken back, so without
--yes nothing leaves this machine. CHECKSUMS is checked against the files before anything is sent.
"""

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASES = ROOT / "sea" / "release"
REPO = "h0ffmann/marola-gpt"
FILES = ("model.pt", "meta.pkl", "LICENSE", "README.md", "CHECKSUMS")


def verify(release: Path) -> list[str]:
    """What is wrong with a release directory: a missing file, or a sha256 that does not match."""
    errors = [f"{n} is missing" for n in FILES if not (release / n).exists()]
    if errors:
        return errors
    for line in (release / "CHECKSUMS").read_text(encoding="utf-8").splitlines():
        sha, name = line.split("  ", 1)
        if hashlib.sha256((release / name).read_bytes()).hexdigest() != sha:
            errors.append(f"{name} does not match CHECKSUMS")
    return errors


def publish(release: Path, repo: str, version: str, api, private: bool = False) -> str:
    api.create_repo(repo_id=repo, repo_type="model", private=private, exist_ok=True)
    info = api.upload_folder(
        folder_path=str(release),
        repo_id=repo,
        repo_type="model",
        commit_message=f"marola-gpt {version}",
    )
    api.create_tag(repo_id=repo, repo_type="model", tag=f"v{version}")
    return getattr(info, "commit_url", str(info))


def self_test() -> int:
    fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal fails
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        fails += 0 if cond else 1

    with tempfile.TemporaryDirectory() as tmp:
        r = Path(tmp)
        for n in FILES[:-1]:
            (r / n).write_text(n, encoding="utf-8")
        (r / "CHECKSUMS").write_text(
            "".join(f"{hashlib.sha256(n.encode()).hexdigest()}  {n}\n" for n in FILES[:-1]),
            encoding="utf-8",
        )
        ok(verify(r) == [], "a release whose files match CHECKSUMS passes")
        (r / "model.pt").write_text("changed", encoding="utf-8")
        ok(
            verify(r) == ["model.pt does not match CHECKSUMS"],
            "a changed file is refused before upload",
        )
        (r / "meta.pkl").unlink()
        ok("meta.pkl is missing" in verify(r), "a missing file is refused")

        calls = []

        class Api:
            def create_repo(self, **kw):
                calls.append(("create_repo", kw))

            def upload_folder(self, **kw):
                calls.append(("upload_folder", kw))
                return type("I", (), {"commit_url": "https://huggingface.co/x/commit/1"})()

            def create_tag(self, **kw):
                calls.append(("create_tag", kw))

        url = publish(r, REPO, "0.1.0", Api())
        ok(
            calls[0]
            == (
                "create_repo",
                {"repo_id": REPO, "repo_type": "model", "private": False, "exist_ok": True},
            ),
            "the repository is created public when it does not exist",
        )
        ok(
            calls[1][1]["commit_message"] == "marola-gpt 0.1.0" and calls[2][1]["tag"] == "v0.1.0",
            "one commit named after the version, tagged v<version>",
        )
        ok(url.endswith("/commit/1"), "the commit's address is returned")
        publish(r, REPO, "0.1.0", Api(), private=True)
        ok(calls[3][1]["private"] is True, "--private creates it private")
    print("publish_hf self-test: " + ("ok" if not fails else f"{fails} failure(s)"))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--version")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--yes", action="store_true", help="upload; without it, a dry run")
    ap.add_argument("--private", action="store_true", help="create the repository private")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.version:
        ap.error("--version X.Y.Z is required")
    release = RELEASES / f"marola-gpt-{a.version}"
    errors = verify(release)
    if errors:
        for e in errors:
            print(f"publish_hf: {release}: {e}", file=sys.stderr)
        return 1
    size = sum((release / n).stat().st_size for n in FILES)
    print(
        f"publish_hf: {release} ({size:,} bytes, {len(FILES)} files) -> huggingface.co/{a.repo}, {'private' if a.private else 'public'}"
    )
    if not a.yes:
        print("publish_hf: dry run; nothing was uploaded (add --yes to upload)")
        return 0
    from huggingface_hub import HfApi

    url = publish(
        release, a.repo, a.version, HfApi(token=os.environ.get("HF_TOKEN")), private=a.private
    )
    print(f"publish_hf: uploaded {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
