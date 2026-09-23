Episodes: 15

| condition | claims | supported | supported, naming a player | contradicted | wrong time | names a player | timestamp on a 5 s grid | delivery count error |
|---|---|---|---|---|---|---|---|---|
| telemetry | 320 | 77% | 77% | 3% | 20% | 97% | 2% | 2.4 |
| video_dense | 395 | 48% | 44% | 14% | 38% | 89% | 63% | 3.19 |
| video_sparse | 322 | 51% | 50% | 8% | 41% | 92% | 42% | 4.2 |

A whole-second timestamp lands on a 5 s grid 20% of the time by chance.

Chance baselines: the same claims with the time moved to a random moment in
the minute, and with P1 and P2 swapped.

| condition | supported | supported at a random time | not contradicted (named player) | not contradicted, P1/P2 swapped |
|---|---|---|---|---|
| telemetry | 77% | 45% | 97% | 62% |
| video_dense | 48% | 48% | 84% | 80% |
| video_sparse | 51% | 51% | 92% | 82% |