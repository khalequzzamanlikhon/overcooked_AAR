# Telemetry vs. video: comparing automatic after-action reviews

**Status: pilot study, started September 2026.** The automatic checks below are done.
The blind human rating is built but not yet run, and is marked as pending throughout.

An after-action review has to say what happened. A game log knows exactly what happened
but not what it looked like. Video shows hesitation, a blocked attempt, a near-miss —
none of which becomes a logged event. So: give the *same* model the *same* episode
through each source, ask it for the same thing, and check every claim it makes against
the log.

## Demo

Real human-human episodes from the 2019 study, rendered straight from the bundled action
logs at the speed they were played, with the episode clock and player labels on screen.

<p align="center">
  <img src="docs/demo/cramped_room.gif" width="32%" alt="cramped_room episode">
  <img src="docs/demo/coordination_ring.gif" width="32%" alt="coordination_ring episode">
  <img src="docs/demo/random0.gif" width="32%" alt="random0 (forced_coordination) episode">
</p>

The same episode as the telemetry condition sees it — an event timeline extracted from
~1,200 timesteps of raw state ([full file](docs/demo/cramped_room_timeline.txt)):

```text
Layout: cramped_room
Episode length: 181 s. This is seconds 0-60.
Final score for the whole episode: 90

Event log:
  t=   2.3s  P2 picked up an onion.
  t=   3.8s  P2 put an onion in the pot.
  t=   7.2s  A pot started cooking (3 onions).
  t=  10.1s  A soup finished cooking.
  t=  11.4s  P2 stood still for 4 s.
  t=  17.1s  P1 filled a dish with soup.
  t=  18.6s  P1 tried to move into P2 and was blocked for 1.2 s.
  t=  21.0s  P1 delivered a soup.
  ...
```

## Design

```
bundled human trials ─┬─ render, real time ─── 60 s clips ──> Video LLM ─┐
                      │                                                  ├─> claims (JSON) ──> AAR
                      └─ event extraction ──── 60 s windows ─> same LLM ─┘        │
                                                                                  ├─> checked against the log
                                                                                  └─> blind pairwise rating (pending)
```

Choices that the comparison depends on:

| | |
|---|---|
| One model | Qwen2.5-VL-7B-Instruct for every condition, 4-bit NF4, greedy. A difference between conditions should come from the input, not from two different models. |
| One prompt | Identical wording; only the sentence naming the source differs. |
| One minute at a time | Both sources are read in 60 s windows, so both get the same number of chances to make a claim, and a 60 s clip at 2 fps fits in context (~10k visual tokens). |
| Claims first, prose second | Stage 1 returns numbered claims (time, player, type, text). Stage 2 writes the review from those claims only. A paragraph cannot be checked; a claim can. |
| Real time, labelled | The video runs at the speed it was played (~6.7 fps, 180 s) with the episode clock and P1/P2 drawn over the chefs, so a claim about P1 in one condition means the same thing in the other. |

## Getting the log right first

The telemetry condition is only meaningful if the log is true. Three things had to be
fixed before any of this meant anything, all verified against the bundled data:

1. **Action alignment.** The action at step `t` produces the move from `t` to `t+1`, not
   from `t-1` to `t`. Matched the other way, most real moves look like failed ones.
2. **Blocked moves.** A blocked move means the teammate is standing on the tile you tried
   to enter. Counting every press that does not move you also counts pressing into a
   counter — which is how you use a counter — and floods the log with false "blocked"
   events. Real ones are rare: a handful per episode.
3. **Nothing is dropped.** The old timeline kept every Nth event when it got long, which
   threw away most deliveries. Deliveries are the score. `tests/test_events.py` checks
   that the number of delivery events equals the final score divided by 5, on every
   episode it is run over.

## Results

15 episodes (3 per layout, spread across the score range), 45 one-minute windows per
condition, 239 real deliveries, 1,140 claims. Full run in
[`results/pilot_2026-09/`](results/pilot_2026-09/).

| condition | claims | supported | supported, naming a player | contradicted | wrong time | names a player | timestamp on a 5 s grid | delivery count error |
|---|---|---|---|---|---|---|---|---|
| telemetry | 351 | **81%** | 81% | 2% | 17% | 97% | 1% | 2.13 |
| video, 2 fps | 411 | **53%** | 52% | 9% | 38% | 96% | 98% | 3.96 |
| video, 1 frame / 3 s | 378 | **59%** | 54% | 8% | 32% | 78% | 79% | 4.56 |

