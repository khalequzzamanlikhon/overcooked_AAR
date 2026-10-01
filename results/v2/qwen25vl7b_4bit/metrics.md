Episodes: 15

| condition | claims | supported | supported, naming a player | contradicted | wrong time | names a player | timestamp on a 5 s grid | delivery count error |
|---|---|---|---|---|---|---|---|---|
| blind | 222 | 72% | 75% | 0% | 28% | 78% | 100% | 5.24 |
| telemetry | 779 | 81% | 80% | 6% | 14% | 100% | 2% | 2.18 |
| video_dense | 783 | 51% | 49% | 13% | 37% | 95% | 27% | 2.8 |
| video_sparse | 362 | 36% | 36% | 18% | 46% | 98% | 54% | 3.69 |
| video_log | 769 | 84% | 83% | 3% | 13% | 100% | 3% | 4.46 |
| state_text | 576 | 62% | 62% | 11% | 27% | 100% | 2% | 4.18 |
| oracle | 0 | - | - | - | - | - | - | - |

A whole-second timestamp lands on a 5 s grid 20% of the time by chance.

Chance baselines: the same claims with the time moved to a random moment in
the minute, and with P1 and P2 swapped.

| condition | supported | supported at a random time | not contradicted (named player) | not contradicted, P1/P2 swapped |
|---|---|---|---|---|
| blind | 72% | 85% | 100% | 98% |
| telemetry | 81% | 54% | 94% | 73% |
| video_dense | 51% | 51% | 87% | 80% |
| video_sparse | 36% | 42% | 83% | 79% |
| video_log | 84% | 56% | 97% | 70% |
| state_text | 62% | 48% | 89% | 74% |
| oracle | - | - | - | - |