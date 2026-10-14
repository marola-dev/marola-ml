<!--
Forked into marola-dev/marola-ml on 2026-10-14 from karpathy/nanoGPT at commit 3adf61e154c3,
https://github.com/karpathy/nanoGPT/blob/3adf61e154c3fe3fca428ad6bc3818b27a3b8291/data/openwebtext/readme.md
Copyright (c) 2022 Andrej Karpathy, MIT License (sea/nanogpt/LICENSE). Copied as is below this header.
-->


## openwebtext dataset

after running `prepare.py` (preprocess) we get:

- train.bin is ~17GB, val.bin ~8.5MB
- train has ~9B tokens (9,035,582,198)
- val has ~4M tokens (4,434,897)

this came from 8,013,769 documents in total.

references:

- OpenAI's WebText dataset is discussed in [GPT-2 paper](https://d4mucfpksywv.cloudfront.net/better-language-models/language_models_are_unsupervised_multitask_learners.pdf)
- [OpenWebText](https://skylion007.github.io/OpenWebTextCorpus/) dataset
