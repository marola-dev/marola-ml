# marola-gpt's training configuration for nanoGPT's train.py: a small character-level GPT on
# marola's corpus notes (sea/prepare_corpus.py). Marola's own file, in the shape of nanoGPT's
# config/train_shakespeare_char.py. train.py executes it, then any --key=value on the command line
# overrides it (sea/nanogpt/configurator.py). The defaults run on a CPU in minutes; give a GPU
# --device=cuda --compile=True and larger n_layer, n_embd and max_iters.

out_dir = "out-marola-gpt"
dataset = "marola_corpus"

eval_interval = 100
eval_iters = 20
log_interval = 10
always_save_checkpoint = False  # the corpus is small: keep only the best validation loss
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 16
block_size = 128  # characters of context

n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.1

learning_rate = 1e-3
max_iters = 1000
lr_decay_iters = 1000
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 50

device = "cpu"
compile = False
dtype = "float32"  # train.py picks float16 when it sees no bf16 GPU; a CPU has no use for it
