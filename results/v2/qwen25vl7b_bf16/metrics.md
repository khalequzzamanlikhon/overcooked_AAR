Episodes: 15

| condition | claims | supported | supported, naming a player | contradicted | wrong time | names a player | timestamp on a 5 s grid | delivery count error |
|---|---|---|---|---|---|---|---|---|
| blind | 252 | 69% | 79% | 6% | 25% | 82% | 100% | 5.31 |
| telemetry | 809 | 81% | 82% | 6% | 13% | 97% | 2% | 1.62 |
| video_dense | 709 | 60% | 60% | 11% | 29% | 97% | 41% | 2.69 |
| video_sparse | 437 | 50% | 49% | 11% | 38% | 98% | 64% | 3.38 |
| video_log | 804 | 78% | 79% | 6% | 16% | 96% | 2% | 3.48 |
| state_text | 332 | 66% | 67% | 9% | 25% | 94% | 3% | 4.02 |
| oracle | 0 | - | - | - | - | - | - | - |

A whole-second timestamp lands on a 5 s grid 20% of the time by chance.

Chance baselines: the same claims with the time moved to a random moment in
the minute, and with P1 and P2 swapped.

| condition | supported | supported at a random time | not contradicted (named player) | not contradicted, P1/P2 swapped |
|---|---|---|---|---|
| blind | 69% | 77% | 100% | 100% |
| telemetry | 81% | 56% | 94% | 73% |
| video_dense | 60% | 57% | 88% | 85% |
| video_sparse | 50% | 59% | 88% | 86% |
| video_log | 78% | 51% | 94% | 73% |
| state_text | 66% | 54% | 91% | 67% |
| oracle | - | - | - | - |