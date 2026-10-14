# Forked into marola-dev/marola-ml on 2026-10-14 from karpathy/nanoGPT at commit 3adf61e154c3,
# https://github.com/karpathy/nanoGPT/blob/3adf61e154c3fe3fca428ad6bc3818b27a3b8291/config/eval_gpt2_xl.py
# Copyright (c) 2022 Andrej Karpathy, MIT License (sea/nanogpt/LICENSE). Copied as is below this header.

# evaluate the base gpt2
# n_layer=48, n_head=25, n_embd=1600
# 1558M parameters
batch_size = 8
eval_iters = 500 # use more iterations to get good estimate
eval_only = True
wandb_log = False
init_from = 'gpt2-xl'
