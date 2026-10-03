# Study v2 metrics: pilot_2026-09 (Qwen2.5-VL-7B-Instruct 4-bit)

Episodes: 15. Claim cap per minute: 8. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 351 | 69% [64, 74] | 69% [64, 74] | 8% [6, 11] | 67% [55, 78] | 66% [56, 78] | 83% [76, 90] (55%) | 0.8 [0.6, 1.2] |
| video_dense | 411 | 48% [43, 54] | 48% [42, 54] | 7% [6, 8] | 55% [47, 63] | 24% [18, 30] | 56% [50, 62] (50%) | 2.4 [1.8, 3.1] |
| video_sparse | 378 | 54% [46, 61] | 47% [38, 57] | 7% [5, 9] | 55% [46, 64] | 13% [9, 18] | 51% [44, 58] (50%) | 1.9 [1.4, 2.2] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 69% [64, 74] | 39% [33, 46] | 0.208 | 97% [94, 99] | 59% [40, 76] |
| video_dense | 48% [43, 54] | 44% [36, 51] | 0.052 | 91% [86, 95] | 85% [77, 92] |
| video_sparse | 54% [46, 61] | 55% [49, 62] | -0.011 | 87% [78, 94] | 84% [76, 91] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 11% [6, 18] | 17% [12, 22] | 3% [1, 6] | 70% [62, 100] | 80% [71, 95] | 0% [0, 0] | 7% [2, 13] |
| video_dense | 0% [0, 0] | 43% [36, 51] | 9% [5, 13] | 62% [50, 75] | 79% [73, 85] | 0% [0, 0] | 1% [0, 3] |
| video_sparse | 0% [0, 0] | 36% [28, 44] | 10% [4, 17] | 75% [66, 84] | 72% [62, 80] | 0% [0, 0] | 1% [0, 2] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 2.13 [1.36, 3.04] | -1.24 [-2.42, -0.22] | 29% [16, 42] | 13% [4, 24] | 2.588 | 1% [0, 2] | 4% [0, 13] | 0% [0, 0] | 0 |
| video_dense | 3.96 [2.91, 5.31] | -3.96 [-5.31, -2.91] | 9% [0, 20] | 89% [78, 98] | 0.503 | 98% [94, 100] | 20% [4, 38] | 95% [89, 100] | 0 |
| video_sparse | 4.56 [3.62, 5.80] | -4.56 [-5.80, -3.62] | 0% [0, 0] | 73% [67, 80] | 0.837 | 79% [71, 85] | 0% [0, 0] | 81% [69, 94] | 0 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle |
|---|---|---|---|---|---|---|
| telemetry | 65 / 66 / 65 (n=243) | 76 / 6 / 10 (n=94) | 100 / 0 / 0 (n=1) | 100 / 0 / 1 (n=1) | 100 / 11 / 20 (n=10) | 50 / 2 / 3 (n=2) |
| video_dense | 27 / 24 / 25 (n=208) | 70 / 11 / 19 (n=202) | 100 / 0 / 0 (n=1) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_sparse | 30 / 13 / 18 (n=105) | 64 / 12 / 21 (n=248) | 59 / 1 / 2 (n=22) | 33 / 0 / 1 (n=3) | - / 0 / - (n=0) | - / 0 / - (n=0) |

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 5 | 0% [0, 0] | 20% [0, 40] |
| video_dense | 15 | 4 | 25% [0, 50] | 0% [0, 0] |
| video_sparse | 15 | 1 | 0% [0, 0] | 0% [0, 0] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +20 [+13, +27], p=0.00018 | +1 [-0, +3], p=0.0832 | +42 [+32, +54], p=0.00073 | +27 [+18, +35], p=6e-05 |
| telemetry - video_sparse | +15 [+7, +23], p=0.00336 | +1 [-0, +4], p=0.379 | +53 [+45, +62], p=0.00065 | +32 [+23, +40], p=6e-05 |
| video_dense - video_sparse | -6 [-13, +2], p=0.135 | -0 [-1, +1], p=0.41 | +10 [+5, +15], p=0.0064 | +5 [-2, +13], p=0.164 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
