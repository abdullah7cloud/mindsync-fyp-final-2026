"""
Pure-Python inference for the trained task-fit model.

The model is TRAINED offline with scikit-learn (ml_training/train.py) and
its learned parameters are saved to app/ml/model_weights.json. At run time
this file simply loads that JSON and does a few multiplications, so:

  * the web app needs no scikit-learn/numpy (fewer packages to install),
  * prediction takes microseconds (well inside the 3-second latency target),
  * it works fully offline,
  * if the weights file is missing or broken, `load_model()` returns None and
    the app silently falls back to the plain heuristic.
"""
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.ml.features import FEATURE_NAMES

WEIGHTS_PATH = Path(__file__).with_name("model_weights.json")


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


@dataclass(frozen=True)
class TaskFitModel:
    kind: str                       # "logistic_regression" or "mlp"
    mean: list[float]
    scale: list[float]
    layers: list[tuple[list[list[float]], list[float]]]   # [(W, b), ...]
    version: str
    trained_on: str
    evaluation: dict            # held-out test results, shown in the dashboard's model panel

    def predict_proba(self, features: list[float]) -> float:
        """Probability (0..1) that this task is a good fit for the student right now."""
        # Standardise with the SAME mean/scale as in training (from the training set only).
        x = [(f - m) / s if s else 0.0 for f, m, s in zip(features, self.mean, self.scale)]
        for i, (weights, bias) in enumerate(self.layers):
            # weights has shape [n_in][n_out]
            out = [
                sum(x[r] * weights[r][c] for r in range(len(x))) + bias[c]
                for c in range(len(bias))
            ]
            last = i == len(self.layers) - 1
            x = out if last else [max(0.0, v) for v in out]   # ReLU on hidden layers
        # Logistic regression = one layer; the sigmoid turns the linear score into a 0..1 probability.
        return _sigmoid(x[0])


def load_model(path: Path = WEIGHTS_PATH) -> Optional[TaskFitModel]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw["feature_names"] != FEATURE_NAMES:
            return None   # weights were trained on different features - do not use
        return TaskFitModel(
            kind=raw["kind"],
            mean=raw["scaler_mean"],
            scale=raw["scaler_scale"],
            layers=[(layer["weights"], layer["bias"]) for layer in raw["layers"]],
            version=raw["version"],
            trained_on=raw["trained_on"],
            evaluation=raw.get("evaluation", {}),
        )
    except (OSError, KeyError, ValueError, TypeError):
        return None


# Loaded once when the server starts.
MODEL: Optional[TaskFitModel] = load_model()


def task_fit_scorer(task, energy_level: int, now) -> float:
    """Adapter with the signature heuristic.rank_tasks expects (see MlScorer)."""
    from app.ml.features import build_features, hours_until

    if MODEL is None:
        raise RuntimeError("model not loaded")
    return MODEL.predict_proba(
        build_features(task.difficulty, energy_level, hours_until(task.deadline, now))
    )
