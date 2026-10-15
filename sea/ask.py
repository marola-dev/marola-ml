"""ask: give marola-gpt a prompt, and print how it continues it.

    python3 sea/ask.py "A água-viva"                        # the latest release on Hugging Face
    python3 sea/ask.py "A água-viva" --version 0.1.0 --tokens 120 --temperature 0.8 --seed 1
    python3 sea/ask.py "A água-viva" --adapter sea/out-marola-gpt   # a local adapter, not a release
    python3 sea/ask.py --self-test

marola-gpt is not a chat model: it continues the text it is given. A release on h0ffmann/marola-gpt
(sea/publish_hf.py's REPO) is a LoRA adapter; this downloads it at its tag v<version>, checks every
file against the release's CHECKSUMS, downloads the base (sea/finetune_tucano.py's BASE at
BASE_REVISION) and runs both on the CPU. Both land in Hugging Face's own cache
(~/.cache/huggingface, or HF_HOME), so a second call does not download again. Needs torch,
transformers, peft and huggingface_hub (sea/requirements.txt).
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from finetune_tucano import BASE, BASE_REVISION  # noqa: E402
from publish_hf import FILES, REPO, verify  # noqa: E402


def latest(tags: list[str]) -> str | None:
    """The highest X.Y.Z among tags named vX.Y.Z, or None."""
    versions = [t[1:] for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
    return max(versions, key=lambda v: tuple(int(x) for x in v.split(".")), default=None)


def download(repo: str, version: str | None) -> tuple[Path, str]:
    if version is not None and version.startswith("0.0."):
        raise SystemExit(f"ask: {version} is a nanoGPT release (0.0.x); this reads 0.1.0 and later")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from huggingface_hub import HfApi, snapshot_download

    if version is None:
        version = latest([t.name for t in HfApi().list_repo_refs(repo).tags])
        if version is None:
            raise SystemExit(f"ask: {repo} has no vX.Y.Z tag yet")
        if version.startswith("0.0."):
            raise SystemExit(f"ask: {repo}'s latest release, {version}, is a nanoGPT one (0.0.x)")
    path = Path(snapshot_download(repo_id=repo, revision=f"v{version}", allow_patterns=list(FILES)))
    errors = verify(path)
    if errors:
        raise SystemExit(f"ask: {repo} v{version}: " + "; ".join(errors))
    return path, version


def generate(
    adapter: Path, prompt: str, tokens: int, temperature: float, top_k: int, seed: int
) -> str:
    if not prompt:
        raise SystemExit("ask: give a prompt to continue")
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(BASE, revision=BASE_REVISION)
    base = AutoModelForCausalLM.from_pretrained(BASE, revision=BASE_REVISION, dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(base, str(adapter)).eval()
    torch.manual_seed(seed)
    ids = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **ids,
            max_new_tokens=tokens,
            do_sample=True,
            temperature=temperature,
            top_k=top_k,
            repetition_penalty=1.2,  # Tucano's card's own setting; without it short prompts loop
        )
    return tok.decode(out[0], skip_special_tokens=True)


def self_test() -> int:
    fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal fails
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        fails += 0 if cond else 1

    ok(
        latest(["v0.0.1", "v0.0.10", "v0.0.2", "main"]) == "0.0.10",
        "the latest tag is by number, not by text",
    )
    ok(latest(["main", "marola-gpt-v0.0.1"]) is None, "only vX.Y.Z tags count")
    try:
        download(REPO, "0.0.1")
        ok(False, "a nanoGPT release is refused before any download")
    except SystemExit as e:
        ok("nanoGPT" in str(e), "a nanoGPT release is refused before any download")
    try:
        generate(Path("."), "", 1, 1.0, 1, 1)
        ok(False, "an empty prompt is refused")
    except SystemExit:
        ok(True, "an empty prompt is refused")
    with tempfile.TemporaryDirectory() as tmp:
        ok(verify(Path(tmp)) != [], "a download missing its files is refused before loading")
    print("ask self-test: " + ("ok" if not fails else f"{fails} failure(s)"))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--version", help="X.Y.Z; default: the latest vX.Y.Z tag on Hugging Face")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--adapter", type=Path, help="a local adapter directory instead of a release")
    ap.add_argument("--tokens", type=int, default=120, help="tokens to add")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.prompt is None:
        ap.error('give a prompt: python3 sea/ask.py "A água-viva"')
    if a.adapter:
        adapter, label = a.adapter, str(a.adapter)
    else:
        adapter, version = download(a.repo, a.version)
        label = f"{version} from huggingface.co/{a.repo}"
    print(f"ask: marola-gpt {label}, on {BASE}", file=sys.stderr)
    print(generate(adapter, a.prompt, a.tokens, a.temperature, a.top_k, a.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
