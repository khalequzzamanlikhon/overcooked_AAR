# Study v2 metrics: qwen25vl7b_bf16_seed1 (Qwen2.5-VL-7B-Instruct)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 856 | 72% [68, 75] | 71% [67, 75] | 17% [14, 22] | 62% [58, 66] | 72% [61, 84] | 80% [74, 86] (50%) | 0.1 [0.0, 0.4] |
| video_dense | 398 | 50% [43, 58] | 45% [37, 54] | 4% [2, 7] | 15% [8, 23] | 17% [8, 28] | 54% [49, 60] (51%) | 1.4 [1.1, 2.0] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 72% [68, 75] | 49% [45, 53] | 0.174 | 91% [87, 95] | 71% [62, 81] |
| video_dense | 50% [43, 58] | 48% [41, 54] | 0.014 | 78% [68, 88] | 74% [63, 84] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 6% [4, 9] | 13% [10, 18] | 9% [5, 13] | 88% [71, 100] | 83% [76, 89] | 0% [0, 0] | 6% [2, 12] |
| video_dense | 6% [1, 11] | 25% [18, 32] | 19% [11, 28] | 100% [100, 100] | 59% [32, 75] | 0% [0, 0] | 4% [0, 11] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 1.87 [1.04, 2.98] | -0.13 [-0.80, 0.47] | 36% [22, 51] | 0% [0, 0] | 2.072 | 2% [1, 3] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 2.41 [1.70, 3.03] | -1.67 [-2.48, -0.85] | 7% [0, 25] | 26% [8, 44] | 1.623 | 36% [27, 45] | 0% [0, 0] | 38% [25, 50] | 18 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 57 / 72 / 64 (n=305) | 81 / 15 / 26 (n=237) | 92 / 15 / 26 (n=220) | 26 / 6 / 9 (n=58) | 80 / 18 / 29 (n=20) | 89 / 14 / 24 (n=9) | - / 0 / - (n=0) | 0 / 0 / - (n=1) | 67 / 3 / 5 (n=3) |
| video_dense | 30 / 17 / 22 (n=136) | 41 / 1 / 3 (n=44) | 66 / 8 / 14 (n=213) | 0 / 0 / - (n=4) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | 0 / 0 / - (n=1) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion 100/1 vs 0/0
- video_dense: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 4 | 0% [0, 0] | 0% [0, 0] |
| video_dense | 15 | 0 | - | 0% [0, 0] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +21 [+13, +30], p=0.00391 | +13 [+10, +18], p=6e-05 | +55 [+46, +66], p=0.00065 | +26 [+18, +33], p=0.00781 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
