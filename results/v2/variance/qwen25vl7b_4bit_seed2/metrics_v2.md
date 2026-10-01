# Study v2 metrics: qwen25vl7b_4bit_seed2 (Qwen2.5-VL-7B-Instruct 4-bit)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 693 | 71% [65, 76] | 72% [66, 78] | 15% [11, 20] | 52% [43, 62] | 73% [61, 85] | 79% [75, 84] (50%) | 0.3 [0.0, 0.6] |
| video_dense | 732 | 34% [27, 41] | 31% [23, 40] | 5% [4, 7] | 19% [16, 21] | 24% [18, 32] | 51% [49, 54] (50%) | 1.6 [1.4, 2.1] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 71% [65, 76] | 46% [40, 52] | 0.183 | 94% [90, 98] | 70% [61, 78] |
| video_dense | 34% [27, 41] | 37% [29, 45] | -0.039 | 69% [58, 79] | 64% [53, 74] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 9% [7, 11] | 15% [11, 18] | 6% [2, 9] | 51% [35, 69] | 83% [78, 89] | 0% [0, 0] | 15% [8, 22] |
| video_dense | 12% [8, 16] | 25% [20, 31] | 29% [20, 40] | 82% [64, 94] | 18% [10, 29] | 0% [0, 0] | 2% [1, 4] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 1.56 [1.11, 2.20] | 0.53 [-0.44, 1.22] | 22% [13, 31] | 0% [0, 0] | 2.06 | 2% [1, 4] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 3.07 [2.24, 4.07] | -2.18 [-3.49, -0.98] | 0% [0, 0] | 0% [0, 0] | 1.583 | 28% [24, 32] | 0% [0, 0] | 65% [47, 82] | 0 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 59 / 73 / 66 (n=295) | 82 / 16 / 27 (n=246) | 98 / 6 / 12 (n=81) | 24 / 3 / 6 (n=37) | 80 / 22 / 34 (n=25) | 50 / 2 / 3 (n=2) | - / 0 / - (n=0) | 0 / 0 / - (n=3) | - / 0 / - (n=0) |
| video_dense | 23 / 24 / 23 (n=257) | 9 / 1 / 2 (n=178) | 62 / 9 / 16 (n=273) | 5 / 0 / 1 (n=21) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | 0 / 0 / - (n=1) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0
- video_dense: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 8 | 0% [0, 0] | 0% [0, 0] |
| video_dense | 15 | 3 | 33% [0, 100] | 7% [0, 20] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +37 [+30, +43], p=0.00012 | +9 [+6, +13], p=6e-05 | +49 [+38, +62], p=6e-05 | +28 [+23, +33], p=6e-05 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
