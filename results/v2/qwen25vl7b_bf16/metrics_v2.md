# Study v2 metrics: qwen25vl7b_bf16 (Qwen2.5-VL-7B-Instruct)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| blind | 252 | 69% [61, 75] | 79% [70, 86] | 3% [2, 3] | 10% [8, 11] | 0% [0, 0] | 45% [39, 51] (50%) | 1.4 [1.1, 2.0] |
| telemetry | 809 | 69% [64, 74] | 70% [64, 75] | 16% [13, 21] | 58% [50, 66] | 76% [67, 85] | 82% [76, 87] (50%) | 0.0 [0.0, 0.0] |
| video_dense | 709 | 34% [27, 41] | 33% [26, 40] | 5% [4, 7] | 19% [15, 23] | 27% [18, 35] | 56% [50, 63] (51%) | 1.7 [1.3, 2.1] |
| video_sparse | 437 | 34% [26, 42] | 33% [25, 41] | 4% [3, 5] | 13% [10, 15] | 13% [8, 18] | 53% [48, 59] (50%) | 1.8 [1.5, 3.0] |
| video_log | 804 | 67% [61, 73] | 68% [62, 74] | 16% [12, 22] | 58% [50, 65] | 74% [62, 85] | 84% [75, 90] (50%) | 0.0 [0.0, 0.3] |
| state_text | 332 | 35% [24, 49] | 36% [24, 51] | 3% [2, 4] | 11% [6, 16] | 18% [9, 28] | 76% [66, 85] (51%) | 1.2 [0.9, 1.8] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| blind | 69% [61, 75] | 73% [67, 78] | -0.031 | 100% [98, 100] | 100% [98, 100] |
| telemetry | 69% [64, 74] | 49% [43, 55] | 0.154 | 93% [91, 96] | 72% [62, 82] |
| video_dense | 34% [27, 41] | 46% [38, 55] | -0.136 | 79% [70, 87] | 75% [68, 83] |
| video_sparse | 34% [26, 42] | 52% [44, 60] | -0.164 | 76% [66, 84] | 74% [63, 84] |
| video_log | 67% [61, 73] | 44% [39, 50] | 0.174 | 94% [88, 98] | 72% [60, 84] |
| state_text | 35% [24, 49] | 44% [30, 58] | -0.108 | 89% [77, 97] | 65% [45, 85] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| blind | 0% [0, 0] | 25% [19, 33] | 6% [5, 7] | 22% [13, 29] | - | 0% [0, 0] | 1% [0, 4] |
| telemetry | 11% [7, 16] | 14% [10, 18] | 7% [4, 9] | 48% [0, 67] | 81% [75, 88] | 0% [0, 0] | 11% [3, 22] |
| video_dense | 23% [15, 31] | 22% [17, 28] | 21% [12, 29] | 65% [65, 65] | 28% [19, 39] | 0% [0, 0] | 8% [3, 15] |
| video_sparse | 13% [4, 23] | 30% [20, 41] | 24% [16, 33] | 88% [88, 88] | 36% [28, 45] | 0% [0, 0] | 0% [0, 0] |
| video_log | 10% [7, 13] | 17% [12, 22] | 6% [2, 11] | 38% [7, 61] | 82% [73, 90] | 0% [0, 0] | 10% [5, 17] |
| state_text | 30% [20, 37] | 24% [16, 35] | 11% [3, 22] | 19% [0, 20] | 38% [27, 60] | 0% [0, 0] | 13% [2, 27] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| blind | 5.31 [4.36, 6.58] | -5.31 [-6.58, -4.36] | 0% [0, 0] | 0% [0, 0] | -0.0 | 100% [100, 100] | 13% [0, 27] | 100% [100, 100] | 0 |
| telemetry | 1.62 [1.02, 2.44] | 0.33 [-0.78, 1.07] | 33% [18, 51] | 2% [0, 7] | 2.351 | 2% [2, 4] | 0% [0, 0] | 7% [0, 14] | 0 |
| video_dense | 2.69 [2.02, 3.53] | -2.24 [-3.20, -1.44] | 9% [0, 20] | 24% [11, 40] | 2.1 | 41% [31, 53] | 9% [0, 22] | 76% [57, 92] | 0 |
| video_sparse | 3.38 [2.56, 4.56] | -3.38 [-4.56, -2.56] | 7% [0, 13] | 51% [38, 67] | 1.646 | 65% [55, 72] | 0% [0, 0] | 79% [68, 89] | 0 |
| video_log | 3.48 [2.95, 4.05] | 2.89 [1.73, 3.86] | 5% [0, 11] | 5% [0, 14] | 1.837 | 2% [1, 3] | 0% [0, 0] | 0% [0, 0] | 0 |
| state_text | 4.02 [3.02, 5.31] | -4.02 [-5.31, -3.02] | 0% [0, 0] | 20% [9, 36] | 1.59 | 3% [2, 4] | 4% [0, 13] | 0% [0, 0] | 0 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| blind | - / 0 / - (n=0) | - / 0 / - (n=0) | 73 / 9 / 15 (n=237) | 7 / 0 / 1 (n=15) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| telemetry | 56 / 76 / 65 (n=321) | 77 / 13 / 23 (n=217) | 86 / 15 / 25 (n=207) | 41 / 5 / 9 (n=32) | 68 / 16 / 27 (n=22) | 100 / 5 / 10 (n=3) | - / 0 / - (n=0) | 0 / 0 / - (n=1) | 0 / 0 / - (n=3) |
| video_dense | 27 / 27 / 27 (n=241) | 9 / 1 / 1 (n=97) | 45 / 9 / 16 (n=371) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_sparse | 37 / 13 / 20 (n=87) | 23 / 2 / 4 (n=121) | 40 / 5 / 10 (n=221) | 0 / 0 / - (n=8) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_log | 48 / 74 / 58 (n=367) | 81 / 15 / 26 (n=241) | 90 / 10 / 18 (n=133) | 75 / 9 / 16 (n=32) | 89 / 9 / 16 (n=9) | 100 / 25 / 39 (n=14) | - / 0 / - (n=0) | 0 / 0 / - (n=5) | 100 / 3 / 5 (n=2) |
| state_text | 33 / 18 / 23 (n=127) | 36 / 2 / 3 (n=55) | 36 / 3 / 6 (n=132) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | 0 / 0 / - (n=1) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- blind: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- telemetry: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion 0/0 vs 0/0
- video_dense: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_sparse: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_log: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion 100/1 vs 0/0
- state_text: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| blind | 15 | 0 | - | 0% [0, 0] |
| telemetry | 15 | 9 | 33% [0, 43] | 0% [0, 0] |
| video_dense | 15 | 9 | 56% [0, 100] | 0% [0, 0] |
| video_sparse | 15 | 0 | - | 0% [0, 0] |
| video_log | 15 | 7 | 29% [0, 100] | 0% [0, 0] |
| state_text | 15 | 8 | 12% [0, 50] | 0% [0, 0] |
| oracle | 15 | 1 | 0% [0, 0] | 0% [0, 0] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +36 [+27, +44], p=6e-05 | +11 [+8, +16], p=0.00012 | +49 [+39, +61], p=6e-05 | +25 [+18, +33], p=6e-05 |
| telemetry - video_sparse | +35 [+26, +45], p=0.00012 | +13 [+10, +17], p=6e-05 | +62 [+52, +74], p=6e-05 | +28 [+22, +35], p=0.00085 |
| telemetry - blind | +1 [-6, +7], p=0.89 | +14 [+11, +18], p=6e-05 | +76 [+68, +85], p=0.00065 | +36 [+28, +44], p=6e-05 |
| video_dense - blind | -35 [-46, -23], p=0.00031 | +3 [+1, +4], p=0.00262 | +27 [+18, +35], p=0.00089 | +11 [+2, +19], p=0.0256 |
| video_sparse - blind | -35 [-45, -24], p=0.00043 | +1 [+0, +2], p=0.0308 | +13 [+8, +18], p=0.00119 | +8 [+2, +15], p=0.132 |
| video_dense - video_sparse | -0 [-11, +11], p=0.978 | +2 [+0, +3], p=0.0833 | +13 [+5, +23], p=0.00827 | +3 [-5, +11], p=0.978 |
| video_log - telemetry | -2 [-8, +4], p=0.887 | -0 [-2, +2], p=0.934 | -2 [-11, +9], p=0.691 | +2 [-2, +7], p=0.0946 |
| video_log - video_dense | +34 [+24, +42], p=0.00012 | +11 [+7, +16], p=6e-05 | +47 [+33, +62], p=6e-05 | +28 [+19, +36], p=0.00012 |
| state_text - telemetry | -34 [-44, -21], p=0.00116 | -13 [-18, -10], p=6e-05 | -58 [-67, -49], p=6e-05 | -6 [-16, +4], p=0.0833 |
| state_text - video_dense | +1 [-13, +18], p=0.679 | -2 [-4, -0], p=0.0382 | -9 [-22, +7], p=0.0993 | +20 [+8, +30], p=0.0413 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
