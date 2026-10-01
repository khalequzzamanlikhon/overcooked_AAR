# Study v2 metrics: qwen3vl8b_bf16_seed3 (Qwen3-VL-8B-Instruct)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 899 | 95% [93, 97] | 96% [94, 98] | 26% [20, 33] | 91% [89, 94] | 94% [89, 99] | 99% [98, 100] (50%) | 0.0 [0.0, 0.0] |
| video_dense | 721 | 41% [34, 48] | 42% [33, 51] | 6% [5, 8] | 23% [20, 27] | 20% [9, 33] | 59% [52, 65] (50%) | 1.1 [0.9, 1.4] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 95% [93, 97] | 54% [49, 60] | 0.331 | 98% [97, 100] | 74% [64, 83] |
| video_dense | 41% [34, 48] | 46% [38, 54] | -0.055 | 77% [67, 87] | 69% [58, 80] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 1% [0, 2] | 2% [1, 4] | 1% [0, 3] | 88% [80, 94] | 100% [98, 100] | 0% [0, 0] | 4% [0, 12] |
| video_dense | 13% [7, 18] | 20% [14, 26] | 27% [18, 34] | 37% [22, 53] | 53% [43, 64] | 0% [0, 0] | 8% [4, 12] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 1.00 [0.71, 1.29] | 0.73 [0.22, 1.13] | 29% [16, 44] | 2% [0, 7] | 2.884 | 2% [1, 2] | 0% [0, 0] | 2% [0, 7] | 0 |
| video_dense | 3.88 [2.77, 5.27] | -3.79 [-5.21, -2.61] | 5% [0, 12] | 0% [0, 0] | 1.705 | 35% [28, 43] | 0% [0, 0] | 20% [8, 34] | 3 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 91 / 94 / 92 (n=246) | 100 / 16 / 27 (n=199) | 96 / 30 / 46 (n=343) | 77 / 13 / 22 (n=43) | 100 / 44 / 61 (n=40) | 100 / 49 / 66 (n=28) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) |
| video_dense | 45 / 20 / 28 (n=107) | 31 / 3 / 6 (n=127) | 58 / 11 / 18 (n=328) | 7 / 2 / 3 (n=83) | 0 / 0 / - (n=6) | 11 / 11 / 11 (n=56) | 0 / 0 / - (n=5) | 0 / 0 / - (n=3) | 100 / 3 / 5 (n=2) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting -/0 vs -/-; handoff -/0 vs -/0; congestion -/0 vs -/0
- video_dense: waiting 20/1 vs 0/-; handoff 0/0 vs 0/0; congestion 100/1 vs 50/3

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 79 | 30% [16, 47] | 40% [13, 67] |
| video_dense | 15 | 86 | 58% [40, 76] | 13% [0, 33] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +54 [+48, +60], p=6e-05 | +19 [+15, +25], p=6e-05 | +74 [+60, +85], p=0.00064 | +41 [+34, +47], p=0.00073 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
