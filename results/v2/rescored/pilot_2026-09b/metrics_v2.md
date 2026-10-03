# Study v2 metrics: pilot_2026-09b (Qwen2.5-VL-7B-Instruct 4-bit)

Episodes: 15. Claim cap per minute: 8. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 320 | 69% [64, 73] | 69% [64, 73] | 8% [6, 10] | 61% [50, 72] | 62% [53, 73] | 81% [74, 88] (53%) | 0.7 [0.6, 1.2] |
| video_dense | 395 | 40% [31, 49] | 36% [28, 44] | 5% [4, 7] | 44% [32, 58] | 24% [17, 33] | 49% [44, 54] (50%) | 2.4 [1.9, 3.1] |
| video_sparse | 322 | 47% [37, 56] | 46% [36, 56] | 5% [4, 6] | 41% [31, 52] | 18% [11, 25] | 53% [45, 61] (51%) | 1.8 [1.5, 2.7] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 69% [64, 73] | 39% [33, 46] | 0.208 | 96% [93, 99] | 62% [42, 78] |
| video_dense | 40% [31, 49] | 40% [31, 50] | 0.003 | 75% [67, 83] | 72% [65, 79] |
| video_sparse | 47% [37, 56] | 44% [34, 52] | 0.034 | 80% [70, 90] | 71% [63, 80] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 8% [5, 12] | 20% [14, 26] | 3% [1, 7] | 67% [62, 100] | 82% [72, 95] | 0% [0, 0] | 8% [2, 16] |
| video_dense | 4% [2, 6] | 34% [27, 42] | 22% [14, 30] | 76% [63, 100] | 62% [47, 75] | 0% [0, 0] | 2% [0, 5] |
| video_sparse | 0% [0, 1] | 34% [29, 41] | 18% [9, 28] | 61% [33, 81] | 60% [48, 71] | 0% [0, 0] | 2% [0, 4] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 2.40 [1.49, 3.69] | -0.89 [-2.53, 0.29] | 22% [9, 36] | 11% [2, 22] | 2.644 | 2% [1, 3] | 4% [0, 13] | 0% [0, 0] | 0 |
| video_dense | 3.19 [2.42, 4.31] | -2.86 [-4.05, -1.95] | 7% [0, 15] | 38% [26, 51] | 2.036 | 63% [52, 76] | 0% [0, 0] | 74% [58, 89] | 2 |
| video_sparse | 4.20 [3.20, 5.51] | -4.20 [-5.51, -3.20] | 0% [0, 0] | 84% [71, 96] | 0.866 | 43% [36, 50] | 0% [0, 0] | 51% [33, 69] | 0 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle |
|---|---|---|---|---|---|---|
| telemetry | 64 / 62 / 63 (n=233) | 81 / 5 / 9 (n=73) | 100 / 0 / 0 (n=1) | 100 / 1 / 2 (n=2) | 100 / 10 / 18 (n=9) | 50 / 2 / 3 (n=2) |
| video_dense | 28 / 24 / 26 (n=206) | 55 / 8 / 14 (n=182) | 20 / 0 / 0 (n=5) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_sparse | 36 / 18 / 24 (n=117) | 54 / 8 / 15 (n=200) | 100 / 0 / - (n=1) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 4 | 25% [0, 33] | 20% [0, 40] |
| video_dense | 15 | 9 | 33% [0, 100] | 13% [0, 33] |
| video_sparse | 15 | 4 | 25% [0, 50] | 7% [0, 20] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +29 [+18, +39], p=0.00012 | +2 [-0, +5], p=0.0408 | +38 [+29, +48], p=0.00073 | +32 [+23, +42], p=0.00012 |
| telemetry - video_sparse | +22 [+10, +34], p=0.00336 | +2 [+0, +5], p=0.0554 | +44 [+35, +55], p=6e-05 | +28 [+18, +38], p=0.00018 |
| video_dense - video_sparse | -7 [-14, -0], p=0.0637 | +0 [-1, +1], p=0.41 | +6 [-1, +13], p=0.105 | -4 [-13, +5], p=0.599 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
