"""تخمین‌گر RUL (FR-11) — رگرسیون Gradient Boosting روی شاخص‌های روند عیب.

ورودی: [severity, trend_slope, age_fraction, life_scale]  → خروجی: RUL بر حسب ساعت.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

MODEL_FILENAME = "rul_estimator.joblib"
RUL_INPUT = ["severity", "trend_slope", "age_fraction", "life_scale"]


class RulEstimator:
    def __init__(self, estimator=None) -> None:
        self.estimator = estimator

    @classmethod
    def load(cls, model_dir: str | Path) -> "RulEstimator":
        path = Path(model_dir) / MODEL_FILENAME
        if path.exists():
            return cls(joblib.load(path))
        return cls(None)

    def save(self, model_dir: str | Path) -> Path:
        d = Path(model_dir)
        d.mkdir(parents=True, exist_ok=True)
        path = d / MODEL_FILENAME
        joblib.dump(self.estimator, path)
        return path

    def predict(self, severity: float, trend_slope: float, age_fraction: float, life_scale: float = 0.5) -> tuple[float, float]:
        if self.estimator is None:
            # fallback تحلیلی
            base = 45000.0 * life_scale
            rem = base * max(0.02, (1 - severity) ** 2) * max(0.05, 1 - 8 * max(trend_slope, 0))
            return float(rem), 0.5
        x = np.array([[severity, trend_slope, age_fraction, life_scale]], dtype=np.float32)
        pred = float(self.estimator.predict(x)[0])
        # اعتماد بر اساس فاصله از مرزهای آموزش
        conf = float(np.clip(1.0 - 0.4 * severity - 0.3 * abs(trend_slope) * 5, 0.3, 0.97))
        return max(0.0, pred), conf