*supported* = an event of that kind, by that player, within 3 s of the claimed time.
*wrong time* = that player did do it in that minute, but more than 3 s away.
*contradicted* = no such event by that player in that minute at all.

What the run says:

- **Reading the log beats watching, 81% against 53%.** Not a surprise on its own. What the
  breakdown shows is *how* the video model is wrong: it is not inventing events (only 9%
  are contradicted outright) — it is putting real events at the wrong moment (38%).
- **The video model is not reading the clock.** 98% of its timestamps land on a 5-second
  grid, against 1% for the log condition. It is spacing claims evenly through the minute
  and labelling them, which is exactly what produces "wrong time" rather than "contradicted".
  The episode clock is on screen in every frame.
- **Neither can count repetitions, video least of all.** The video condition under-counted
  deliveries in 41 of 45 minutes at 2 fps and in **45 of 45** at 1 frame per 3 s, usually
  reporting one delivery in a minute where four to seven happened. Reading the log it was
  exact in 13 of 45.
- **A lower frame rate looks better until you control for vagueness.** At 1 frame per 3 s the
  supported rate rises to 59%, but only 78% of those claims name a player, against 96% at
  2 fps. Count only the claims that name P1 or P2 and the two rates are the same (54% vs
  52%). The sparse model buys accuracy with "both players", not with better seeing.
- **Type of claim follows the source.** The log condition mostly claims deliveries
  (243 of 351); the sparse video condition mostly claims pickups (248 of 378) — the visible
  action — and almost half as many deliveries.

## Limitations

- **15 episodes, one model, one prompt, greedy decoding, 4-bit weights.** No other models,
  no prompt variants, no repeated runs.
- **The automatic check only judges what the log records.** Claims about coordination or
  strategy are left alone; they are what the human rating is for.
- **Vague claims are easier to support.** "Both players picked up an onion" matches
  whoever did it, so the table reports supported-rate again over only the claims that name
  a specific player.
- **Rendered sprites, not real video, and no audio.** Whatever a Video LLM does here, it
  is not the same problem as reading a real recording of real people.
- **The human rating is not done**, so nothing here says which review is more *useful* to
  a player — only which claims are true.

## Pending

Blind pairwise rating: each rater watches the episode, sees two reviews of it as A and B
with the source hidden, picks which is more accurate and which is more useful, and guesses
which came from the video. Ranking is easier than rating, and the guess is there to show
whether the comparison is really blind.

```bash
python rate_aars.py --run results/pilot_2026-09 --rater <name>   # one file per rater
python analyze.py --run results/pilot_2026-09                    # adds the ratings to the table
```

## Run it

```bash
git clone https://github.com/khalequzzamanlikhon/overcooked_AAR && cd overcooked_AAR
bash run.sh                      # 3 episodes per layout, all three conditions
NO_LLM=1 bash run.sh             # no GPU: render the videos and event logs only
GPU=1 MODEL=Qwen/Qwen2.5-VL-3B-Instruct bash run.sh
python -m pytest tests -q
```

Needs ~10 GB of free VRAM for the 7B in 4-bit; pass `--bf16` to `run_pipeline.py` if you
have ~17 GB. A 60 s clip at 2 fps is about 10k visual tokens, a whole 180 s episode about
30k, which is why the clips are split.

| Path | What it is |
|---|---|
| `aar/telemetry_to_text.py` | raw state -> events -> the text the telemetry condition reads |
| `aar/render_video.py` | trials -> real-time mp4s, labelled, split by minute |
| `aar/generate_aar.py` | the two prompts, identical except for the source line |
| `aar/verify.py` | one claim vs the log: supported, wrong time, contradicted, unchecked |
| `analyze.py` | the results table |
| `rate_aars.py` | blind pairwise rating, one file per rater |
| `results/pilot_2026-09/` | this run: claims, verdicts, reviews, metrics |

## Data

Ships with the `overcooked-ai` package: 39 train and 37 test trials of real human-human
play across five layouts, final scores 40-205. Nothing to download.

Carroll, M., Shah, R., Ho, M. K., Griffiths, T. L., Seshia, S. A., Abbeel, P., Dragan, A.
*On the Utility of Learning about Humans for Human-AI Coordination.* NeurIPS 2019.
