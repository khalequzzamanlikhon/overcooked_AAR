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

<p align="center">
  <img src="docs/demo/cramped_room.gif" width="32%" alt="cramped_room episode">
  <img src="docs/demo/coordination_ring.gif" width="32%" alt="coordination_ring episode">
  <img src="docs/demo/random0.gif" width="32%" alt="random0 (forced_coordination) episode">
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
version had three bugs, which I found by checking the events against the raw data:

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
per condition, 239 real deliveries and 1,140 claims in total. The full run is in
[`results/pilot_2026-09/`](results/pilot_2026-09/).

| condition | claims | supported | supported, naming a player | contradicted | wrong time | names a player | timestamp on a 5 s grid | delivery count error |
|---|---|---|---|---|---|---|---|---|
| log (`telemetry`) | 351 | **81%** | 81% | 2% | 17% | 97% | 1% | 2.13 |
| video, 2 fps (`video_dense`) | 411 | **53%** | 52% | 9% | 38% | 96% | 98% | 3.96 |
| video, 1 frame / 3 s (`video_sparse`) | 378 | **59%** | 54% | 8% | 32% | 78% | 79% | 4.56 |

*supported*: an event of that kind, by that player, within 3 s of the claimed time.
*wrong time*: that player did it in that minute, but more than 3 s away.
*contradicted*: that player did no such thing in that minute.

What I found:

- **The log beats the video, 81% to 53%.** That alone isn't surprising. The
  interesting part is *how* the video model goes wrong: it rarely invents events (9%
  contradicted); mostly it puts real events at the wrong moment (38%).
- **The video model doesn't read the clock.** 98% of its timestamps land on a 5-second
  grid, against 1% for the log. It spaces its claims evenly through the minute (15 s,
  20 s, 25 s…) instead of reading the time, even though the clock is on screen in
  every frame.
- **Neither counts well, and video is worse.** With video at 2 fps the model
  under-counted deliveries in 41 of 45 minutes, and in all 45 at 1 frame per 3 s,
  often saying one delivery when there were four to seven. From the log it was exact
  in 13 of 45.
- **Fewer frames only looked better.** At 1 frame per 3 s the supported rate goes up
  to 59%, but only 78% of those claims name a player (96% at 2 fps). Counting only
  claims that name P1 or P2, the two video settings are the same: 54% vs. 52%. The
  model got "more accurate" by being vaguer.
- **What the model claims follows the source.** From the log it mostly claims
  deliveries (243 of 351). From sparse video it mostly claims pickups (248 of 378),
  the most visible action, and far fewer deliveries.

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

| Path | What it is |
|---|---|
| `aar/data_loader.py` | loads the 2019 human trials (with a fix for old pandas pickles) |
| `aar/telemetry_to_text.py` | raw state → events → the text the log condition reads |
| `aar/render_video.py` | trials → real-time mp4s with labels, split by minute |
| `aar/generate_aar.py` | the prompts: claims first, then the review |
| `aar/vlm_local.py` | loads Qwen2.5-VL and runs it on text or video |
| `aar/verify.py` | checks one claim against the log: supported, wrong time, contradicted, unchecked |
| `run_pipeline.py` | runs everything, one episode at a time |
| `analyze.py` | the results table |
| `rate_aars.py` | blind pairwise rating, one file per rater |
| `results/pilot_2026-09/` | this run: claims, verdicts, reviews, metrics |

## Data

The data ships with the `overcooked-ai` package: 39 train and 37 test trials of real
human-human play across five layouts, with final scores from 40 to 205. There is
nothing to download.

Carroll, M., Shah, R., Ho, M. K., Griffiths, T. L., Seshia, S. A., Abbeel, P., Dragan, A.
*On the Utility of Learning about Humans for Human-AI Coordination.* NeurIPS 2019.
