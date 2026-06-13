# Anti-leak guard for benchmark runs. Preferred layout: dataset/data (train input) and dataset/truth (evaluation only).
from __future__ import annotations

import inspect
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


_PHASE = "training"
_TRUTH_DIRS = set()
_TRUTH_NAME_PATTERNS = ("a_true", "w_true", "topo_true")


def configure_truth_dirs(*dirs: Optional[str]) -> None:
    _TRUTH_DIRS.clear()
    for d in dirs:
        if not d:
            continue
        try:
            _TRUTH_DIRS.add(str(Path(d).resolve()))
        except Exception:
            _TRUTH_DIRS.add(str(d))


def _path_in_truth(path: str) -> bool:
    try:
        rp = str(Path(path).resolve())
    except Exception:
        rp = str(path)
    rp_low = rp.lower()
    if "/truth/" in rp_low or "\\truth\\" in rp_low:
        return True
    return any(rp.startswith(td) for td in _TRUTH_DIRS)


def _assert_path_allowed(path: str, stage: str = "training") -> None:
    if _PHASE == "training" and _path_in_truth(path):
        raise RuntimeError(
            f"[ANTI-LEAK] Truth path accessed during training ({stage}): {path}"
        )


def guarded_read_csv(path, *args, **kwargs):
    _assert_path_allowed(str(path), stage="read_csv")
    return pd.read_csv(path, *args, **kwargs)


def guarded_open(path, *args, **kwargs):
    _assert_path_allowed(str(path), stage="open")
    return open(path, *args, **kwargs)


def assert_no_truth_loaded(stage: str) -> None:
    if _PHASE != "training":
        return
    for frame_info in inspect.stack():
        loc = frame_info.frame.f_locals
        for k, v in loc.items():
            kl = str(k).lower()
            if any(p in kl for p in _TRUTH_NAME_PATTERNS) and v is not None:
                raise RuntimeError(
                    f"[ANTI-LEAK] Truth-like variable '{k}' observed during training "
                    f"(stage={stage}, function={frame_info.function})"
                )


@contextmanager
def training_phase():
    global _PHASE
    prev = _PHASE
    _PHASE = "training"
    try:
        yield
    finally:
        _PHASE = prev


@contextmanager
def evaluation_phase():
    global _PHASE
    prev = _PHASE
    _PHASE = "evaluation"
    try:
        yield
    finally:
        _PHASE = prev


