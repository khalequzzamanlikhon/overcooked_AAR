# Study v2 metrics: qwen3vl8b_bf16 (Qwen3-VL-8B-Instruct)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| blind | 60 | 37% [15, 50] | 37% [15, 50] | 0% [0, 1] | 1% [0, 3] | 0% [0, 1] | 46% [42, 50] (49%) | 1.3 [1.1, 5.0] |
| telemetry | 898 | 93% [92, 95] | 95% [94, 97] | 25% [20, 33] | 90% [88, 92] | 98% [96, 100] | 99% [98, 100] (51%) | 0.0 [0.0, 0.0] |
| video_dense | 535 | 43% [32, 53] | 42% [30, 53] | 5% [3, 8] | 18% [11, 25] | 16% [4, 32] | 58% [51, 69] (50%) | 1.1 [0.9, 1.7] |
| video_sparse | 680 | 37% [26, 50] | 41% [29, 55] | 5% [4, 7] | 18% [14, 23] | 6% [2, 12] | 53% [51, 56] (50%) | 1.5 [0.9, 2.1] |
| video_log | 615 | 96% [94, 97] | 98% [96, 99] | 18% [11, 25] | 63% [43, 81] | 62% [36, 89] | 99% [98, 100] (54%) | 0.0 [0.0, 0.0] |
| state_text | 897 | 49% [40, 58] | 48% [38, 57] | 9% [8, 11] | 34% [27, 41] | 47% [38, 57] | 68% [62, 73] (50%) | 0.7 [0.6, 1.0] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| blind | 37% [15, 50] | 41% [28, 51] | -0.040 | 62% [60, 65] | 58% [55, 65] |
| telemetry | 93% [92, 95] | 54% [49, 58] | 0.320 | 99% [98, 100] | 74% [65, 83] |
| video_dense | 43% [32, 53] | 53% [39, 65] | -0.093 | 78% [67, 88] | 67% [49, 82] |
| video_sparse | 37% [26, 50] | 50% [39, 61] | -0.128 | 74% [62, 85] | 73% [61, 85] |
| video_log | 96% [94, 97] | 56% [51, 61] | 0.318 | 99% [99, 100] | 76% [62, 87] |
| state_text | 49% [40, 58] | 43% [36, 50] | 0.023 | 73% [66, 80] | 61% [54, 67] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| blind | 0% [0, 0] | 25% [10, 45] | 38% [35, 40] | - | 33% [0, 50] | 0% [0, 0] | 0% [0, 0] |
| telemetry | 2% [1, 3] | 4% [2, 5] | 1% [0, 2] | 80% [71, 88] | 99% [96, 100] | 0% [0, 0] | 10% [4, 16] |
| video_dense | 20% [12, 27] | 16% [9, 25] | 21% [12, 32] | 51% [19, 80] | 47% [31, 70] | 0% [0, 0] | 15% [4, 28] |
| video_sparse | 14% [6, 24] | 22% [14, 32] | 26% [16, 36] | 16% [8, 28] | 43% [37, 49] | 0% [0, 0] | 14% [4, 24] |
| video_log | 1% [0, 2] | 3% [2, 4] | 0% [0, 1] | 78% [61, 92] | 99% [97, 100] | 0% [0, 0] | 11% [0, 29] |
| state_text | 11% [8, 15] | 13% [8, 18] | 27% [20, 34] | 61% [43, 80] | 69% [61, 76] | 0% [0, 0] | 7% [3, 11] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| blind | 5.31 [4.36, 6.58] | -5.31 [-6.58, -4.36] | 0% [0, 0] | 0% [0, 0] | -0.0 | 20% [20, 20] | 0% [0, 0] | 0% [0, 0] | 0 |
| telemetry | 0.91 [0.64, 1.18] | 0.78 [0.38, 1.13] | 33% [18, 51] | 2% [0, 7] | 2.962 | 2% [1, 3] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 3.28 [2.29, 4.27] | -3.22 [-4.24, -2.19] | 6% [0, 14] | 0% [0, 0] | 1.541 | 26% [21, 33] | 0% [0, 0] | 30% [11, 52] | 9 |
| video_sparse | 4.36 [3.33, 5.78] | -4.36 [-5.78, -3.33] | 0% [0, 0] | 0% [0, 0] | 1.126 | 64% [54, 74] | 0% [0, 0] | 75% [61, 89] | 0 |
| video_log | 0.78 [0.38, 1.19] | 0.78 [0.38, 1.19] | 50% [29, 72] | 3% [0, 10] | 2.938 | 1% [1, 2] | 0% [0, 0] | 0% [0, 0] | 13 |
| state_text | 3.20 [2.20, 4.51] | -3.20 [-4.51, -2.20] | 7% [0, 13] | 2% [0, 7] | 1.651 | 3% [2, 5] | 0% [0, 0] | 0% [0, 0] | 0 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| blind | 33 / 0 / 1 (n=3) | 25 / 0 / 1 (n=24) | 83 / 1 / 1 (n=18) | 0 / 0 / - (n=6) | - / 0 / - (n=0) | - / 0 / - (n=0) | 0 / 0 / - (n=6) | 0 / 0 / - (n=3) | - / 0 / - (n=0) |
| telemetry | 89 / 98 / 93 (n=264) | 99 / 16 / 27 (n=202) | 94 / 32 / 48 (n=364) | 71 / 6 / 11 (n=21) | 100 / 32 / 48 (n=29) | 100 / 32 / 48 (n=18) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_dense | 52 / 16 / 24 (n=73) | 23 / 2 / 3 (n=104) | 54 / 10 / 16 (n=306) | 2 / 0 / 1 (n=40) | 100 / 1 / 2 (n=1) | 25 / 4 / 6 (n=8) | 0 / 0 / - (n=3) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_sparse | 27 / 6 / 10 (n=56) | 23 / 3 / 5 (n=164) | 55 / 11 / 18 (n=358) | 1 / 0 / 1 (n=68) | 0 / 0 / - (n=4) | 8 / 2 / 3 (n=12) | 0 / 0 / - (n=6) | 33 / 0 / 1 (n=3) | 0 / 0 / - (n=5) |
| video_log | 94 / 62 / 75 (n=158) | 99 / 12 / 22 (n=159) | 95 / 23 / 37 (n=268) | 86 / 5 / 9 (n=14) | 100 / 10 / 18 (n=9) | 100 / 12 / 22 (n=7) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| state_text | 70 / 47 / 56 (n=162) | 38 / 4 / 6 (n=120) | 69 / 13 / 22 (n=378) | 8 / 5 / 6 (n=173) | 67 / 2 / 4 (n=3) | 7 / 2 / 3 (n=15) | 0 / 0 / - (n=21) | 0 / 0 / - (n=16) | 0 / 0 / - (n=1) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- blind: waiting 33/3 vs 0/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0
- telemetry: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_dense: waiting 33/1 vs 0/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_sparse: waiting 0/0 vs 0/-; handoff 33/0 vs 33/0; congestion 0/0 vs 0/0
- video_log: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- state_text: waiting 19/5 vs 0/-; handoff 0/0 vs 0/0; congestion 0/0 vs 0/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| blind | 15 | 25 | 72% [50, 100] | 0% [0, 0] |
| telemetry | 15 | 88 | 28% [17, 40] | 47% [20, 73] |
| video_dense | 15 | 54 | 67% [41, 85] | 27% [7, 47] |
| video_sparse | 15 | 56 | 59% [46, 71] | 7% [0, 20] |
| video_log | 15 | 84 | 46% [29, 63] | 20% [0, 40] |
| state_text | 15 | 80 | 54% [35, 70] | 20% [0, 40] |
| oracle | 15 | 100 | 21% [15, 27] | 47% [20, 73] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +50 [+40, +60], p=0.00049 | +20 [+16, +26], p=6e-05 | +82 [+66, +94], p=0.00066 | +41 [+30, +48], p=0.00195 |
| telemetry - video_sparse | +56 [+44, +67], p=6e-05 | +20 [+16, +26], p=6e-05 | +92 [+86, +96], p=0.0006 | +46 [+42, +48], p=0.00064 |
| telemetry - blind | +57 [+43, +78] | +25 [+20, +32], p=6e-05 | +97 [+95, +100], p=0.00036 | +53 [+48, +58] |
| video_dense - blind | +7 [-8, +24] | +5 [+3, +7], p=0.0012 | +15 [+3, +32], p=0.0603 | +12 [+1, +25] |
| video_sparse - blind | +1 [-17, +22] | +5 [+3, +6], p=6e-05 | +6 [+1, +12], p=0.123 | +7 [+1, +13] |
| video_dense - video_sparse | +6 [-9, +19], p=0.11 | -0 [-3, +3], p=0.977 | +10 [+1, +22], p=0.204 | +4 [-2, +15], p=0.519 |
| video_log - telemetry | +2 [+1, +4], p=0.00977 | -8 [-14, -3], p=0.0833 | -36 [-62, -8], p=0.0954 | -0 [-2, +1], p=1 |
| video_log - video_dense | +52 [+42, +63], p=0.00049 | +12 [+8, +18], p=0.0012 | +46 [+23, +72], p=0.00511 | +41 [+30, +48], p=0.00195 |
| state_text - telemetry | -44 [-54, -35], p=0.00065 | -16 [-23, -11], p=6e-05 | -51 [-60, -41], p=6e-05 | -31 [-37, -26], p=6e-05 |
| state_text - video_dense | +5 [-6, +19], p=0.569 | +4 [+1, +7], p=0.0413 | +31 [+16, +45], p=0.00976 | +10 [-1, +18], p=0.424 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
