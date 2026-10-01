# Study v2 metrics: qwen25vl7b_bf16_seed3 (Qwen2.5-VL-7B-Instruct)

Episodes: 15. Claim cap per minute: 20. Brackets are 95% CIs from resampling episodes (10,000 draws).

## Claims

| condition | claims | precision | precision, named player | recall | recall / ceiling | delivery recall | actor accuracy (chance) | median time error, s |
|---|---|---|---|---|---|---|---|---|
| telemetry | 818 | 69% [65, 74] | 69% [65, 74] | 16% [13, 20] | 58% [52, 64] | 77% [70, 86] | 85% [80, 90] (52%) | 0.0 [0.0, 0.3] |
| video_dense | 388 | 59% [50, 69] | 59% [50, 69] | 5% [3, 7] | 17% [11, 23] | 11% [5, 19] | 55% [47, 63] (52%) | 1.4 [1.1, 1.8] |

*precision*: claims matched one-to-one to a real event (right type, player, within 3 s) / checkable claims. *recall*: real events some claim was matched to. The ceiling is what recall could reach with the claim cap.

## Against chance

| condition | supported at 3 s | at a random time | above-chance area | not contradicted | P1/P2 swapped |
|---|---|---|---|---|---|
| telemetry | 69% [65, 74] | 46% [40, 51] | 0.175 | 95% [92, 97] | 71% [60, 82] |
| video_dense | 59% [50, 69] | 57% [50, 65] | -0.008 | 88% [80, 95] | 82% [74, 91] |

*above-chance area*: mean gap between the supported rate and its random-time baseline over tolerances 0.5-10 s. Zero means the timestamps carry no information.

## Where claims go wrong

| condition | duplicate | wrong time | contradicted | both/unclear precision | pickup incl. fill_dish | before the window | rescued by +start |
|---|---|---|---|---|---|---|---|
| telemetry | 10% [7, 13] | 16% [12, 20] | 5% [3, 8] | 60% [40, 100] | 84% [78, 92] | 0% [0, 0] | 6% [4, 9] |
| video_dense | 2% [1, 3] | 27% [19, 35] | 12% [5, 20] | - | 46% [30, 64] | 0% [0, 0] | 1% [0, 3] |

*rescued by +start*: unsupported claims that would be supported if their time were read as seconds since the clip started.

## Counting and output collapse

| condition | delivery MAE | signed error | exact | says 1 | answer entropy, bits | 5 s grid | repeated minutes | strict P1/P2 alternation | parse failures |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 3.16 [2.31, 3.91] | 1.82 [0.56, 2.87] | 24% [11, 40] | 7% [0, 13] | 2.16 | 2% [1, 3] | 0% [0, 0] | 0% [0, 0] | 0 |
| video_dense | 3.63 [2.94, 4.35] | -3.63 [-4.35, -2.94] | 3% [0, 9] | 97% [90, 100] | 0.187 | 23% [21, 25] | 0% [0, 0] | 11% [0, 23] | 9 |

## By claim type (precision / recall / F1)

| condition | delivery | pickup | pot | counter | blocked | idle | waiting | handoff | congestion |
|---|---|---|---|---|---|---|---|---|---|
| telemetry | 55 / 77 / 65 (n=334) | 82 / 15 / 25 (n=227) | 90 / 12 / 22 (n=175) | 48 / 7 / 13 (n=40) | 50 / 9 / 15 (n=16) | 83 / 9 / 16 (n=6) | 0 / 0 / - (n=7) | 0 / 0 / - (n=5) | 0 / 0 / - (n=2) |
| video_dense | 31 / 11 / 17 (n=87) | 38 / 2 / 4 (n=68) | 76 / 10 / 18 (n=232) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | - / 0 / - (n=0) | 0 / 0 / - (n=1) | - / 0 / - (n=0) |

Behaviour thresholds at 0.5x / 1.5x (precision / recall):

- telemetry: waiting 14/1 vs 0/-; handoff 0/0 vs 0/0; congestion 50/0 vs 0/0
- video_dense: waiting -/0 vs -/-; handoff 0/0 vs 0/0; congestion -/0 vs -/0

## The written reviews

| condition | reviews | timed statements checked | timed statements wrong | reviews with a wrong count |
|---|---|---|---|---|
| telemetry | 15 | 5 | 20% [0, 33] | 0% [0, 0] |
| video_dense | 15 | 10 | 20% [20, 20] | 0% [0, 0] |

## Paired differences (A - B, same episodes)

| A - B | precision | recall | delivery recall | actor accuracy |
|---|---|---|---|---|
| telemetry - video_dense | +10 [-0, +20], p=0.064 | +12 [+8, +16], p=6e-05 | +66 [+58, +74], p=6e-05 | +30 [+21, +40], p=0.00049 |

Differences in percentage points; p from a Wilcoxon signed-rank test on per-episode rates.
