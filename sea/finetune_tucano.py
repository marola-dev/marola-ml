"""finetune_tucano: marola-gpt as a LoRA adapter on TucanoBR/Tucano-2b4, trained on marola's corpus.

    python3 sea/finetune_tucano.py [--steps 200] [--out sea/out-marola-gpt]
    python3 sea/finetune_tucano.py --self-test

The base is downloaded from Hugging Face at BASE_REVISION into its own cache and never changed:
only a LoRA adapter on the attention projections is trained, on the CPU, so it fits a
GitHub-hosted runner (4 cores, 16 GB). The pinned corpus (`just corpus-fetch`, read the way
sea/prepare_corpus.py reads it) is tokenized with Tucano's tokenizer and cut into blocks of
--block tokens; every tenth block is held out for validation. The adapter with the lowest
validation loss is kept in --out, with train_state.json beside it (sea/package.py reads both).
Needs torch, transformers and peft (sea/requirements.txt); the self-test needs none of them.
"""

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare_corpus import CORPUS, read_corpus  # noqa: E402

# Apache-2.0 (sea/LICENSE-Tucano-2b4). The revision is pinned so a release names the exact base.
BASE = "TucanoBR/Tucano-2b4"
BASE_REVISION = "b8def49a1931508a7cedc1f3fd6ff163515b0983"
OUT = HERE / "out-marola-gpt"
LORA = {"r": 8, "lora_alpha": 16, "lora_dropout": 0.05, "target_modules": ["q_proj", "v_proj"]}


def blocks(ids: list[int], size: int) -> tuple[list[list[int]], list[list[int]]]:
    """The token ids cut into full blocks; every tenth block (the 10th, 20th, ...) is validation."""
    chunks = [ids[i : i + size] for i in range(0, len(ids) - size + 1, size)]
    if len(chunks) < 2:
        raise SystemExit(f"finetune_tucano: {len(ids)} tokens make fewer than two blocks of {size}")
    val = [c for i, c in enumerate(chunks) if i % 10 == 9] or chunks[-1:]
    train = [c for i, c in enumerate(chunks) if i % 10 != 9 and c is not val[-1]]
    return train, val


def train(steps: int, block: int, lr: float, eval_every: int, out: Path, corpus: Path) -> dict:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(1337)
    tok = AutoTokenizer.from_pretrained(BASE, revision=BASE_REVISION)
    ids = tok(read_corpus(corpus), add_special_tokens=False)["input_ids"]
    tr, va = blocks(ids, block)
    model = AutoModelForCausalLM.from_pretrained(BASE, revision=BASE_REVISION, dtype=torch.bfloat16)
    model = get_peft_model(model, LoraConfig(task_type="CAUSAL_LM", **LORA))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)

    def loss_of(batch: list[list[int]]) -> torch.Tensor:
        x = torch.tensor(batch)
        return model(input_ids=x, labels=x).loss

    def val_loss() -> float:
        model.eval()
        with torch.no_grad():
            v = sum(loss_of([b]).item() for b in va) / len(va)
        model.train()
        return v

    best, best_step, t0 = val_loss(), 0, time.time()
    print(
        f"finetune_tucano: {len(ids)} tokens, {len(tr)}+{len(va)} blocks of {block}, "
        f"{trainable:,} trainable; step 0 val {best:.4f}",
        file=sys.stderr,
    )
    model.train()
    for step in range(1, steps + 1):
        loss = loss_of([tr[(step - 1) % len(tr)]])
        loss.backward()
        opt.step()
        opt.zero_grad()
        if step % eval_every == 0 or step == steps:
            v = val_loss()
            print(
                f"  step {step}: train {loss.item():.4f}, val {v:.4f} ({time.time() - t0:.0f}s)",
                file=sys.stderr,
            )
            if v < best:
                best, best_step = v, step
                model.save_pretrained(out)
    if best_step == 0:
        model.save_pretrained(out)  # no step beat the base; the release still needs an adapter
    state = {
        "base": BASE,
        "base_revision": BASE_REVISION,
        "lora": LORA,
        "steps": steps,
        "best_step": best_step,
        "best_val_loss": round(best, 4),
        "tokens": len(ids),
        "block": block,
        "trainable_params": trainable,
        "seconds": round(time.time() - t0),
    }
    (out / "train_state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def self_test() -> int:
    fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal fails
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        fails += 0 if cond else 1

    tr, va = blocks(list(range(205)), 10)
    ok(len(tr) + len(va) == 20 and all(len(b) == 10 for b in tr + va), "only full blocks are kept")
    ok(va == [list(range(90, 100)), list(range(190, 200))], "every tenth block is validation")
    ok(not any(b in tr for b in va), "no block is in both splits")
    tr, va = blocks(list(range(30)), 10)
    ok(len(va) == 1 and va[0] not in tr, "a short corpus still holds one block out")
    try:
        blocks(list(range(15)), 10)
        ok(False, "fewer than two blocks is refused")
    except SystemExit:
        ok(True, "fewer than two blocks is refused")
    ok(len(BASE_REVISION) == 40, "the base is pinned to a commit")
    print("finetune_tucano self-test: " + ("ok" if not fails else f"{fails} failure(s)"))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--block", type=int, default=128, help="tokens per training block")
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--eval-every", type=int, default=25)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    s = train(a.steps, a.block, a.lr, a.eval_every, a.out, a.corpus)
    print(
        f"finetune_tucano: best val loss {s['best_val_loss']} at step {s['best_step']} "
        f"of {s['steps']} ({s['seconds']}s) -> {a.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
