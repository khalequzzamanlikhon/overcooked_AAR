# Study v2 metrics: qwen25vl7b_4bit (Qwen2.5-VL-7B-Instruct 4-bit)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| blind | 222 | 73% [63, 81] | 75% [62, 86] | 2% [2, 3] | 8% [7, 10] | 1% [0, 2] | 49% [45, 53] (50%) | 1.2 [0.9, 1.7] |
| telemetry | 779 | 67% [62, 71] | 67% [62, 71] | 15% [12, 20] | 54% [48, 61] | 71% [57, 83] | 80% [74, 85] (51%) | 0.2 [0.0, 0.5] |
| video_dense | 783 | 30% [22, 38] | 29% [20, 38] | 5% [4, 7] | 19% [14, 25] | 13% [8, 19] | 61% [52, 69] (55%) | 1.5 [1.2, 2.1] |
| video_sparse | 362 | 22% [14, 32] | 22% [14, 32] | 2% [2, 3] | 8% [5, 12] | 8% [4, 12] | 58% [49, 67] (51%) | 1.8 [1.1, 3.0] |
| video_log | 769 | 68% [64, 72] | 68% [64, 72] | 16% [12, 20] | 56% [51, 62] | 67% [57, 76] | 86% [81, 90] (50%) | 0.0 [0.0, 0.3] |
| state_text | 576 | 24% [16, 32] | 24% [16, 32] | 4% [3, 5] | 14% [8, 20] | 20% [13, 28] | 65% [58, 71] (54%) | 1.2 [0.8, 1.8] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| blind | 73% [63, 81] | 83% [76, 89] | -0.061 | 98% [97, 100] | 97% [94, 100] |
| telemetry | 67% [62, 71] | 48% [42, 53] | 0.131 | 94% [90, 97] | 72% [62, 82] |
| video_dense | 30% [22, 38] | 36% [28, 45] | -0.075 | 59% [45, 73] | 53% [42, 64] |
| video_sparse | 22% [14, 32] | 26% [17, 35] | -0.030 | 44% [31, 56] | 41% [29, 51] |
| video_log | 68% [64, 72] | 49% [43, 54] | 0.133 | 96% [94, 98] | 70% [60, 79] |
| state_text | 24% [16, 32] | 35% [25, 45] | -0.121 | 80% [69, 90] | 68% [54, 80] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| blind | 0% [0, 0] | 26% [18, 36] | 1% [0, 3] | 62% [55, 68] | 0% [0, 0] | 0% [0, 0] | 2% [0, 6] |
| telemetry | 13% [9, 18] | 14% [9, 19] | 6% [3, 10] | 100% [100, 100] | 70% [62, 79] | 0% [0, 0] | 11% [6, 16] |
| video_dense | 11% [8, 14] | 20% [14, 27] | 39% [26, 51] | 53% [50, 55] | 21% [14, 28] | 0% [0, 0] | 3% [1, 6] |
| video_sparse | 2% [0, 7] | 19% [11, 29] | 56% [44, 69] | 29% [29, 29] | 33% [22, 44] | 0% [0, 0] | 3% [0, 9] |
| video_log | 15% [11, 19] | 13% [9, 18] | 4% [2, 6] | 50% [0, 100] | 75% [69, 83] | 0% [0, 0] | 14% [9, 19] |
| state_text | 33% [25, 40] | 24% [13, 37] | 20% [10, 31] | 0% [0, 0] | 31% [20, 42] | 0% [0, 0] | 15% [7, 26] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| blind | 5.24 [4.29, 6.53] | -5.24 [-6.53, -4.29] | 0% [0, 0] | 7% [0, 13] | 0.353 | 100% [100, 100] | 40% [22, 58] | 100% [100, 100] | 0 |
| telemetry | 2.18 [1.29, 3.49] | -0.44 [-2.16, 0.80] | 31% [18, 44] | 13% [2, 27] | 2.542 | 2% [1, 3] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 2.80 [2.09, 3.69] | -2.11 [-3.16, -1.25] | 7% [0, 18] | 20% [11, 31] | 2.285 | 27% [23, 31] | 18% [4, 31] | 66% [45, 86] | 0 |
| video_sparse | 3.69 [2.84, 4.87] | -3.69 [-4.87, -2.84] | 2% [0, 7] | 67% [49, 82] | 1.476 | 54% [43, 65] | 0% [0, 0] | 67% [54, 81] | 0 |
| video_log | 4.46 [3.60, 5.67] | -1.33 [-3.30, 0.53] | 3% [0, 8] | 54% [34, 72] | 1.802 | 3% [2, 4] | 0% [0, 0] | 0% [0, 0] | 0 |
| state_text | 4.18 [3.24, 5.47] | -4.18 [-5.47, -3.24] | 0% [0, 0] | 27% [16, 38] | 1.683 | 2% [2, 3] | 0% [0, 0] | 10% [0, 20] | 0 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| blind | 67 / 1 / 2 (n=3) | 0 / 0 / - (n=3) | 74 / 7 / 13 (n=216) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| telemetry | 55 / 71 / 62 (n=307) | 69 / 15 / 25 (n=277) | 93 / 8 / 15 (n=119) | 56 / 8 / 13 (n=36) | 81 / 24 / 37 (n=27) | 67 / 7 / 13 (n=6) | - / 0 / - (n=0) | 0 / 0 / - (n=3) | - / 0 / - (n=0) |
| video_dense | 22 / 13 / 16 (n=139) | 10 / 3 / 4 (n=341) | 60 / 11 / 19 (n=285) | 0 / 0 / - (n=18) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_sparse | 38 / 8 / 13 (n=47) | 17 / 3 / 6 (n=251) | 37 / 1 / 3 (n=54) | 0 / 0 / - (n=10) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_log | 52 / 67 / 59 (n=307) | 74 / 17 / 27 (n=292) | 95 / 8 / 15 (n=97) | 69 / 10 / 18 (n=39) | 81 / 19 / 30 (n=21) | 100 / 11 / 19 (n=6) | - / 0 / - (n=0) | 0 / 0 / - (n=1) | 50 / 1 / 3 (n=2) |
| state_text | 21 / 20 / 21 (n=224) | 25 / 4 / 8 (n=227) | 50 / 1 / 3 (n=46) | 0 / 0 / - (n=8) | - / 0 / - (n=0) | 8 / 7 / 7 (n=50) | - / 0 / - (n=0) | 0 / 0 / - (n=4) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- blind: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- telemetry: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0
- video_dense: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_sparse: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_log: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion 100/1 vs 50/3
- state_text: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| blind | 15 | 0 | - | 0% [0, 0] |
| telemetry | 15 | 3 | 0% [0, 0] | 7% [0, 20] |
| video_dense | 15 | 2 | 100% [100, 100] | 0% [0, 0] |
| video_sparse | 15 | 2 | 50% [50, 50] | 0% [0, 0] |
| video_log | 15 | 0 | - | 0% [0, 0] |
| state_text | 15 | 5 | 60% [0, 100] | 7% [0, 20] |
| oracle | 15 | 2 | 0% [0, 0] | 0% [0, 0] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +37 [+26, +46], p=0.00012 | +10 [+6, +14], p=6e-05 | +58 [+47, +70], p=6e-05 | +19 [+8, +30], p=0.0124 |
| telemetry - video_sparse | +45 [+33, +54], p=0.00012 | +13 [+9, +18], p=6e-05 | +63 [+51, +76], p=0.00065 | +22 [+10, +33], p=0.0266 |
| telemetry - blind | -6 [-17, +5], p=0.454 | +13 [+10, +17], p=6e-05 | +70 [+57, +82], p=6e-05 | +31 [+23, +38], p=6e-05 |
| video_dense - blind | -43 [-55, -30], p=6e-05 | +3 [+2, +4], p=0.00492 | +12 [+7, +18], p=0.00194 | +12 [+1, +23], p=0.169 |
| video_sparse - blind | -50 [-62, -37], p=0.00012 | -0 [-1, +1], p=0.268 | +7 [+3, +11], p=0.00945 | +9 [-2, +21], p=0.244 |
| video_dense - video_sparse | +8 [-3, +19], p=0.188 | +3 [+2, +5], p=0.00197 | +5 [+2, +10], p=0.0305 | +3 [-6, +9], p=0.685 |
| video_log - telemetry | +1 [-4, +7], p=0.599 | +1 [-1, +3], p=0.847 | -4 [-20, +15], p=0.118 | +6 [+3, +9], p=0.00085 |
| video_log - video_dense | +38 [+27, +48], p=0.00012 | +10 [+7, +15], p=0.00012 | +54 [+39, +67], p=6e-05 | +24 [+15, +35], p=0.00061 |
| state_text - telemetry | -43 [-52, -33], p=6e-05 | -11 [-17, -8], p=0.00012 | -51 [-65, -36], p=6e-05 | -15 [-22, -8], p=0.00427 |
| state_text - video_dense | -6 [-16, +4], p=0.208 | -2 [-4, +0], p=0.0649 | +7 [-3, +17], p=0.57 | +4 [-8, +17], p=0.89 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
