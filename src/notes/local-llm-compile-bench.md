---
title: Does the code compile? Five local models on a DGX Spark
date: 2026-10-27
section: llm
summary: Six programming tasks in Rust, C++, Python, Go, TypeScript and React, five open-weight models on one GB10 box, scored by compiler and tests instead of by eye.
license: own
draft: true
---

Most "DGX Spark benchmark" posts measure tokens per second. That answers
*how fast*, not *which model to install*. For a developer the second question
reduces to something a machine can check: does the code compile, and do the
tests pass?

## Setup

- ASUS Ascent GX10 (NVIDIA GB10, 128 GB unified memory)
- Ollama for models that fit side by side, `llama-server` (llama.cpp) for the rest
- Harness: [bench](https://github.com/cryply/spark-compile-bench) — one prompt per
  language with a fixed signature, hidden tests, `cargo` / `g++` / `pytest` /
  `go test` / `tsc` as judges

## Models

| Model | Quant | Size | Runtime |
|---|---|---|---|
| Nemotron 3.5 Lightning 30B-A3B | IQ4_NL | 17 GB | Ollama |
| Qwen3.8-27B | Q4_K_M | 18 GB | Ollama |
| gpt-oss-120b | MXFP4 | 65 GB | Ollama |
| Qwen3.6-35B-A3B ("qwopus36") | Q6 + MTP | ~30 GB | llama.cpp |
| DeepSeek V4 Flash 0731 | UD-IQ2_XXS | 91 GB | llama.cpp |

## Results

<!-- TODO: вставить таблицу из summary.py после полного прогона -->

| Model | Compiles | Tests pass | Avg time | tok/s |
|---|---|---|---|---|
| … | …/6 | …/6 | … s | … |

## A first look, before the harness

The same one-line prompt — *write a Rust function that parses an ISO-8601
date* — sent by hand to four models:

```text
Nemotron 3.5 Lightning   93 tok/s    27 s   answered in English, date-only
gpt-oss-120b             44 tok/s    95 s   invented "chrono 0.5", missing dep
Qwen3.8-27B              30 tok/s    73 s   clean; one missing `use Datelike`
DeepSeek V4 Flash        17 tok/s   659 s   best code, 11k tokens of thinking
```

Capping DeepSeek's reasoning at 2048 tokens made it four times faster — and
its answer stopped compiling. Thinking is where its quality comes from.

## Takeaways

<!-- TODO -->
