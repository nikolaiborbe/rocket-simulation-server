"""Store and retrieve trajectory data as compressed .npz files."""

import numpy as np
from pathlib import Path
from config import STORAGE_DIR


def save_trajectories(run_id: str, trajectories: list[list[list[float]]]) -> str:
    """Save trajectory data as compressed .npz file. Returns file path."""
    path = STORAGE_DIR / f"{run_id}_trajectories.npz"
    arrays = {f"traj_{i}": np.array(t, dtype=np.float32) for i, t in enumerate(trajectories)}
    np.savez_compressed(str(path), **arrays)
    return str(path)


def load_trajectories(run_id: str) -> list[list[list[float]]]:
    """Load trajectory data from .npz file."""
    path = STORAGE_DIR / f"{run_id}_trajectories.npz"
    if not path.exists():
        return []
    data = np.load(str(path))
    return [data[key].tolist() for key in sorted(data.files)]
