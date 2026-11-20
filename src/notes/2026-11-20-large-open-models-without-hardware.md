---
title: "Large open models without your own hardware: what privacy you really get"
date: 2026-11-20
section: llm
summary: "Two ways to run a large open model, including uncensored ones, without owning the hardware: a hosted service or a rented GPU node. What each costs, and why only a local model gives real privacy. Services, five models and GPU prices as of 20 November 2026."
license: own
draft: false
---

Some people want to try a strong uncensored model. That does not make them
criminals. Most of them simply do not want to be watched: they do not want
every question logged, stored, and maybe used for training. Others are tired
of a model that refuses a harmless question about security, medicine or
fiction.

The clean answer is a local model on your own box. But the biggest open models
do not fit on a home machine. My GB10 box has about 121 GiB of usable memory,
and the models below need 300 to 600 GB. So this note is about the non-local
options. There are two:

1. A hosted service that already runs uncensored models.
2. A rented GPU node, where you run the weights yourself.

One thing first, so nobody reads this the wrong way: **privacy in both
options is conditional.** You send your prompts to a machine that belongs to
someone else. A "no logs" service can log. Any of these services could even be
a honeypot, built to collect exactly the questions people do not want to ask
elsewhere. I have no evidence that any of them is, but from the outside you
cannot rule it out. Only a local model on your own hardware can guarantee
privacy. Everything below is a trade: less privacy for more model.

I have not benchmarked the services or the models below. Prices and privacy
statements are taken from the providers' own pages on 20 November 2026, unless
I say otherwise. Check them before you pay.

## What "uncensored" means here

Almost all of these models are *abliterated*: someone found the direction in
the weights that produces refusals and removed it. The model is not retrained
and it does not become smarter. It just stops saying no. The law does not
change either: what was illegal to do stays illegal.

## Option 1: hosted services

The fastest way. You pay per token or per month and you need no hardware.

