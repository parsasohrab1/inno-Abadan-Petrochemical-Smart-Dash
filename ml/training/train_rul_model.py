"""آموزش تخمین‌گر RUL روی داده‌ی سنتتیک روند عیب (FR-11: دقت ±۵٪ هدف)."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.model_selection import train_test_split

from ml.datagen.rul import synth_rul_row
from ml.models.rul_estimator import RulEstimator
from services.common.config import get_settings
from services.common.logging import get_logger

log = get_logger("train.rul")
N = 20000


def main() -> None:
    settings = get_settings()
    rng = np.random.default_rng(11)
    X, y = [], []
    for _ in range(N):
        sev = rng.beta(1.5, 3)
        slope = abs(rng.normal(0, 0.03))
        age = rng.uniform(0.02, 0.95)
        vec, rul = synth_rul_row(sev, slope, age, rng)
        X.append(vec)
        y.append(rul)
    X, y = np.array(X), np.array(y)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=5)

    reg = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, random_state=5)
    reg.fit(X_tr, y_tr)
    mape = mean_absolute_percentage_error(y_te, reg.predict(X_te))
    log.info("train.rul.mape", mape=round(float(mape), 4))

    path = RulEstimator(reg).save(settings.model_registry_path)
    log.info("train.rul.saved", path=str(path))


if __name__ == "__main__":
    main()
