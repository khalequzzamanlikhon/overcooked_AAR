"""Load the bundled 2019 human-human Overcooked trials.

Two breakages you will hit and this module works around:

1. The pickles were written under pandas 1.x and reference
   `pandas.core.indexes.numeric`, which pandas 2.x removed. Unpickling dies
   with ModuleNotFoundError. Installing pandas<2.0 is not a fix on Python
   3.12 (it won't build), so `_install_pandas_shim()` registers a stub
   module instead. Call it before any pickle load.

2. There is no explicit trial ID column. A trial is the combination of
   (workerid_num, round_num, layout_name).
"""
from __future__ import annotations

import ast
import logging
import pickle
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_SHIM_INSTALLED = False


def _install_pandas_shim() -> None:
    """Register a stub for the pandas 1.x module path these pickles reference."""
    global _SHIM_INSTALLED
    if _SHIM_INSTALLED or "pandas.core.indexes.numeric" in sys.modules:
        return
    mod = types.ModuleType("pandas.core.indexes.numeric")

    class _LegacyIndex(pd.Index):
        def __new__(cls, *args, **kwargs):
            return pd.Index(*args, **kwargs)

    mod.Int64Index = _LegacyIndex
    mod.Float64Index = _LegacyIndex
    mod.NumericIndex = _LegacyIndex
    sys.modules["pandas.core.indexes.numeric"] = mod
    _SHIM_INSTALLED = True


def human_data_dir() -> Path:
    import overcooked_ai_py

    return Path(overcooked_ai_py.__file__).parent / "data" / "human_data"


@dataclass
class Trial:
    """One human-human episode."""

    trial_id: str
    layout_name: str
    final_score: float
    states: list[dict]  # parsed old-format state dicts, one per timestep
    joint_actions: list[list]
    scores: list[float]
    time_elapsed: list[float]

    def __len__(self) -> int:
        return len(self.states)


def load_trials(pickle_name: str, layout: str | None = None) -> list[Trial]:
    """Load trials from a bundled pickle, optionally filtered to one layout."""
    _install_pandas_shim()
    path = human_data_dir() / pickle_name
    with path.open("rb") as f:
        df: pd.DataFrame = pickle.load(f)

    if layout is not None:
        df = df[df["layout_name"] == layout]

    df = df.copy()
    df["trial_id"] = (
        df["workerid_num"].astype(str)
        + "_r"
        + df["round_num"].astype(int).astype(str)
        + "_"
        + df["layout_name"]
    )

    trials: list[Trial] = []
    for trial_id, group in df.groupby("trial_id", sort=True):
        group = group.sort_values("cur_gameloop")
        trials.append(
            Trial(
                trial_id=str(trial_id),
                layout_name=str(group["layout_name"].iloc[0]),
                final_score=float(group["score"].max()),
                states=[ast.literal_eval(s) for s in group["state"]],
                joint_actions=[ast.literal_eval(a) if isinstance(a, str) else a for a in group["joint_action"]],
                scores=[float(s) for s in group["score"]],
                time_elapsed=[float(t) for t in group["time_elapsed"]],
            )
        )
    logger.info("loaded %d trials from %s", len(trials), pickle_name)
    return trials
