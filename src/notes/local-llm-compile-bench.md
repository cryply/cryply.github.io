---
title: Does the code compile? Five local models on a DGX Spark
date: 2026-10-27
section: llm
summary: Six programming tasks in Rust, C++, Python, Go, TypeScript and React, five open-weight models on one GB10 box, scored by compiler and tests instead of by eye.
license: own
draft: false
---

Most "DGX Spark benchmark" posts measure tokens per second. That answers
*how fast*, not *which model to install*. For a developer the second question
reduces to something a machine can check: does the code compile, and do the
tests pass?

## Setup

- ASUS Ascent GX10 (NVIDIA GB10, 128 GB unified memory)
- Ollama for models that fit side by side, `llama-server` (llama.cpp) for the rest
- Harness: [llm-compile-bench](https://github.com/cryply/llm-compile-bench): one prompt per
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

Six tasks, five runs per model (30 attempts each), temperature 0.2, 32k
completion tokens. "Wall-to-pass" is the average time over the attempts that
passed: the number that matters when you are waiting for a usable answer.
"Flaky" lists tasks that passed in some runs and failed in others.

| Model | Compiles | Tests pass | Wall median | Wall min..max | Wall-to-pass | tok/s | Flaky tasks |
|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | 30/30 | 28/30 | 54 s | 15..134 s | 57 s | 31 | go_worker_pool 4/5, rust_iso8601 4/5 |
| gpt-oss-120b | 30/30 | 26/30 | 22 s | 10..63 s | 27 s | 39 | go_worker_pool 1/5 |
| DeepSeek V4 Flash | 26/30 | 25/30 | 118 s | 55..1638 s | 169 s | 20 | go_worker_pool 3/5, react_counter 4/5, rust_iso8601 3/5 |
| Qwen3.6-35B-A3B | 18/30 | 17/30 | 22 s | 11..326 s | 24 s | 95 | rust_iso8601 2/5 |
| Nemotron 3.5 Lightning | 18/30 | 15/30 | 42 s | 13..233 s | 34 s | 86 | cpp_lru 2/5, go_worker_pool 2/5, ts_debounce 1/5 |

The first single run told a different story: gpt-oss-120b went 6 for 6 and
looked like the clear winner. Over five runs its Go worker pool passed once in
five. Qwen3.8-27B, second on that first run, is the most reliable model here.
The Go task is the one that separates the field: every model is flaky on it,
and it is the only task about concurrency.

## A first look, before the harness

The same one-line prompt, *write a Rust function that parses an ISO-8601
date*, sent by hand to four models:

```text
Nemotron 3.5 Lightning   93 tok/s    27 s   answered in English, date-only
gpt-oss-120b             44 tok/s    95 s   invented "chrono 0.5", missing dep
Qwen3.8-27B              30 tok/s    73 s   clean; one missing `use Datelike`
DeepSeek V4 Flash        17 tok/s   659 s   best code, 11k tokens of thinking
```

Capping DeepSeek's reasoning at 2048 tokens made it four times faster, and
its answer stopped compiling. Thinking is where its quality comes from.

## Takeaways

**Tokens per second ranks the models backwards.** The two fastest generators,
Qwen3.6 at 95 tok/s and Nemotron at 86, pass about half the attempts. The two
slowest-by-token models are the two most reliable. If you only benchmark
throughput, you install the wrong model.

**Qwen3.8-27B is the quality pick, gpt-oss-120b the balance pick.** 28 of 30
at 17 GB on disk, leaving room for a second model next to it. gpt-oss is twice
as fast to a passing answer (27 s against 57 s) at 26 of 30, and it is the one
I would leave loaded for daily work, as long as the task is not concurrency
in Go.

**DeepSeek V4 Flash is the strongest reasoner and the worst daily driver.**
It solves what the others cannot, at five to ten times the wait, and its
run-to-run spread (55 s to 27 minutes on the same prompt) is larger than the
gap between the other models. Capping its reasoning makes it fast and wrong.

**The small MoE models fail on Rust and Go specifically.** Python, TypeScript
and React mostly pass; the type system and the concurrency model are where
they come apart.

**Half of the first run's failures were mine, not the models'.** Missing
toolchains on the box (every Rust, Go and TypeScript task would have scored
zero), code returned without Markdown fences that the harness refused to read,
a token budget set too low for reasoning models. A benchmark harness needs the
same scepticism as the models it judges; a preflight check that the judges
exist is now the first thing the script does.

**One run is not a measurement.** The single run had gpt-oss at 6/6 and Qwen
3.8 second. Five runs reversed them. Report the spread, not the mean.
