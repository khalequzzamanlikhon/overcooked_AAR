Episodes: 15

| condition | claims | supported | supported, naming a player | contradicted | wrong time | names a player | timestamp on a 5 s grid | delivery count error |
|---|---|---|---|---|---|---|---|---|
| telemetry | 351 | 81% | 81% | 2% | 17% | 97% | 1% | 2.13 |
| video_dense | 411 | 53% | 52% | 9% | 38% | 96% | 98% | 3.96 |
| video_sparse | 378 | 59% | 54% | 8% | 32% | 78% | 79% | 4.56 |

A whole-second timestamp lands on a 5 s grid 20% of the time by chance.

Chance baselines: the same claims with the time moved to a random moment in
the minute, and with P1 and P2 swapped.

| condition | supported | supported at a random time | not contradicted (named player) | not contradicted, P1/P2 swapped |
|---|---|---|---|---|
| telemetry | 81% | 46% | 98% | 59% |
| video_dense | 53% | 52% | 91% | 85% |
| video_sparse | 59% | 63% | 89% | 86% |