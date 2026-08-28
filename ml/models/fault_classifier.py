"""طبقه‌بند عیب تجهیزات دوار (FR-08، FR-09).

پیاده‌سازی مرجع: Gradient Boosting روی بردار ویژگی مهندسی‌شده (ML واقعی، قابل آموزش).
جایگزین یادگیری عمیق (CNN+LSTM روی طیف/سری‌زمانی خام) در `deep_fault_net.py` با
همان رابط قرار می‌گیرد؛ برای استقرار پیش‌فرض که وابستگی torch اختیاری است از GBM
استفاده می‌شود. اگر artifact موجود نباشد، `RuleBasedClassifier` به‌عنوان fallback
از امضاهای فرکانسی `services.common.domain.faults` استفاده می‌کند.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from ml.features.extract import FEATURE_ORDER, to_vector
from services.common.domain.enums import FaultType
from services.common.domain.faults import SIGNATURES

MODEL_FILENAME = "fault_classifier.joblib"


class FaultClassifier:
    """پوشش مدل sklearn با پیش‌بینی احتمال کلاس + شدت."""

    def __init__(self, estimator, classes: list[str], feature_order: list[str]) -> None:
        self.estimator = estimator
        self.classes = classes
        self.feature_order = feature_order

    @classmethod
    def load(cls, model_dir: str | Path) -> "FaultClassifier | RuleBasedClassifier":
        path = Path(model_dir) / MODEL_FILENAME
        if path.exists():
            blob = joblib.load(path)
            return cls(blob["estimator"], blob["classes"], blob["feature_order"])
        return RuleBasedClassifier()

    def save(self, model_dir: str | Path) -> Path:
        d = Path(model_dir)
        d.mkdir(parents=True, exist_ok=True)
        path = d / MODEL_FILENAME
        joblib.dump(
            {"estimator": self.estimator, "classes": self.classes, "feature_order": self.feature_order},
            path,
        )
        return path

    def predict(self, feats: dict[str, float]) -> tuple[FaultType, float, float]:
        vec = np.array([feats.get(k, 0.0) for k in self.feature_order], dtype=np.float32).reshape(1, -1)
        proba = self.estimator.predict_proba(vec)[0]
        idx = int(np.argmax(proba))
        fault = FaultType(self.classes[idx])
        confidence = float(proba[idx])
        severity = _severity_from_features(feats, fault)
        return fault, severity, confidence


class RuleBasedClassifier:
    """fallback بدون آموزش — امتیازدهی بر اساس نسبت دامنه در مضارب مشخصه."""

    feature_order = FEATURE_ORDER
    classes = [f.value for f in SIGNATURES]

    def predict(self, feats: dict[str, float]) -> tuple[FaultType, float, float]:
        scores: dict[FaultType, float] = {}
        one_x = feats.get("ord_1x", 1e-9) or 1e-9
        for fault, sig in SIGNATURES.items():
            if fault == FaultType.NORMAL:
                scores[fault] = 1.0 / (1.0 + feats.get("rms", 0) * 20 + abs(feats.get("kurtosis", 0)))
                continue
            s = 0.0
            for order in sig.dominant_orders:
                key = f"ord_{order:g}x"
                s += feats.get(key, 0.0) / one_x
            if sig.broadband:
                s += feats.get("hf_energy_ratio", 0) * 3 + max(0, feats.get("envelope_kurtosis", 0)) * 0.3
            if fault == FaultType.MECHANICAL_LOOSENESS:
                s += feats.get("half_order_sum", 0) * 2
            if fault == FaultType.MISALIGNMENT:
                s += feats.get("ratio_2x_1x", 0) * 2
            scores[fault] = s
        total = sum(scores.values()) or 1e-9
        best = max(scores, key=scores.get)
        confidence = scores[best] / total
        severity = _severity_from_features(feats, best)
        return best, severity, float(min(0.99, confidence))


def _severity_from_features(feats: dict[str, float], fault: FaultType) -> float:
    if fault == FaultType.NORMAL:
        return 0.0
    rms = feats.get("rms", 0.0)
    kurt = max(0.0, feats.get("kurtosis", 0.0))
    crest = feats.get("crest_factor", 1.4)
    # نرمال‌سازی تجربی به بازه‌ی ۰..۱
    sev = 0.5 * np.tanh(rms * 6) + 0.3 * np.tanh(kurt / 8) + 0.2 * np.tanh((crest - 1.4) / 3)
    return float(np.clip(sev, 0.0, 1.0))
