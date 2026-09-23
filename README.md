# Telemetry vs. video: comparing automatic after-action reviews

**Status: pilot study, started September 2026.** The automatic claim checks are done.
I plan to add a blind human rating next; the tool for it is built.

After a team plays, an after-action review says what they did well, what cost them
time, and what to change. I wanted to know whether a model writes a better review
from the game's event log or from watching the gameplay video. The log knows exactly
what happened, but video shows things the log never records, like hesitation or a
near-miss.

So I gave the *same* model the *same* episode in two forms, asked it the same
questions, and checked every claim it made against the log.

## Demo

These are real human-human episodes from the 2019 Overcooked study, rendered from the
bundled action logs at the speed they were played, with the clock and player labels
on screen.

**Current render** (used for [`results/pilot_2026-09b/`](results/pilot_2026-09b/)):
large clock strip, white outlined P1/P2 labels.

<p align="center">
  <img src="docs/demo/cramped_room.gif" width="32%" alt="cramped_room episode, current render">
  <img src="docs/demo/coordination_ring.gif" width="32%" alt="coordination_ring episode, current render">
  <img src="docs/demo/random0.gif" width="32%" alt="random0 (forced_coordination) episode, current render">
</p>

**First render** (used for [`results/pilot_2026-09/`](results/pilot_2026-09/)), kept
for comparison: the same episodes, with the clock in ~8 px text at the top left and
the labels drawn in the hat colour on top of the hat. Both were close to unreadable
for the model.

<p align="center">
  <img src="docs/demo/v1/cramped_room.gif" width="32%" alt="cramped_room episode, first render">
  <img src="docs/demo/v1/coordination_ring.gif" width="32%" alt="coordination_ring episode, first render">
  <img src="docs/demo/v1/random0.gif" width="32%" alt="random0 (forced_coordination) episode, first render">
</p>

And this is what the model reads in the log condition for the same episode: events I
extract from about 1,200 timesteps of raw game state
([full file](docs/demo/cramped_room_timeline.txt)):

```text
Layout: cramped_room
Episode length: 181 s. This is seconds 0-60.
Final score for the whole episode: 55

Event log:
  t=   5.4s  P1 picked up an onion.
  t=   5.6s  P1 tried to move into P2 and was blocked for 0.8 s.
  t=   8.1s  P1 put an onion in the pot.
  ...
  t=  14.1s  A pot started cooking (3 onions).
  t=  17.0s  A soup finished cooking.
  t=  18.0s  P1 filled a dish with soup.
  t=  22.2s  P1 delivered a soup.
  ...
```

## How it works

```
human game logs ─┬─ render in real time ─── 60 s clips ──> Video LLM ─┐
                 │                                                    ├─> claims (JSON) ──> review
                 └─ extract events ──────── 60 s windows ─> same model ┘        │
                                                                               ├─> checked against the log
                                                                               └─> blind human rating (planned)
```

The choices the comparison depends on:

| | |
|---|---|
| One model | I used Qwen2.5-VL-7B-Instruct (4-bit, greedy) for every condition, so a difference comes from the input, not the model. |
| One prompt | The wording is the same for both; only the sentence that names the source changes. |
| One minute at a time | Both sources are read in 60 s windows, so both get the same number of chances to make a claim. A 60 s clip at 2 fps also fits in the model's context. |
| Claims first, review second | First the model lists numbered claims (time, player, type, text). Then it writes the review from those claims only. I can check a claim; I can't check a paragraph. |
| Real time, labelled | The video plays at the speed it was played, with the episode clock and P1/P2 drawn on screen, so "P1" means the same player in both conditions. |

## Getting the log right first

The comparison only means something if the log condition is fed the truth. My first
version had three bugs, which I found by checking the events against the raw data
(a fourth, the last minute ending at 180 s, is described under Results):

1. **Action timing.** The action at step `t` moves the player from `t` to `t+1`, not
   from `t-1` to `t`. Matched the wrong way, most real moves looked like failed ones.
2. **Blocked moves.** A move is blocked only when the teammate is standing on the tile
   you tried to enter. I was also counting presses into a counter, which is simply how
   you use a counter, so the log was full of fake "blocked" events.
3. **Dropped deliveries.** When a timeline got long, I kept every Nth event, which
   threw away most deliveries, and deliveries are the score. Now nothing is dropped,
   and `tests/test_events.py` checks that the number of deliveries always matches the
   final score.

## Results

I ran 15 episodes (3 per layout, spread across the score range): 45 one-minute windows
per condition and 239 real deliveries. I ran them twice:

- [`results/pilot_2026-09/`](results/pilot_2026-09/), the first run. In its video the
  P1/P2 labels were drawn in the hat colour on top of the hat, and the clock was
  ~8 px text. Both were close to unreadable, and the last minute stopped at 180 s,
  losing the final 0.6 s of each episode (one delivery in total).
- [`results/pilot_2026-09b/`](results/pilot_2026-09b/), the rerun with white outlined
  labels, a large clock strip and the last minute running to the end. Same episodes,
  model, precision and prompts. The numbers below are from this run.

| condition | claims | supported | supported, naming a player | contradicted | wrong time | names a player | timestamp on a 5 s grid | delivery count error |
|---|---|---|---|---|---|---|---|---|
| log (`telemetry`) | 320 | **77%** | 77% | 3% | 20% | 97% | 2% | 2.40 |
| video, 2 fps (`video_dense`) | 395 | **48%** | 44% | 14% | 38% | 89% | 63% | 3.19 |
| video, 1 frame / 3 s (`video_sparse`) | 322 | **51%** | 50% | 8% | 41% | 92% | 42% | 4.20 |

