# sea: marolaGPT, from nanoGPT

marolaGPT, marola's own model, is built here, and only here: a small GPT trained from random weights on marola's own
corpus notes, with the code of [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) copied as
is into [`nanogpt/`](nanogpt/) on 14 October 2026. Marola owns the weights it trains and every
change it makes; Andrej Karpathy keeps the copyright of the code he wrote, under the MIT License
that came with it ([`nanogpt/LICENSE`](nanogpt/LICENSE)). The decision and its reasons are
[ADR 0001](../docs/adr/0001-marola-sea-from-nanogpt.md); its name and its licence are
[ADR 0002](../docs/adr/0002-marolagpt-and-the-restricted-licence.md).

## Build it

```bash
# a Python with sea/requirements.txt installed (CPU: torch from download.pytorch.org/whl/cpu)
export SEA_PYTHON=/path/to/python
just marolagpt-prepare          # the pinned corpus -> nanogpt/data/marola_corpus/{train,val}.bin, meta.pkl
just marolagpt-train            # sea/config/train_marolagpt.py; --key=value overrides any setting
just marolagpt-sample           # text from the best checkpoint, nanogpt/out-marolagpt/ckpt.pt
just marolagpt-package 0.1.0    # release/marolaGPT-0.1.0/: model.pt, meta.pkl, LICENSE, README.md, CHECKSUMS
just marolagpt-publish 0.1.0    # a dry run; --yes uploads to huggingface.co/h0ffmann/marolaGPT (private)
```

The first run, 14 October 2026, on the owner's workstation CPU (torch 2.7.1): the corpus at
v0.1.0 is 15 080 characters with 87 distinct ones; 1 000 steps of a 0.80M-parameter model took
99.7 s, and the validation loss fell from the start to 2.485 at step 600, then rose while the
training loss kept falling: the model memorises a corpus this small. Its samples are word-shaped
noise. That is the honest start: more text, a larger model and a GPU come next.

## What is here

| Path | Whose | What |
|---|---|---|
| `nanogpt/` | Andrej Karpathy's, MIT | nanoGPT at `3adf61e154c3`, each file with a provenance header; listed in [`FORK.tsv`](FORK.tsv) |
| `prepare_corpus.py` | marola's | the corpus notes as nanoGPT's character-level dataset |
| `config/train_marolagpt.py` | marola's | the training settings |
| `package.py` | marola's | one release: weights, vocabulary, model card, licence, checksums |
| `publish_hf.py` | marola's | the upload to Hugging Face, a dry run unless `--yes` |
| `fork_check.py` | marola's | refuses a copied file without its header, and an `as-is` file that changed |
| `requirements.txt` | marola's | what nanoGPT's scripts and the upload import |

When marola changes a copied file, its row in `FORK.tsv` says `edited`; the provenance header and
the MIT notice stay. `just quality` runs `fork_check.py`.

## Credits

- **Andrej Karpathy**, for nanoGPT (MIT), the code marolaGPT is built with.
- **Fabio Akita** ([@akitaonrails](https://github.com/akitaonrails)), whose
  [microgpt](https://github.com/akitaonrails/microgpt) showed the path: a GPT trained from random
  weights on one consumer GPU, measured honestly. No code of microgpt is here: on 14 October 2026
  it had no licence, so it was read, not copied (marola-ml#48, marola-site#146).
