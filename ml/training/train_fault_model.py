"""آموزش طبقه‌بند عیب روی داده‌ی ارتعاش سنتتیک.

هدف NFR-08: دقت ≥ ۹۵٪. اگر دقت اعتبارسنجی از آستانه کمتر باشد، خروج با کد خطا.
اجرا: python -m ml.training.train_fault_model
"""
from __future__ import annotations

import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from ml.datagen.vibration import WaveformSpec, synth_waveform
from ml.features.extract import FEATURE_ORDER, extract_features, to_vector
from ml.models.fault_classifier import FaultClassifier
from services.common.config import get_settings
from services.common.domain.faults import ALL_FAULTS
from services.common.logging import get_logger

log = get_logger("train.fault")

SAMPLES_PER_FAULT = 420
RPMS = [740, 990, 1480, 1780, 2960, 3560, 4200, 6300, 8200]


def build_dataset(seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X, y = [], []
    for fault in ALL_FAULTS:
        for _ in range(SAMPLES_PER_FAULT):
            rpm = float(rng.choice(RPMS)) * float(rng.uniform(0.97, 1.03))
            severity = (
                0.0 if fault.value == "normal" else float(rng.uniform(0.12, 1.0))
            )
            # تنوع دامنه‌ی پایه و نویز برای تعمیم‌پذیری بهتر
            spec = WaveformSpec(
                rpm=rpm,
                base_g=float(rng.uniform(0.035, 0.07)),
                noise_g=float(rng.uniform(0.004, 0.014)),
            )
            wave = synth_waveform(fault, severity, spec, rng)
            feats = extract_features(wave, spec.fs, rpm)
            X.append(to_vector(feats))
            y.append(fault.value)
    return np.array(X), np.array(y)


def main() -> None:
    settings = get_settings()
    log.info("train.fault.start", samples=SAMPLES_PER_FAULT * len(ALL_FAULTS))
    X, y = build_dataset()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.22, stratify=y, random_state=7)

    clf = HistGradientBoostingClassifier(max_iter=350, learning_rate=0.08, max_depth=None,
                                         l2_regularization=0.1, random_state=7)
    clf.fit(X_tr, y_tr)
    acc = clf.score(X_te, y_te)
    log.info("train.fault.accuracy", accuracy=round(acc, 4))
    print(classification_report(y_te, clf.predict(X_te)))
    print("confusion matrix:\n", confusion_matrix(y_te, clf.predict(X_te)))

    model = FaultClassifier(clf, classes=list(clf.classes_), feature_order=FEATURE_ORDER)
    path = model.save(settings.model_registry_path)
    log.info("train.fault.saved", path=str(path))

    if acc < settings.fault_detection_min_accuracy:
        log.error("train.fault.below_target", target=settings.fault_detection_min_accuracy)
        sys.exit(1)


if __name__ == "__main__":
    main()
