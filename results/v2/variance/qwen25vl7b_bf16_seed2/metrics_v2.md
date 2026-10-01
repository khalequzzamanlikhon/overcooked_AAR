# Study v2 metrics: qwen25vl7b_bf16_seed2 (Qwen2.5-VL-7B-Instruct)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 754 | 74% [71, 78] | 75% [72, 78] | 16% [11, 22] | 56% [48, 64] | 69% [57, 81] | 81% [76, 85] (50%) | 0.0 [0.0, 0.4] |
| video_dense | 411 | 46% [35, 54] | 44% [32, 54] | 4% [2, 6] | 15% [8, 21] | 23% [12, 36] | 56% [47, 66] (54%) | 1.4 [1.1, 2.2] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 74% [71, 78] | 49% [45, 53] | 0.195 | 94% [91, 97] | 72% [62, 82] |
| video_dense | 46% [35, 54] | 43% [35, 51] | 0.003 | 79% [69, 87] | 75% [66, 84] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 6% [4, 8] | 14% [11, 17] | 5% [3, 8] | 54% [33, 74] | 88% [83, 93] | 0% [0, 0] | 9% [5, 14] |
| video_dense | 9% [4, 13] | 26% [18, 34] | 20% [12, 29] | 71% [40, 100] | 39% [22, 77] | 0% [0, 0] | 3% [1, 5] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 1.82 [1.22, 2.73] | 0.27 [-0.98, 1.09] | 20% [9, 33] | 0% [0, 0] | 2.311 | 3% [2, 4] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 2.19 [1.52, 2.81] | -1.22 [-2.33, -0.19] | 4% [0, 12] | 0% [0, 0] | 1.462 | 29% [25, 34] | 0% [0, 0] | 64% [46, 83] | 18 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 59 / 69 / 64 (n=280) | 87 / 14 / 24 (n=206) | 88 / 13 / 23 (n=207) | 51 / 7 / 13 (n=37) | 56 / 5 / 10 (n=9) | 100 / 11 / 19 (n=6) | - / 0 / - (n=0) | 0 / 0 / - (n=2) | 0 / 0 / - (n=1) |
| video_dense | 28 / 23 / 25 (n=195) | 18 / 1 / 1 (n=49) | 74 / 7 / 12 (n=167) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion 0/0 vs 0/0
- video_dense: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 3 | 0% [0, 0] | 0% [0, 0] |
| video_dense | 15 | 4 | 0% [0, 0] | 0% [0, 0] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +29 [+19, +40], p=0.00781 | +12 [+7, +17], p=0.00012 | +46 [+36, +58], p=0.00073 | +26 [+15, +35], p=0.00391 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
