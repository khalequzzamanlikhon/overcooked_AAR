# Study v2 metrics: qwen3vl8b_bf16_seed1 (Qwen3-VL-8B-Instruct)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 899 | 93% [91, 95] | 95% [93, 97] | 25% [20, 32] | 89% [87, 91] | 93% [89, 97] | 99% [98, 100] (51%) | 0.0 [0.0, 0.0] |
| video_dense | 665 | 50% [43, 57] | 48% [40, 55] | 7% [5, 10] | 25% [19, 31] | 15% [6, 25] | 56% [50, 62] (50%) | 1.1 [0.8, 1.4] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 93% [91, 95] | 54% [49, 59] | 0.315 | 98% [97, 100] | 71% [62, 80] |
| video_dense | 50% [43, 57] | 53% [45, 61] | -0.041 | 78% [70, 86] | 73% [60, 83] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 2% [1, 3] | 3% [1, 5] | 2% [1, 3] | 82% [74, 93] | 99% [97, 100] | 0% [0, 0] | 10% [3, 19] |
| video_dense | 13% [8, 18] | 18% [11, 24] | 20% [13, 28] | 63% [36, 74] | 49% [39, 61] | 0% [0, 0] | 11% [6, 16] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 0.91 [0.62, 1.20] | 0.73 [0.29, 1.11] | 36% [20, 53] | 2% [0, 7] | 2.988 | 2% [1, 2] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 4.00 [2.83, 5.47] | -4.00 [-5.47, -2.83] | 3% [0, 8] | 0% [0, 0] | 1.216 | 23% [19, 31] | 0% [0, 0] | 12% [3, 22] | 6 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 89 / 93 / 91 (n=251) | 99 / 14 / 24 (n=174) | 96 / 32 / 48 (n=376) | 55 / 6 / 12 (n=31) | 100 / 48 / 65 (n=44) | 100 / 40 / 57 (n=23) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_dense | 50 / 15 / 23 (n=70) | 37 / 5 / 9 (n=168) | 69 / 13 / 21 (n=334) | 3 / 1 / 1 (n=65) | 0 / 0 / - (n=2) | 10 / 4 / 5 (n=21) | 0 / 0 / - (n=5) | - / 0 / - (n=0) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_dense: waiting 0/0 vs 0/-; handoff -/0 vs -/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 97 | 27% [19, 37] | 40% [20, 67] |
| video_dense | 15 | 75 | 60% [51, 72] | 7% [0, 20] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +43 [+36, +50], p=0.00012 | +18 [+14, +23], p=6e-05 | +79 [+68, +88], p=0.00062 | +43 [+37, +49], p=0.00012 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
