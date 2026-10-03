Episodes: 15

| condition | claims | supported | supported, naming a player | contradicted | wrong time | names a player | timestamp on a 5 s grid | delivery count error |
|---|---|---|---|---|---|---|---|---|
| blind | 60 | 47% | 47% | 20% | 33% | 100% | 20% | 5.31 |
| telemetry | 898 | 95% | 98% | 1% | 4% | 88% | 2% | 0.91 |
| video_dense | 535 | 69% | 70% | 9% | 21% | 88% | 26% | 3.28 |
| video_sparse | 680 | 58% | 61% | 14% | 28% | 85% | 64% | 4.36 |
| video_log | 615 | 97% | 98% | 0% | 3% | 90% | 2% | 0.78 |
| state_text | 897 | 68% | 68% | 18% | 14% | 93% | 3% | 3.2 |
| oracle | 0 | - | - | - | - | - | - | - |

A whole-second timestamp lands on a 5 s grid 20% of the time by chance.

Chance baselines: the same claims with the time moved to a random moment in
the minute, and with P1 and P2 swapped.

| condition | supported | supported at a random time | not contradicted (named player) | not contradicted, P1/P2 swapped |
|---|---|---|---|---|
| blind | 47% | 52% | 80% | 76% |
| telemetry | 95% | 59% | 99% | 74% |
| video_dense | 69% | 64% | 91% | 75% |
| video_sparse | 58% | 58% | 86% | 85% |
| video_log | 97% | 62% | 100% | 76% |
| state_text | 68% | 51% | 81% | 67% |
| oracle | - | - | - | - |