| Service | What you get | Price | What they say about your prompts |
|---|---|---|---|
| [NanoGPT](https://nano-gpt.com/models/text) | Chat and API, about 600 text models, several uncensored ones (GLM 5.3 Uncensored, DeepSeek V4.1 Flash Uncensored, Abliterated Large) | Pay as you go, deposit from $0.10 in crypto or $1 by card. PRO is $12 per month. GLM 5.3 Flash Uncensored is $0.20 / $0.80 per 1M tokens | "By default, we do NOT store prompt or conversation content on our servers." No training on your content. Works without an account |
| [Venice](https://venice.ai) | Chat and API, own model "venice-uncensored" | Free tier (10 text prompts a day, no card), Pro $18 per month, or pay per token | "Zero data retention by default" on the API. Says illegal content is blocked at every setting |
| [Featherless](https://featherless.ai) | API and chat, hundreds of abliterated open models, mostly small and mid-size | Chat plan $25 per month, developer plan from $50 per month | "Featherless does not log chats, prompts, or completions sent through our API." |
| [abliteration.ai](https://abliteration.ai) | API, one large abliterated model | Plans from $20 per month or pay as you go; about $3.00 / $5.00 per 1M tokens according to a third-party comparison | "Your prompts and responses stay out of our logs." |
| [OpenRouter](https://openrouter.ai) | A router to other providers, includes Venice Uncensored | Per token, plus a card fee | Logging only if you opt in, but each upstream provider has its own policy |

Things to keep in mind:

- **"No logs" is a promise, not a proof.** You cannot verify it from outside,
  and a service that advertises "uncensored and private" is also the perfect
  honeypot. Do not type anything there that you could not afford to see
  leaked.
- **Routers pass your prompt on.** NanoGPT and OpenRouter send the request to
  a third-party host. NanoGPT's own policy calls "zero data retention" a
  best-effort label based on what that host claims. Read the privacy page and
  its settings before you rely on it.
- **Payment can identify you.** A card does. Crypto is visible on the chain.
- **Start small.** NanoGPT and Venice let you try with no account or no card.
  Subscribe only if the answers are good enough.

## Option 2: rent a GPU node and run the weights yourself

More work, but your prompts go only to a machine you rent for a few hours.
That is better than a chat service, not the same as private.

### Where to get the models

Hugging Face, filtered to GGUF text models with more than 500B parameters and
"uncensored" in the name:
[the search](https://huggingface.co/models?pipeline_tag=text-generation&num_parameters=min:500B&library=gguf&sort=trending&search=uncensored).
Five from the top of that list:

| Model | Size | Method | File | Notes from the model card |
|---|---|---|---|---|
| [AtomicChat/DeepSeek-V4.1-Flash-1017-Uncensored-GSQ-RCO-GGUF](https://huggingface.co/AtomicChat/DeepSeek-V4.1-Flash-1017-Uncensored-GSQ-RCO-GGUF) | 552B | abliteration | IQ1_M to IQ2_XS, 121 to 155 GB in the file list | Needs the Strata runtime, not plain llama.cpp. MIT |
| [AtomicChat/DeepSeek-V4.1-Flash-1017-Uncensored-DwarfStar-GGUF](https://huggingface.co/AtomicChat/DeepSeek-V4.1-Flash-1017-Uncensored-DwarfStar-GGUF) | 755B | abliteration | Q2_K, 366 GB | Needs the DwarfStar runtime. MIT |
| [softwareweaver/GLM-5.3-Uncensored-GGUF](https://huggingface.co/softwareweaver/GLM-5.3-Uncensored-GGUF) | 753B | converted from an uncensored FP8 release | Q4_K_M, 455 GB | Runs with llama.cpp. MIT |
| [Ryanchen911/Kimi-K3-Uncensored-GGUF](https://huggingface.co/Ryanchen911/Kimi-K3-Uncensored-GGUF) | 2.8T | abliteration | IQ1_S, 580 GB | Needs a llama.cpp fork and about 550 GB of RAM plus VRAM. Kimi K3 license |
| [Harsha001/DeepSeek-V4.1-Flash-1017-Uncensored-GSQ-RCO-StrixHalo-GGUF](https://huggingface.co/Harsha001/DeepSeek-V4.1-Flash-1017-Uncensored-GSQ-RCO-StrixHalo-GGUF) | 658B | pruned and abliterated | 215 GB | Made for one AMD machine with 128 GB of unified memory, not for a rented NVIDIA node. MIT |

Two warnings before you download half a terabyte:

- **Read the card.** Three of these five need a special runtime or a fork.
  The GLM 5.3 file is the only one that the card says runs with normal
  llama.cpp, so it is the easy first try.
- **Low-bit files lose quality.** Most of these are 1-bit and 2-bit quants.
  In [my own test](../nemotron-quantization/) a 30B model broke below 4 bits.
  Very large models are said to survive it better, but I have not measured
  these. The 4-bit GLM file is the safer bet.

### How much memory you need

Rough sizing: memory = parameters x bytes per parameter, plus 10 to 20% for
the KV cache. BF16 is 2 bytes per parameter, FP8 is 1, 4-bit is about 0.5 to
0.6. For a GGUF file it is simpler: the file size plus the cache.

| H200s in one node | Memory | Fits roughly |
|---|---|---|
| 1 | 141 GB | 70B in FP8, about 200B in 4-bit |
| 2 | 282 GB | 70B in BF16, about 400B in 4-bit |
| 4 | 564 GB | about 400B in FP8; the 455 GB GLM 5.3 file |
| 8 | 1128 GB | 600 to 700B in FP8, the largest open models |

Rent the GPUs **in one node** (2, 4 or 8 on the same machine). Separate
single-GPU instances cannot be joined. Many providers sell H200 only as
8-GPU nodes.

How the model is split depends on the format:

- **GGUF with llama.cpp**: it spreads the layers over all GPUs it sees, and
  what does not fit can stay in system RAM (slower).
- **Safetensors (BF16, FP8) with vLLM or SGLang**: tensor parallelism, one
  flag, for example `--tensor-parallel-size 8`.

### What it costs

Prices per GPU-hour. Overseas prices come from aggregators, Chinese prices
from rentgpu.link, both November 2026. CNY is converted at 7.25 per dollar.
They change daily.

**H200, 141 GB**

| Provider | Price per GPU-hour | Type |
|---|---|---|
| Vast.ai | from $0.74 | spot, marketplace |
| Nebius | $0.79 | spot |
| Beam | $2.09 | on demand |
| Together AI | $2.99 | on demand |
| Koyeb | $3.00 | on demand |
| DigitalOcean | $3.44 to $4.47 | on demand, sources differ |
| RunPod | $3.59 to $5.29 | on demand, sources differ |
| Gongji Compute (China) | 35.00 CNY, about $4.83 | pay as you go |
| AWS | $7.91 | on demand, 8-GPU node |

A 4x H200 node is about $8 to $12 per hour on demand, an 8x node $16 to $32,
and less on spot. Count the download too: 455 GB takes about an hour at
1 Gbit/s, and you pay for that hour.

**China, other cards (cheapest listing per card)**

| GPU | Memory | Price per card-hour | Platform |
|---|---|---|---|
| H20 | 96 GB | 3.40 CNY, about $0.47 | PPIO, spot |
| Ascend 910B2 | 64 GB | 2.97 CNY, about $0.41 | JiZhiSuan |
| A800 | 80 GB | 5.15 CNY, about $0.71 | MornAI |
| A100 | 80 GB | 5.98 CNY, about $0.82 | AutoDL |
| H800 | 80 GB | 10.50 CNY, about $1.45 | AutoDL |
| H100 | 80 GB | 11.88 CNY, about $1.64 | PPIO, spot |
| Ascend 910C | 128 GB | 13.20 CNY, about $1.82 | Gongji Compute |

Notes on China:

- The H20 is the cheapest large memory on the list. It is slow at compute,
  but for inference of a big model memory matters most.
- Ascend cards are not CUDA. They use Huawei's own stack, so expect extra
  work.
- Registration may need Alipay or a Chinese bank card. Alibaba Cloud
  International takes normal cards, but its big-cloud prices are higher.
- Your prompts and files sit under Chinese jurisdiction.

### Is a rented node private?

More than a chat service, less than your own box. Nobody logs your prompts by
design, but the provider owns the machine and can technically look inside. On
a marketplace like Vast.ai the host is some third party you know nothing
about. Use a known provider if the content matters, and delete the instance
and its disk when you are done.

## Which one to pick

- **Just curious:** a hosted service. Try the free tier or put in one dollar.
- **You want the largest model, or you do not trust any "no logs" promise:**
  rent a 4x or 8x H200 node for an evening. That is $30 to $100.
- **You need real privacy:** a smaller model on your own hardware. It is the
  only setup where nobody else is in the loop, and the only one that can
  guarantee anything.

## Sources

- [NanoGPT models](https://nano-gpt.com/models/text), [pricing](https://nano-gpt.com/pricing), [privacy policy](https://nano-gpt.com/legal/privacy-policy)
- [Venice: best uncensored LLM APIs](https://venice.ai/blog/best-uncensored-llm-apis)
- [Featherless: best uncensored AI models 2026](https://featherless.ai/blog/best-uncensored-ai-models-2026)
- [Brutal AI: uncensored LLM API providers compared](https://brutal.ai/en/models/guides/uncensored-llm-api-providers-compared)
- [Off Grid AI: best private LLM APIs in 2026](https://getoffgridai.co/articles/best-private-llm-apis-in-2026-prompts-never-stored-or-trained-on/)
- [flopper.io: H200 cloud pricing](https://flopper.io/pricing/nvidia-h200)
- [Thunder Compute: H200 price comparison](https://www.thundercompute.com/blog/nvidia-h200-pricing)
- [vps.fund: H200 cloud price comparison](https://vps.fund/article/l40s-gpu-cloud-pricing-comparison-20260602)
- [rentgpu.link: GPU prices on Chinese platforms](https://rentgpu.link/en/china)
- [PromptQuorum: AutoDL, Alibaba and Tencent GPU pricing](https://www.promptquorum.com/local-llms/alibaba-cloud-vs-tencent-cloud-gpu-ai-2026)
