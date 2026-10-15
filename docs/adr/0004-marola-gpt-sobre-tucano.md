# ADR-0004: o marola-gpt passa a ser um adaptador LoRA sobre o Tucano-2b4

| | |
|---|---|
| **Status** | Proposto (2026-10-15), por pedido do dono do repositório (#67) |
| **Substitui** | [ADR 0001](0001-marola-sea-from-nanogpt.md) (o modelo do marola só a partir do nanoGPT, treinado do zero) e, para os pesos publicados, a decisão 1 do [ADR 0003](0003-mit-again-and-the-name-marola-gpt.md) (MIT também no modelo) |

## Contexto

O marola-gpt 0.0.1 é um nanoGPT por caractere com 826 240 parâmetros, treinado do zero nos 15 080
caracteres do marola-corpus v0.1.0. O texto que ele gera tem forma de palavra e não tem sentido
(README, "marola-gpt"). Em 15 de outubro de 2026, o dono pediu: "mude a base do modelo para
Tucano-2b4, respeitando a licença". A MIP-0050 já tinha comparado os modelos abertos em português.
O Manacá-1B ficou de fora porque o tokenizer dele converte tudo para minúsculas e não consegue
citar o `PRÓPRIA`/`IMPRÓPRIA` da agência (MIP-0050 §6).

O [Tucano-2b4](https://huggingface.co/TucanoBR/Tucano-2b4) tem 2 444 618 240 parâmetros, foi
treinado do zero em português (GigaVerbo), usa arquitetura Llama com tokenizer de 32 mil peças
que diferencia maiúsculas e é distribuído sob Apache-2.0. Os números vêm do card e do
`config.json` na revisão `b8def49a1931`, lidos em 15/10/2026.

## Decisão

1. **A base é o Tucano-2b4, fixado na revisão `b8def49a1931508a7cedc1f3fd6ff163515b0983`**
   (`sea/finetune_tucano.py`, `BASE_REVISION`). Os pesos da base não mudam e não são
   redistribuídos: quem usa o marola-gpt baixa a base do repositório do TucanoBR.
2. **O marola treina só um adaptador LoRA** (r=8, alpha=16, em `q_proj` e `v_proj`; 1 597 440
   parâmetros treináveis) no marola-corpus fixado em `corpus.version`, na CPU. Cabe num runner
   hospedado do GitHub (4 núcleos, 16 GB). Medido aqui, no mesmo formato de máquina, com o
   corpus v0.1.0 (5 005 tokens): cerca de 1,4 s por passo com blocos de 128 tokens.
3. **Uma release é o adaptador**: `adapter_config.json`, `adapter_model.safetensors`, `LICENSE`,
   `README.md` e `CHECKSUMS`, com cerca de 6 MB (o adaptador da primeira rodada tinha 6 402 376 bytes) em vez de cerca de 4,9 GB.
4. **Licença dos pesos: Apache-2.0**, a do Tucano. O `LICENSE` da release é o do Tucano, copiado
   byte a byte em `sea/LICENSE-Tucano-2b4`. O model card dá crédito aos autores, diz o que o
   marola mudou (seção 4(b) da Apache-2.0) e declara `base_model: TucanoBR/Tucano-2b4`. O
   repositório do Tucano não tem arquivo `NOTICE`, então não há o que repassar pela seção 4(d).
   O código do marola-ml continua MIT.
5. **As versões 0.0.x ficam com o nanoGPT.** A primeira release LoRA é a 0.1.0.
   `scripts/sea-release.sh` e `marola-gpt-publish.yml` recusam 0.0.x. O `sea/nanogpt/` fica no
   repositório como o código que treinou a 0.0.1, ainda verificado pelo `sea/fork_check.py`.

## Consequências

- O marola-gpt deixa de ser "do marola desde o primeiro peso". Ele passa a ser o Tucano com uma
  camada treinada pelo marola, e o README diz isso.
- O corpus continua em inglês. O Tucano escreve em português, então a saída mistura a língua da
  base com o vocabulário do corpus até existir um corpus em português (fora do escopo de #67).
- Rodar o `ask.py` exige baixar cerca de 4,9 GB na primeira vez e uns 10 GB de RAM.
- Um adaptador só funciona sobre a revisão exata da base. Trocar `BASE_REVISION` exige treinar e
  publicar uma release nova.
