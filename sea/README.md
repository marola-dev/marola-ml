# sea: marola-gpt

marola-gpt, marola's own model, is built here. From 0.1.0 it is a LoRA adapter that marola trains
on its own corpus notes, on top of [TucanoBR/Tucano-2b4](https://huggingface.co/TucanoBR/Tucano-2b4)
(Apache-2.0, pinned by revision in [`finetune_tucano.py`](finetune_tucano.py)); the base is
downloaded unchanged and never redistributed ([ADR 0004](../docs/adr/0004-marola-gpt-sobre-tucano.md)).
Releases 0.0.x were a character-level GPT trained from random weights with the code of
[karpathy/nanoGPT](https://github.com/karpathy/nanoGPT), copied as is into [`nanogpt/`](nanogpt/)
on 14 October 2026 ([ADR 0001](../docs/adr/0001-marola-sea-from-nanogpt.md)); that code stays here,
under Andrej Karpathy's MIT License ([`nanogpt/LICENSE`](nanogpt/LICENSE)).

## Build it

```bash
# a Python with sea/requirements.txt installed (CPU: torch from download.pytorch.org/whl/cpu)
export SEA_PYTHON=/path/to/python
just marola-gpt-train                  # the pinned corpus -> a LoRA adapter in out-marola-gpt/ (--steps, --lr)
just marola-gpt-sample "A água-viva"   # text from that adapter on Tucano-2b4
just marola-gpt-package 0.1.0          # release/marola-gpt-0.1.0/: adapter, LICENSE, README.md, CHECKSUMS
just marola-gpt-publish 0.1.0          # a dry run; --yes uploads to huggingface.co/h0ffmann/marola-gpt (public)
```

The first run, 15 October 2026, on a 4-core, 16 GB cloud CPU (torch 2.14.1, transformers 5.20.0,
peft 0.21.2): the corpus at v0.1.0 is 5 005 Tucano tokens, 36 training and 3 validation blocks of
128. 200 steps took 284 s; the validation loss fell from 3.1701 (the base alone) to 3.0201 at step
75, then rose while the training loss kept falling: the adapter memorises a corpus this small.
The adapter is 6 402 376 bytes. Its text is fluent Portuguese with no hold on the facts.

## What is here

| Path | Whose | What |
|---|---|---|
| `nanogpt/` | Andrej Karpathy's, MIT | nanoGPT at `3adf61e154c3`, each file with a provenance header; listed in [`FORK.tsv`](FORK.tsv) |
| `finetune_tucano.py` | marola's | the LoRA training on Tucano-2b4, and the base's pinned revision |
| `LICENSE-Tucano-2b4` | Tucano's, Apache-2.0 | copied byte for byte from TucanoBR/Tucano-2b4; every release carries it |
| `ask.py` | marola's | a prompt continued by a release, or by a local adapter |
| `prepare_corpus.py` | marola's | reads the corpus notes; also nanoGPT's character-level dataset (0.0.x) |
| `config/train_marola_gpt.py` | marola's | nanoGPT's training settings (0.0.x) |
| `package.py` | marola's | one release: adapter, licence, model card, checksums |
| `publish_hf.py` | marola's | the upload to Hugging Face, a dry run unless `--yes` |
| `fork_check.py` | marola's | refuses a copied file without its header, and an `as-is` file that changed |
| `requirements.txt` | marola's | what the LoRA training, ask, nanoGPT's scripts and the upload import |

When marola changes a copied file, its row in `FORK.tsv` says `edited`; the provenance header and
the MIT notice stay. `just quality` runs `fork_check.py`.

## Credits

- **Nicholas Kluge Corrêa, Aniket Sen, Sophia Falk and Shiza Fatimah**, for Tucano (Apache-2.0),
  marola-gpt's base from 0.1.0.
- **Andrej Karpathy**, for nanoGPT (MIT), the code marola-gpt 0.0.x was built with.
- **Fabio Akita** ([@akitaonrails](https://github.com/akitaonrails)), whose
  [microgpt](https://github.com/akitaonrails/microgpt) showed the path: a GPT trained from random
  weights on one consumer GPU, measured honestly. No code of microgpt is here: on 14 October 2026
  it had no licence, so it was read, not copied (marola-ml#48, marola-site#146).
