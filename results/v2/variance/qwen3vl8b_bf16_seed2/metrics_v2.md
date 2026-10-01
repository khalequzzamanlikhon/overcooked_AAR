# Study v2 metrics: qwen3vl8b_bf16_seed2 (Qwen3-VL-8B-Instruct)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 899 | 95% [93, 97] | 96% [94, 98] | 25% [20, 33] | 91% [89, 93] | 97% [93, 100] | 99% [98, 100] (51%) | 0.0 [0.0, 0.0] |
| video_dense | 737 | 40% [33, 47] | 40% [31, 48] | 6% [5, 8] | 23% [19, 27] | 13% [4, 23] | 57% [51, 62] (51%) | 1.1 [0.8, 1.3] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 95% [93, 97] | 55% [49, 61] | 0.325 | 98% [97, 100] | 74% [65, 83] |
| video_dense | 40% [33, 47] | 42% [35, 49] | -0.023 | 67% [58, 76] | 65% [57, 72] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 1% [1, 2] | 2% [1, 4] | 2% [0, 3] | 90% [84, 95] | 100% [99, 100] | 0% [0, 0] | 9% [2, 19] |
| video_dense | 9% [6, 13] | 16% [10, 22] | 35% [25, 44] | 41% [20, 64] | 46% [34, 58] | 0% [0, 0] | 5% [1, 9] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 1.02 [0.69, 1.36] | 0.80 [0.29, 1.24] | 33% [18, 51] | 2% [0, 7] | 2.719 | 1% [1, 2] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 3.81 [2.66, 5.23] | -3.71 [-5.18, -2.50] | 10% [0, 21] | 0% [0, 0] | 1.268 | 25% [21, 30] | 0% [0, 0] | 20% [6, 38] | 3 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 91 / 97 / 94 (n=254) | 99 / 16 / 28 (n=212) | 97 / 32 / 49 (n=369) | 63 / 6 / 12 (n=27) | 100 / 24 / 39 (n=22) | 100 / 26 / 42 (n=15) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_dense | 37 / 13 / 19 (n=82) | 29 / 4 / 7 (n=178) | 66 / 12 / 20 (n=312) | 1 / 0 / 1 (n=126) | 0 / 0 / - (n=1) | 29 / 7 / 11 (n=14) | 0 / 0 / - (n=7) | 0 / 0 / - (n=12) | 100 / 1 / 3 (n=1) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_dense: waiting 14/1 vs 0/-; handoff 0/0 vs 0/0; congestion 100/0 vs 0/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 75 | 24% [12, 39] | 40% [13, 67] |
| video_dense | 15 | 83 | 60% [44, 75] | 20% [0, 40] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +55 [+48, +62], p=6e-05 | +19 [+14, +26], p=6e-05 | +85 [+74, +93], p=0.00064 | +43 [+38, +48], p=0.00065 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