*supported*: an event of that kind, by that player, within 3 s of the claimed time.
*wrong time*: that player did it in that minute, but more than 3 s away.
*contradicted*: that player did no such thing in that minute.

A supported rate needs a baseline: in a busy minute, a claim like "P1 picked up an
onion" lands within 3 s of some real pickup fairly often by luck alone. So I checked
the same claims again twice: once with each time moved to a random moment in its
minute, and once with P1 and P2 swapped.

| condition | supported | supported at a random time | not contradicted | not contradicted, P1/P2 swapped |
|---|---|---|---|---|
| log | 77% | 45% | 97% | 62% |
| video, 2 fps | 48% | **48%** | 84% | **80%** |
| video, 1 frame / 3 s | 51% | **51%** | 92% | **82%** |

What I found:

- **The log beats the video, 77% to 48%.** And the log's timing is real: it scores
  32 points above its random-time baseline.
- **The video model's timestamps carry no information.** Its claims score exactly
  what they would at a random time in the minute, in both video settings and in both
  runs (53% vs. 52% in the first run). I first read the 38% "wrong time" as "it sees
  the right events and gets the moment wrong". The baseline says otherwise: it knows
  roughly what kinds of things happen in a minute of Overcooked, not when they did.
- **Its player names carry little more.** Swapping P1 and P2 barely changes the
  video claims (84% → 80% not contradicted), while the log's claims fall apart
  (97% → 62%). Both players pick things up all the time, so a low contradicted rate
  doesn't show the model was looking.
- **A readable clock changed the timestamps, not their accuracy.** With the clock too
  small to read, 98% of video timestamps landed on a 5 s grid (15 s, 20 s, 25 s…);
  with a large clock strip, 63%. Whole-second times would land there 20% of the time
  by chance, so the model now uses the clock more, but its times still don't line up
  with events. Unreadable video was part of the problem, not all of it.
- **Neither counts well, and video is worse.** At 2 fps the model under-counted
  deliveries in 37 of 42 minutes it answered, and in all 45 at 1 frame per 3 s,
  often saying one delivery when there were four to seven. From the log it was exact
  in 10 of 45.
- **Fewer frames don't help.** At 1 frame per 3 s the supported rate is 51% against
  48% at 2 fps, and both equal their random-time baselines.
- **What the model claims follows the source.** From the log it mostly claims
  deliveries (233 of 320). From sparse video it mostly claims pickups (200 of 322),
  the most visible action, and far fewer deliveries.
- **The runs are repeatable.** Decoding is greedy, and for the log condition the
  first two minutes of every episode produced identical claims in both runs. Its drop
  from 81% to 77% comes entirely from the last minute, whose input now includes the
  final 0.6 s.

## Limitations

- **Small pilot.** 15 episodes, one model, one prompt, greedy decoding, no repeated runs.
- **Small model.** Qwen2.5-VL-7B in 4-bit is a small, compressed model. A larger Video
  LLM may do better on video; I haven't tested that yet. Because both conditions use
  the same model, the gap is about the input, but the absolute numbers would likely
  change.
- **The check only covers what the log records.** Claims about coordination or
  strategy are left alone; that is what the human rating is for.
- **The written review isn't checked.** Stage 2 can add its own mistakes. In one
  episode, the log-based review said P1 made 24 deliveries when the team made 17.
- **Vague claims are easier to support.** "Both players picked up an onion" matches
  whoever did it, so the table also reports the supported rate for claims that name a
  player.
- **Rendered sprites, no audio.** This is not the same as real video of real people.

## Next: blind human rating (planned)

Each rater watches an episode, reads two reviews of it labelled A and B with the
source hidden, picks which is more accurate and which would help the team more, and
guesses which one came from the video. Ranking two reviews is easier than scoring one,
and the guess shows whether the test was really blind.

```bash
# one file per rater; --pairs limits it to log vs. 2 fps video (15 comparisons, ~1 hour)
python rate_aars.py --run results/pilot_2026-09 --rater r1 --pairs telemetry:video_dense
python analyze.py --run results/pilot_2026-09      # adds the ratings to the results
```

After that, I want to rerun the pipeline with a larger Video LLM to see how much of
the gap is the model and how much is the input.

## Run it

```bash
git clone https://github.com/khalequzzamanlikhon/overcooked_AAR && cd overcooked_AAR
bash run.sh                      # 3 episodes per layout, all three conditions
NO_LLM=1 bash run.sh             # no GPU: render the videos and event logs only
GPU=1 MODEL=Qwen/Qwen2.5-VL-3B-Instruct bash run.sh
python -m pytest tests -q
```

The 7B model in 4-bit needs about 10 GB of free VRAM; pass `--bf16` to
`run_pipeline.py` if you have about 17 GB. A 60 s clip at 2 fps is about 10k visual
tokens, and a whole 180 s episode would be about 30k, which is why I split the video
into minutes. The full pilot took about 2.3 hours on one RTX A5000.

## Data

The data ships with the `overcooked-ai` package: 39 train and 37 test trials of real
human-human play across five layouts, with final scores from 40 to 205. There is
nothing to download.

Carroll, M., Shah, R., Ho, M. K., Griffiths, T. L., Seshia, S. A., Abbeel, P., Dragan, A.
*On the Utility of Learning about Humans for Human-AI Coordination.* NeurIPS 2019.
