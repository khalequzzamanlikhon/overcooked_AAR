# Perception probe

1646 items from all 76 episodes. Brackets: 95% CIs, resampling episodes.

## Video vs. the same information as text

| question | chance (uniform / majority) | qwen25vl7b_4bit video | qwen25vl7b_4bit text | qwen25vl7b_bf16 video | qwen25vl7b_bf16 text | qwen3vl8b_bf16 video | qwen3vl8b_bf16 text |
|---|---|---|---|---|---|---|---|
| L0_clock | - / 3% | 100% [100, 100] | - | 100% [100, 100] | - | 100% [100, 100] | - |
| L0_score | - / 15% | 100% [100, 100] | - | 100% [100, 100] | - | 100% [100, 100] | - |
| L1_held | 25% / 25% | 26% [18, 34] | 100% [100, 100] | 24% [16, 31] | 100% [100, 100] | 45% [37, 54] | 100% [100, 100] |
| L1_who_holds | 50% / 50% | 49% [41, 59] | 100% [100, 100] | 50% [42, 58] | 100% [100, 100] | 79% [71, 87] | 100% [100, 100] |
| L1_relpos | 50% / 50% | 100% [100, 100] | 92% [87, 97] | 100% [100, 100] | 97% [94, 99] | 99% [97, 100] | 97% [95, 99] |
| L1_pot_onions | - / 25% | 32% [24, 39] | 89% [83, 94] | 39% [32, 47] | 84% [78, 90] | 27% [20, 34] | 77% [70, 84] |
| L1_pot_state | 33% / 33% | 39% [31, 47] | 72% [65, 79] | 41% [32, 50] | 94% [90, 97] | 50% [41, 59] | 100% [100, 100] |
| L2_detect | 50% / 50% | 51% [41, 60] | 97% [93, 99] | 50% [41, 59] | 97% [93, 99] | 50% [41, 59] | 98% [96, 100] |
| L2_actor | 50% / 50% | 61% [50, 71] | 100% [100, 100] | 56% [46, 66] | 100% [100, 100] | 59% [48, 70] | 100% [100, 100] |
| L3_order | 50% / 50% | 52% [42, 63] | 92% [87, 96] | 55% [45, 65] | 92% [87, 96] | 51% [42, 60] | 96% [91, 99] |
| L3_localize | 39% / 2% | 46% [36, 56], median error 3.5 s | 100% [100, 100], median error 0.1 s | 44% [34, 54], median error 3.7 s | 100% [100, 100], median error 0.1 s | 32% [23, 41], median error 5.7 s | 99% [97, 100], median error 0.0 s |
| L4_count | - / 20% | 32% [23, 42] | 57% [48, 66] | 30% [21, 40] | 50% [41, 59] | 28% [20, 35] | 54% [47, 62] |

## Frames per second (clip questions)

**qwen25vl7b_4bit**

| variant | L0_clock | L0_score | L1_held | L1_who_holds | L1_relpos | L1_pot_onions | L1_pot_state | L2_detect | L2_actor | L3_order | L3_localize | L4_count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video_fps0.33 | - | - | - | - | - | - | - | 50% [41, 59] | 52% [41, 62] | 52% [42, 62] | 30% [22, 38], median error 4.7 s | 28% [19, 38] |
| video_fps1 | - | - | - | - | - | - | - | 50% [41, 59] | 52% [41, 62] | 52% [43, 62] | 39% [30, 50], median error 3.8 s | 32% [23, 42] |
| video_main | 100% [100, 100] | 100% [100, 100] | 26% [18, 34] | 49% [41, 59] | 100% [100, 100] | 32% [24, 39] | 39% [31, 47] | 51% [41, 60] | 61% [50, 71] | 52% [42, 63] | 46% [36, 56], median error 3.5 s | 32% [23, 42] |
| video_fps4 | - | - | - | - | - | - | - | 57% [48, 67] | 53% [42, 64] | 53% [43, 63] | 62% [53, 71], median error 2.1 s | 28% [20, 36] |

**qwen25vl7b_bf16**

| variant | L0_clock | L0_score | L1_held | L1_who_holds | L1_relpos | L1_pot_onions | L1_pot_state | L2_detect | L2_actor | L3_order | L3_localize | L4_count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video_fps0.33 | - | - | - | - | - | - | - | 50% [41, 59] | 53% [43, 64] | 56% [46, 65] | 26% [17, 35], median error 5.4 s | 29% [20, 39] |
| video_fps1 | - | - | - | - | - | - | - | 50% [41, 59] | 53% [43, 64] | 57% [48, 67] | 36% [26, 46], median error 3.9 s | 32% [23, 42] |
| video_main | 100% [100, 100] | 100% [100, 100] | 24% [16, 31] | 50% [42, 58] | 100% [100, 100] | 39% [32, 47] | 41% [32, 50] | 50% [41, 59] | 56% [46, 66] | 55% [45, 65] | 44% [34, 54], median error 3.7 s | 30% [21, 40] |
| video_fps4 | - | - | - | - | - | - | - | 54% [45, 63] | 52% [40, 63] | 54% [44, 64] | 56% [46, 65], median error 2.7 s | 24% [16, 32] |

