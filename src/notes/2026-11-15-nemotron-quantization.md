---
title: What does quantization cost a local coding model? Seven quants of one model
date: 2026-11-15
section: llm
summary: One model, seven quantizations from 2.5 to 8 bits, two engines, 36 coding tasks scored by compiler and tests. Below 4 bits the model breaks; between 4 and 8 bits run-to-run noise is as large as the difference.
license: own
draft: false
---

The usual advice is "Q4 is fine, Q8 if you can afford it". I wanted a number
for that. Same model, same box, same 36 tasks from
[llm-compile-bench](https://github.com/cryply/llm-compile-bench); only the
quantization changes. A task counts only if the code compiles and passes the
hidden tests on the first try.

## Setup

- ASUS Ascent GX10 (NVIDIA GB10, 128 GB unified memory)
- Model: Nemotron 3.5 Lightning 30B-A3B, a mixture-of-experts model with 3B
  active parameters. It is the weakest model of my
  [first comparison](../local-llm-compile-bench/), but also one of the
  fastest, which makes it the obvious candidate for a lower-bit quant.
- Quants: Q8_0, Q5_0, Q4_0, IQ4_NL, MXFP4, and two mixed 2-bit GGUFs
  (2.47 and 2.97 bits per weight on average)
- Engines: `llama-server` (llama.cpp b11234) and Ollama 0.33.1.
  Context 40960, temperature 0.2, nothing else tuned.
- 36 tasks: six each in C++, Go, Python, React, Rust and TypeScript

## Results: llama-server, four runs per quant

| Quant | Run 1 | Run 2 | Run 3 | Run 4 | Mean (of 36) | tok/s |
|---|---|---|---|---|---|---|
| Q8_0 | 23 | 19 | 22 | 19 | **20.8** | 56 |
| Q4_0 | 17 | 19 | 17 | 20 | **18.2** | 88 |
| MXFP4 | 15 | 18 | 19 | 21 | **18.2** | 69 |
| IQ4_NL | 15 | 18 | 17 | 19 | **17.2** | 88 |
| Q5_0 | 18 | 15 | 15 | 18 | **16.5** | 78 |
| 2.97 bpw | 5 | | | | 5 | 100 |
| 2.47 bpw | 5 | | | | 5 | 104 |

The 2-bit quants ran once: at 5 of 36 there was nothing left to average.
They compiled 12 and 7 times, so most of their code did not even build.

## The same quants on Ollama

| Quant | Runs | Mean (of 36) | tok/s |
|---|---|---|---|
| Q5_0 | 17, 21, 21 | 19.7 | 77 |
| Q8_0 | 22, 16, 19 | 19.0 | 55 |
| MXFP4 | 15, 15, 18 | 16.0 | 69 |
| IQ4_NL | 7 runs, 14..18 | 15.7 | 88 |
| Q4_0 | 16, 14, 16 | 15.3 | 88 |

Ollama 0.33.1 failed on the 2-bit files with a tensor size error, which is why they only ran on `llama-server`.
Speed is the same on both engines. One Ollama run was dropped: my Rust tutor was using a model on the same box
at the same time.

## Tests passed by language, llama-server

Four runs, six tasks per language, so out of 24:

| Quant | C++ | Go | Python | React | Rust | TypeScript |
|---|---|---|---|---|---|---|
| Q8_0 | 21 | 11 | 20 | 13 | 7 | 11 |
| Q4_0 | 17 | 11 | 20 | 13 | 4 | 8 |
| MXFP4 | 17 | 9 | 20 | 15 | 6 | 6 |
| IQ4_NL | 21 | 4 | 18 | 13 | 4 | 9 |
| Q5_0 | 20 | 7 | 19 | 8 | 5 | 7 |

## What the numbers say

**Below 4 bits the model breaks.** 5 of 36 against 17 to 21 for every quant
from 4 bits up. This is the only result here that no amount of noise explains.

**Between 4 and 8 bits, the noise is as large as the difference.** The same
MXFP4 file passed 15, 18, 19 and 21 tasks in four runs. Q8_0 is ahead of the
4-bit quants by about 3 tasks, but that is not significant at four runs
(Welch's t-test, p = 0.06). Q5_0 came out last on `llama-server` and first on
Ollama. If the ranking flips when you change the engine, one run per quant
tells you nothing about the quant.

**Q4_0 is the practical pick.** About 88 % of Q8_0's pass rate at 1.6 times
the speed. MXFP4 matches its pass
rate but is slower on this box.

**Rust is the hardest language for this model at every quant.** 4 to 7 of 24
in Rust, against 17 to 21 in C++ and 18 to 20 in Python. Quantization does not
explain it: Q8_0 is barely better. My guess is that a model with 3B active
parameters does not have room for the borrow checker; the bigger models of the
first comparison did much better here.

**The engine matters a little, the runs matter more.** The 4-bit quants
averaged 15.7 on Ollama and 17.9 on `llama-server`. The two engines use
different default sampling settings; I only fixed the temperature. That
difference is smaller than the spread of a single quant across runs.

## Caveats

- Four runs per quant on one engine, three on the other. Enough to see the
  2-bit cliff and to see that the rest is noise; not enough to rank 4-bit
  formats against each other.
- One model. A dense model, or one with more active parameters, may lose more
  or less from the same quantization.
- Only temperature was fixed. Top-p, min-p and repeat penalty were left at
  each engine's defaults.

Raw CSVs are in the repository under
[results/gb10](https://github.com/cryply/llm-compile-bench/tree/main/results/gb10).
