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
    """fallback بدون آموزش — امتیازدهی هیوریستیک بر پایه‌ی امضاهای فرکانسی/پاکت.

    فقط زمانی استفاده می‌شود که artifact مدل آموزش‌دیده موجود نباشد. دقت آن پایین‌تر
    از مدل GBM است و برای رعایت NFR-08 باید `python -m ml.training.train_fault_model` اجرا شود.
    """

    feature_order = FEATURE_ORDER
    classes = [f.value for f in SIGNATURES]

    def predict(self, feats: dict[str, float]) -> tuple[FaultType, float, float]:
        one_x = feats.get("ord_1x", 1e-9) or 1e-9
        g = feats.get
        scores: dict[FaultType, float] = {
            FaultType.NORMAL: 1.0 / (1.0 + g("rms", 0) * 25 + abs(g("kurtosis", 0)) * 0.5),
            FaultType.UNBALANCE: g("ord_1x", 0) / one_x - g("harmonic_sum", 0) * 0.3,
            FaultType.MISALIGNMENT: g("ratio_2x_1x", 0) * 2 + g("ratio_3x_1x", 0),
            FaultType.MECHANICAL_LOOSENESS: g("half_order_sum", 0) * 2 + g("impulse_factor", 0) * 0.2,
            FaultType.ROTOR_RUB: g("sub_synchronous", 0) * 1.5 + g("mid_band_peakiness", 0) * 0.05
            + g("ord_0.33x", 0) / one_x,
            FaultType.BENT_SHAFT: g("ord_1x", 0) / one_x + g("ratio_2x_1x", 0) * 1.2,
            FaultType.BEARING_OUTER_RACE: g("env_bpfo", 0) - g("env_bpfi_sidebands", 0) * 0.5,
            FaultType.BEARING_INNER_RACE: g("env_bpfi", 0) + g("env_bpfi_sidebands", 0),
            FaultType.BEARING_BALL: g("env_bsf", 0) + g("env_bsf_sidebands", 0),
            FaultType.BEARING_CAGE: g("env_ftf", 0) + g("be_500_1500", 0) * 2,
            FaultType.GEAR_MESH_WEAR: g("gmf_ratio", 0) * 3,
            FaultType.BROKEN_ROTOR_BAR: g("env_pole_pass", 0) * 1.5,
            FaultType.OIL_WHIRL: g("oil_whirl_ratio", 0) * 2 + min(g("oil_whirl_no_harmonic", 0), 5),
            FaultType.CAVITATION: g("spectral_flatness", 0) * 4 + g("hf_energy_ratio", 0) * 2,
            FaultType.RESONANCE: g("mid_band_peakiness", 0) * 0.08 + g("be_1500_2500", 0) * 3,
            FaultType.BELT_DEFECT: g("belt_series", 0) * 2,
            FaultType.ELECTRICAL_STATOR: g("line_100hz", 0) * 3,
        }
        best = max(scores, key=lambda k: scores[k])
        positive = {k: max(0.0, v) for k, v in scores.items()}
        total = sum(positive.values()) or 1e-9
        confidence = positive[best] / total
        severity = _severity_from_features(feats, best)
        return best, severity, float(min(0.99, max(0.05, confidence)))


def _severity_from_features(feats: dict[str, float], fault: FaultType) -> float:
    if fault == FaultType.NORMAL:
        return 0.0
    rms = feats.get("rms", 0.0)
    kurt = max(0.0, feats.get("kurtosis", 0.0))
    crest = feats.get("crest_factor", 1.4)
    # نرمال‌سازی تجربی به بازه‌ی ۰..۱
    sev = 0.5 * np.tanh(rms * 6) + 0.3 * np.tanh(kurt / 8) + 0.2 * np.tanh((crest - 1.4) / 3)
    return float(np.clip(sev, 0.0, 1.0))