**qwen3vl8b_bf16**

| variant | L0_clock | L0_score | L1_held | L1_who_holds | L1_relpos | L1_pot_onions | L1_pot_state | L2_detect | L2_actor | L3_order | L3_localize | L4_count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video_fps0.33 | - | - | - | - | - | - | - | 50% [41, 59] | 51% [39, 63] | 48% [39, 58] | 22% [14, 30], median error 5.8 s | 22% [14, 30] |
| video_fps1 | - | - | - | - | - | - | - | 50% [41, 59] | 51% [39, 63] | 52% [42, 62] | 27% [19, 35], median error 5.3 s | 29% [21, 37] |
| video_main | 100% [100, 100] | 100% [100, 100] | 45% [37, 54] | 79% [71, 87] | 99% [97, 100] | 27% [20, 34] | 50% [41, 59] | 50% [41, 59] | 59% [48, 70] | 51% [42, 60] | 32% [23, 41], median error 5.7 s | 28% [20, 35] |
| video_fps4 | - | - | - | - | - | - | - | 50% [41, 59] | 62% [52, 72] | 52% [42, 62] | 37% [27, 47], median error 5.4 s | 26% [19, 33] |


## What is on screen above the grid

**qwen25vl7b_4bit**

| variant | L0_clock | L0_score | L1_held | L1_who_holds | L1_relpos | L1_pot_onions | L1_pot_state | L2_detect | L2_actor | L3_order | L3_localize | L4_count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video_main | 100% [100, 100] | 100% [100, 100] | 26% [18, 34] | 49% [41, 59] | 100% [100, 100] | 32% [24, 39] | 39% [31, 47] | 51% [41, 60] | 61% [50, 71] | 52% [42, 63] | 46% [36, 56], median error 3.5 s | 32% [23, 42] |
| video_hud_clock | - | - | - | - | - | - | - | 50% [41, 59] | - | - | 42% [33, 51], median error 4.0 s | 32% [23, 42] |
| video_hud_none | - | - | - | - | - | - | - | 50% [41, 59] | - | - | 36% [27, 44], median error 3.9 s | 24% [15, 33] |

**qwen25vl7b_bf16**

| variant | L0_clock | L0_score | L1_held | L1_who_holds | L1_relpos | L1_pot_onions | L1_pot_state | L2_detect | L2_actor | L3_order | L3_localize | L4_count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video_main | 100% [100, 100] | 100% [100, 100] | 24% [16, 31] | 50% [42, 58] | 100% [100, 100] | 39% [32, 47] | 41% [32, 50] | 50% [41, 59] | 56% [46, 66] | 55% [45, 65] | 44% [34, 54], median error 3.7 s | 30% [21, 40] |
| video_hud_clock | - | - | - | - | - | - | - | 50% [41, 59] | - | - | 35% [26, 44], median error 4.7 s | 29% [20, 39] |
| video_hud_none | - | - | - | - | - | - | - | 50% [41, 59] | - | - | 32% [23, 41], median error 4.8 s | 25% [16, 34] |

**qwen3vl8b_bf16**

| variant | L0_clock | L0_score | L1_held | L1_who_holds | L1_relpos | L1_pot_onions | L1_pot_state | L2_detect | L2_actor | L3_order | L3_localize | L4_count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video_main | 100% [100, 100] | 100% [100, 100] | 45% [37, 54] | 79% [71, 87] | 99% [97, 100] | 27% [20, 34] | 50% [41, 59] | 50% [41, 59] | 59% [48, 70] | 51% [42, 60] | 32% [23, 41], median error 5.7 s | 28% [20, 35] |
| video_hud_clock | - | - | - | - | - | - | - | 50% [41, 59] | - | - | 15% [8, 23], median error 6.7 s | 18% [12, 25] |
| video_hud_none | - | - | - | - | - | - | - | 50% [41, 59] | - | - | 17% [10, 24], median error 6.6 s | 20% [14, 27] |

`video_main` is 2 fps with the clock and score strip; `video_hud_clock` drops the score, `video_hud_none` drops the strip. For L3_localize, *accuracy* is within 3 s.
