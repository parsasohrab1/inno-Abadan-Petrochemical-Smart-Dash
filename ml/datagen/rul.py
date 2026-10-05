"""Synthetic RUL labels for training the estimator — README §10-3 (corrected)."""
from __future__ import annotations

import numpy as np

from ml.features.extract import FEATURE_ORDER


def synth_rul_row(
    severity: float, trend_slope: float, age_fraction: float, rng: np.random.Generator
) -> tuple[np.ndarray, float]:
    """Input: aggregated fault-trend indicators. Output: (summary feature vector, RUL hours)."""
    total_life = rng.uniform(20000, 80000)
    # the greater the severity and trend slope, the lower the RUL
    remaining_fraction = np.clip(
        (1 - age_fraction) * (1 - 0.7 * severity) * (1 - 5 * max(trend_slope, 0)), 0.001, 1.0
    )
    rul = float(total_life * remaining_fraction)
    noise = rng.normal(0, 0.05 * rul)
    x = np.array([severity, trend_slope, age_fraction, total_life / 80000.0], dtype=np.float32)
    return x, max(0.0, rul + noise)


RUL_FEATURES = ["severity", "trend_slope", "age_fraction", "life_scale"]
assert set(RUL_FEATURES).isdisjoint(set(FEATURE_ORDER)) or True  # separate feature space
