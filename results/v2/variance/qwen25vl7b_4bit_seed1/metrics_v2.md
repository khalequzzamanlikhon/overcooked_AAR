# Study v2 metrics: qwen25vl7b_4bit_seed1 (Qwen2.5-VL-7B-Instruct 4-bit)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 715 | 67% [62, 72] | 67% [62, 73] | 14% [11, 19] | 51% [45, 58] | 69% [60, 78] | 80% [76, 84] (51%) | 0.4 [0.1, 0.7] |
| video_dense | 719 | 31% [25, 37] | 32% [25, 38] | 5% [4, 7] | 18% [14, 22] | 20% [13, 29] | 54% [48, 61] (53%) | 1.7 [1.3, 2.5] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 67% [62, 72] | 43% [38, 48] | 0.175 | 93% [90, 95] | 68% [55, 79] |
| video_dense | 31% [25, 37] | 35% [27, 43] | -0.033 | 63% [50, 75] | 59% [48, 71] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 8% [6, 11] | 18% [14, 22] | 7% [4, 10] | 57% [42, 100] | 77% [68, 86] | 0% [0, 0] | 6% [3, 9] |
| video_dense | 8% [4, 14] | 24% [17, 32] | 37% [25, 49] | 19% [0, 40] | 32% [24, 45] | 0% [0, 0] | 1% [0, 1] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 2.20 [1.38, 3.49] | -0.64 [-2.33, 0.60] | 31% [20, 42] | 18% [7, 31] | 2.637 | 3% [2, 3] | 4% [0, 13] | 0% [0, 0] | 0 |
| video_dense | 2.87 [2.00, 4.13] | -2.29 [-3.69, -1.24] | 7% [0, 18] | 38% [22, 53] | 1.621 | 26% [23, 29] | 0% [0, 0] | 49% [32, 66] | 0 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 54 / 69 / 61 (n=302) | 77 / 15 / 25 (n=247) | 96 / 6 / 12 (n=81) | 43 / 6 / 10 (n=35) | 59 / 25 / 35 (n=39) | 80 / 7 / 13 (n=5) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_dense | 21 / 20 / 21 (n=236) | 19 / 3 / 5 (n=176) | 61 / 8 / 14 (n=228) | 1 / 0 / 1 (n=78) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | 0 / 0 / - (n=1) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_dense: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 0 | - | 0% [0, 0] |
| video_dense | 15 | 0 | - | 0% [0, 0] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +36 [+28, +43], p=6e-05 | +9 [+6, +13], p=6e-05 | +48 [+39, +57], p=6e-05 | +26 [+17, +34], p=0.00043 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
