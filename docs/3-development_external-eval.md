# External evaluation

What marola asks an evaluation provider to run, and the terms any provider is held to. A provider
gets this page to estimate the cost. The design behind it (the backend seam, the results store,
the reproducibility check) is
[MIP-0081](https://docs.marola.dev/6-MIPs/MIP-0081-external-llm-evaluation/). Until that lands,
marola's only numbers are its own: [the benchmark gate](3-development_benchmark-gate.md)'s 22
ocean questions and the training-time `eval_loss`.

## Models

Tier A is the first request. Tier B follows once tier A's numbers show which base is worth
fine-tuning.

| Tier | Model | Hugging Face repo | Params | Weights sent | Why |
|---|---|---|---|---|---|
| A | SmolLM2-360M-Instruct | `HuggingFaceTB/SmolLM2-360M-Instruct` | 0.36B | bf16 safetensors | the base of the released model |
| A | marola-sea-tiny | `h0ffmann/marola-sea-tiny-GGUF` at `e6d8b16` | 0.36B | GGUF `Q8_0`, the one file published | the released model; minus the row above, the fine-tune's delta |
| A | Llama-3.2-3B-Instruct | `meta-llama/Llama-3.2-3B-Instruct` (gated) | 3.2B | bf16 safetensors | what the app answers with today (`llama3.2` in `Dockerfile.local`) |
| A | Qwen3-4B-Instruct-2507 | `Qwen/Qwen3-4B-Instruct-2507` | 4.02B | bf16 safetensors | `qwen-4b`, the Apache-2.0 step up from `tiny` |
| A | Qwen2.5-7B-Instruct | `Qwen/Qwen2.5-7B-Instruct` | 7.62B | bf16 safetensors | `qwen-7b` |
| B | Llama-3.2-1B-Instruct | `unsloth/Llama-3.2-1B-Instruct` | 1.24B | bf16 safetensors | `small` |
| B | Qwen2.5-14B-Instruct | `Qwen/Qwen2.5-14B-Instruct` | 14.77B | bf16 safetensors | `qwen-14b` |
| B | each marola-sea fine-tune of a tier A base, once published | `h0ffmann/marola-sea-<preset>-GGUF` | | GGUF `Q4_K_M` and `Q8_0` | the fine-tune's delta at that size |

Sizes and repos are `finetune/train_lora.py`'s `PRESETS`. `qwen-27b` is left out because
MIP-0048 parks it. Only public weights are sent.

## Benchmarks

Task names are [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)'s
(checked at `d6de816`, 2026-09-14) unless marked *pt fork*, which is
[lm-evaluation-harness-pt](https://github.com/eduagarcia/lm-evaluation-harness-pt) (`ab24923`),
the harness behind the Open Portuguese LLM Leaderboard. Shots are the task config's own, or the
usual leaderboard setting passed as `--num_fewshot` where the config sets none (`arc_pt`,
`global_mmlu_pt`); a provider that changes one says so in the results.

| Set | Task | Shots | Metric | Items | Why |
|---|---|---|---|---|---|
| General | `arc_challenge` | 25 | acc_norm | 1,172 | grade-school science reasoning |
| General | `hellaswag` | 10 | acc_norm | 10,042 | common-sense completion |
| General | `mmlu` | 5 | acc | 14,042 | broad knowledge; comparable with every model card |
| General | `truthfulqa_mc2` | 0 | acc | 817 | invented facts, marola-sea's known failure |
| General | `gsm8k` | 5 | exact_match (strict) | 1,319 | multi-step arithmetic |
| General | `ifeval` | 0 | prompt-level strict acc | 541 | following the answer format the app asks for |
| Portuguese | `arc_pt` | 25 | acc_norm | | `arc_challenge`, machine-translated |
| Portuguese | `global_mmlu_pt` | 5 | acc | | MMLU with a reviewed translation |
| Portuguese | `belebele_por_Latn` | 0 | acc | 900 | reading comprehension in pt |
| Portuguese | `enem_challenge` (*pt fork*) | 3 | acc | | Brazil's national high-school exam |
| Portuguese | `bluex` (*pt fork*) | 3 | acc | | Brazilian university entrance exams |
| Portuguese | `oab_exams` (*pt fork*) | 3 | acc | | Brazilian bar exam, long pt-BR prompts |
| Portuguese | `assin2_rte` (*pt fork*) | 15 | F1 macro | | entailment in pt-BR |
| Portuguese | `faquad_nli` (*pt fork*) | 15 | F1 macro | | whether a pt-BR passage answers a question |
| Domain | `marola_ocean` | 0 | keyword coverage | 22 | marola's own job; a custom task, exported per MIP-0081 task 4 ([#29](https://github.com/marola-dev/marola-ml/issues/29)) |

Tier A is 5 models × the 14 tasks above `marola_ocean`: 70 model-task runs. `marola_ocean` joins
once it exists as a harness task. MIP-0081's tasks here are
[#26](https://github.com/marola-dev/marola-ml/issues/26) to
[#30](https://github.com/marola-dev/marola-ml/issues/30).

## Questions for the provider

1. Which harness and version runs each task, and is the exact config (few-shot seed, chat template
   on or off, batch size, dtype) returned with the score?
2. How is a GGUF run: llama.cpp, and are `multiple_choice` tasks scored by log-likelihood or by
   generation? A generation-scored ARC is a different benchmark.
3. Can the *pt fork* tasks and a custom task (`marola_ocean`, a YAML and a `utils.py`) run?
4. Are per-sample outputs and logs exportable, so a score can be checked without the provider?
5. Is a gated repo (Llama 3.2) run with the provider's own accepted licence?

## Terms any provider is held to

- **Reproducible**: harness name and version, task versions, few-shot settings, dtype or
  quantisation, and the model's revision SHA are disclosed with every score.
- **Exportable**: raw per-sample outputs come back as files marola keeps in this repo; a score
  that lives only on a provider's dashboard is not published.
- **Checked**: before a provider's numbers are published, one task re-run here on `tiny` must
  match its score within the reported stderr. A mismatch holds back those numbers; the
  partnership goes on.
- **No exclusivity, no claim**: marola may use other providers and runs its own evaluations; the
  provider gets no rights to marola's data, models or results beyond citing them.
- **Never in the critical path**: a provider's score informs; it never gates `docker-local.yml`
  or a model publish.
- **Credit**: a provider that runs evaluations at no cost to marola is credited on marola.dev's
  partners page, in the model card next to each score it produced, and in the results file.
- **Cost**: every run is started by a person, its cost or credit is recorded in the commit's
  `Cost:` line, and a provider's API key lives in a repository secret or a local environment
  variable, never in a file.
</content>
</invoke>
