"""Synthetic process data (pressure/temperature/flow/level) — README §10 (process data row).

The line production rate is modeled with slow noise + a loss effect caused by the health of critical equipment;
this rate is the input to the "instantaneous profit" calculation in the economics service.
"""
from __future__ import annotations

import math

import numpy as np


def line_flow_tph(
    design_rate_tph: float,
    t_seconds: float,
    availability: float = 1.0,
    rng: np.random.Generator | None = None,
) -> float:
    """Instantaneous line production rate. availability ∈ [0,1] from the mean health of the line's equipment."""
    rng = rng or np.random.default_rng()
    if design_rate_tph <= 0:
        return 0.0
    diurnal = 0.03 * math.sin(2 * math.pi * t_seconds / 86400.0)
    drift = 0.02 * math.sin(2 * math.pi * t_seconds / (7 * 86400.0))
    noise = rng.normal(0, 0.01)
    factor = max(0.0, availability * (0.95 + diurnal + drift + noise))
    return round(design_rate_tph * factor, 4)


def process_point(
    kind: str, nominal: float, t_seconds: float, rng: np.random.Generator | None = None
) -> float:
    rng = rng or np.random.default_rng()
    osc = {
        "pressure": 0.02, "temperature_rtd": 0.015, "temperature_tc": 0.015,
        "flow_meter": 0.03, "level": 0.05, "gas_detector": 0.0,
    }.get(kind, 0.02)
    val = nominal * (1 + osc * math.sin(2 * math.pi * t_seconds / 600.0) + rng.normal(0, osc / 2))
    if kind == "gas_detector":
        val = max(0.0, rng.exponential(0.4) + (8.0 if rng.random() < 0.002 else 0.0))
    return round(val, 4)


def power_draw_kw(rated_kw: float, load: float, rng: np.random.Generator | None = None) -> float:
    rng = rng or np.random.default_rng()
    return round(rated_kw * (0.35 + 0.6 * load) * (1 + rng.normal(0, 0.02)), 2)
