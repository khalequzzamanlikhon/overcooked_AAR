# Study v2 metrics: qwen25vl7b_4bit_seed3 (Qwen2.5-VL-7B-Instruct 4-bit)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 775 | 69% [63, 75] | 69% [63, 74] | 16% [13, 20] | 57% [50, 64] | 72% [62, 82] | 81% [74, 87] (50%) | 0.2 [0.0, 0.5] |
| video_dense | 522 | 50% [42, 59] | 52% [43, 61] | 6% [6, 7] | 23% [18, 29] | 28% [22, 34] | 55% [50, 61] (50%) | 1.7 [1.4, 2.0] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 69% [63, 75] | 45% [40, 50] | 0.177 | 94% [88, 97] | 72% [62, 82] |
| video_dense | 50% [42, 59] | 49% [41, 57] | 0.001 | 82% [75, 88] | 78% [72, 84] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 9% [6, 12] | 16% [10, 22] | 6% [3, 12] | 80% [33, 100] | 81% [70, 92] | 0% [0, 0] | 5% [3, 9] |
| video_dense | 5% [3, 8] | 25% [20, 32] | 19% [13, 25] | 33% [25, 67] | 53% [38, 74] | 0% [0, 0] | 2% [0, 4] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 3.02 [2.18, 3.78] | 0.89 [-0.27, 1.91] | 23% [9, 40] | 14% [4, 25] | 2.399 | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 4.07 [3.27, 5.05] | -4.07 [-5.05, -3.27] | 2% [0, 7] | 93% [85, 100] | 0.484 | 36% [30, 43] | 0% [0, 0] | 29% [17, 40] | 0 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 54 / 72 / 62 (n=316) | 81 / 17 / 28 (n=269) | 90 / 8 / 14 (n=101) | 49 / 8 / 14 (n=43) | 67 / 22 / 33 (n=30) | 100 / 7 / 13 (n=4) | - / 0 / - (n=0) | - / 0 / - (n=0) | 0 / 0 / - (n=1) |
| video_dense | 37 / 28 / 32 (n=182) | 51 / 6 / 11 (n=150) | 74 / 7 / 12 (n=163) | 0 / 0 / - (n=14) | - / 0 / - (n=0) | - / 0 / - (n=0) | 0 / 0 / - (n=2) | 0 / 0 / - (n=11) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion 0/0 vs 0/0
- video_dense: waiting 0/0 vs 0/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 0 | - | 7% [0, 20] |
| video_dense | 15 | 0 | - | 0% [0, 0] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +18 [+10, +27], p=0.00201 | +9 [+6, +13], p=6e-05 | +44 [+33, +56], p=6e-05 | +26 [+18, +34], p=0.00031 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
