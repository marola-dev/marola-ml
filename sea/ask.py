"""ask: give the published marola-gpt a prompt, and print how it continues it.

    python3 sea/ask.py "Rip currents"                       # the latest release on Hugging Face
    python3 sea/ask.py "Rip currents" --version 0.0.1 --tokens 300 --temperature 0.8 --seed 1
    python3 sea/ask.py --self-test

marola-gpt is a character-level model, not a chat model: it continues the text it is given, one
character at a time. This downloads a release from h0ffmann/marola-gpt (sea/publish_hf.py's REPO)
at its tag v<version>, into Hugging Face's own cache (~/.cache/huggingface, or HF_HOME), so nothing
has to exist in this repository first and a second call does not download again. Every file is
checked against the release's CHECKSUMS before the weights are loaded. The model is nanoGPT's
(sea/nanogpt/model.py), run on the CPU. Needs torch and huggingface_hub (sea/requirements.txt).
"""

import argparse
import contextlib
import os
import pickle
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from publish_hf import FILES, REPO, verify  # noqa: E402


def latest(tags: list[str]) -> str | None:
    """The highest X.Y.Z among tags named vX.Y.Z, or None."""
    versions = [t[1:] for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
    return max(versions, key=lambda v: tuple(int(x) for x in v.split(".")), default=None)


def encode(prompt: str, stoi: dict) -> list[int]:
    """The prompt as character ids; a character the model never saw is refused, by name."""
    unknown = sorted({c for c in prompt if c not in stoi})
    if unknown:
        raise SystemExit(
            f"ask: the model does not know {''.join(unknown)!r}: it learned only the characters of "
            f"its corpus ({len(stoi)}); write the prompt without them"
        )
    if not prompt:
        raise SystemExit("ask: give a prompt to continue")
    return [stoi[c] for c in prompt]


def download(repo: str, version: str | None) -> tuple[Path, str]:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from huggingface_hub import HfApi, snapshot_download

    if version is None:
        version = latest([t.name for t in HfApi().list_repo_refs(repo).tags])
        if version is None:
            raise SystemExit(f"ask: {repo} has no vX.Y.Z tag yet")
    path = Path(snapshot_download(repo_id=repo, revision=f"v{version}", allow_patterns=list(FILES)))
    errors = verify(path)
    if errors:
        raise SystemExit(f"ask: {repo} v{version}: " + "; ".join(errors))
    return path, version


def generate(
    release: Path, prompt: str, tokens: int, temperature: float, top_k: int, seed: int
) -> str:
    import torch

    sys.path.insert(0, str(HERE / "nanogpt"))
    from model import GPT, GPTConfig

    ckpt = torch.load(release / "model.pt", map_location="cpu", weights_only=False)
    with contextlib.redirect_stdout(sys.stderr):  # nanoGPT prints its parameter count
        model = GPT(GPTConfig(**ckpt["model_args"]))
    state = {k.removeprefix("_orig_mod."): v for k, v in ckpt["model"].items()}
    model.load_state_dict(state)
    model.eval()
    with open(release / "meta.pkl", "rb") as f:
        meta = pickle.load(f)
    torch.manual_seed(seed)
    idx = torch.tensor([encode(prompt, meta["stoi"])], dtype=torch.long)
    with torch.no_grad():
        out = model.generate(idx, tokens, temperature=temperature, top_k=top_k)
    return "".join(meta["itos"][i] for i in out[0].tolist())


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
    stoi = {"a": 0, "r": 1, " ": 2}
    ok(encode("ar a", stoi) == [0, 1, 2, 0], "a prompt becomes character ids")
    for bad, label in (
        ("arz", "an unknown character is refused"),
        ("", "an empty prompt is refused"),
    ):
        try:
            encode(bad, stoi)
            ok(False, label)
        except SystemExit:
            ok(True, label)
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
    ap.add_argument("--tokens", type=int, default=200, help="characters to add")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.prompt is None:
        ap.error('give a prompt: python3 sea/ask.py "Rip currents"')
    release, version = download(a.repo, a.version)
    print(f"ask: marola-gpt {version} from huggingface.co/{a.repo}", file=sys.stderr)
    print(generate(release, a.prompt, a.tokens, a.temperature, a.top_k, a.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
