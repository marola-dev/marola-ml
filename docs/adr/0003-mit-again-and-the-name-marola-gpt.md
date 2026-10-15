# ADR-0003: marola-ml is MIT again, and the model is marola-gpt

| | |
|---|---|
| **Status** | Proposed (2026-10-14), by the owner's order |
| **Supersedes** | the licence of [ADR 0002](0002-marolagpt-and-the-restricted-licence.md) (its decision 3), and the name marolaGPT |

## Context

The owner, 14 October 2026: "change license of marola-ml to MIT, so you can distribute with no
problem. Dont do any minting for now, change the name to marola-gpt not marolagpt, name this
prepare for 0.0.1 release on hugging face, update README.md license".

## Decision

1. **MIT.** `LICENSE` is the MIT License, Copyright (c) 2026 marola.dev, byte for byte the one
   v0.1.0 was released with. It covers the code and the model it trains. `sea/nanogpt/` keeps
   nanoGPT's own MIT License.
2. **The name is marola-gpt**, everywhere: the recipes (`just marola-gpt` and its steps), the tags
   (`marola-gpt-vX.Y.Z`), the release directory (`sea/release/marola-gpt-<version>/`), the Hugging
   Face repository (`h0ffmann/marola-gpt`) and the model card.
3. **The first release is 0.0.1.** `just sea-release` counts from 0.0.0, so its first patch is
   `marola-gpt-v0.0.1`.
4. **Public on Hugging Face.** `sea/publish_hf.py` creates the repository public; `--private` is the
   exception.
5. **No DOI for now.** marola-ml#56 waits.

## Consequences

- The restricted licence was on `main` from #53 to this change, and no release was made under it:
  the only release is v0.1.0, MIT. The question of relicensing contributors' code is gone.
- ADR 0002's chain (the recipes, the release directory, the publish workflow) stands, under the new
  name; its licence and its "no distribution outside marola" consequences do not.
- `marola-gpt-publish.yml` still keeps no workflow artifact; the reason now is only that a release
  belongs on Hugging Face, not in a run's storage.
