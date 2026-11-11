"""
Inference for the trained WELLBEING (stress-risk) model.

What this model does
--------------------
The student answers a short questionnaire (sleep, study hours, assignment load ...).
The model returns a stress-risk class - Low / Medium / High - with a probability for
each class, plus the questionnaire answers that pushed the result up or down.

How it was made (see ml_training/wellbeing_train.py)
----------------------------------------------------
Trained offline with scikit-learn on a public survey dataset of university students.
The learned numbers (scaler + coefficients) are saved in app/ml/wellbeing_weights.json.
This file only LOADS that JSON and does the arithmetic, so:

  * the running web app does not need scikit-learn or numpy;
  * a prediction takes microseconds (far inside the 3-second latency target);
  * everything runs locally - no external AI service is contacted;
  * if the weights file is missing the feature switches itself off cleanly
    (`MODEL is None`) instead of crashing the app.

The model is a multinomial logistic regression chosen because it is accurate enough
for this problem AND explainable: each answer has one coefficient per class, so we
can show the student exactly which answers raised or lowered their risk.

The questionnaire itself is described INSIDE the weights file ("features"): the
question text, allowed range or options. The web form is generated from that
description, so the questions, the validation and the model can never drift apart.
"""
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

WEIGHTS_PATH = Path(__file__).with_name("wellbeing_weights.json")

# The class we call "high risk" and its opposite; the explanation is built from the
# difference between their coefficients (what makes High more likely than Low).
HIGH, LOW = "High", "Low"


class AnswerError(ValueError):
    """The student's answers do not match the questionnaire (message is safe to show)."""


@dataclass(frozen=True)
class WellbeingModel:
    version: str
    kind: str
    trained_on: str
    labels: list[str]                 # e.g. ["Low", "Medium", "High"]
    features: list[dict]              # questionnaire description (see module docstring)
    columns: list[str]                # model input columns after one-hot encoding
    mean: list[float]                 # StandardScaler mean per column
    scale: list[float]                # StandardScaler scale per column
    coef: list[list[float]]           # [class][column]
    intercept: list[float]            # [class]
    metrics: dict                     # held-out test results, shown in the UI "model card"
    card: dict                        # limitations and notes shown in the UI

    # ---------- questionnaire ----------
    def validate(self, answers: dict[str, Any]) -> dict[str, Any]:
        """
        Check the answers against the questionnaire and return a cleaned copy.

        Why strict validation: the answers come from the browser, so they are untrusted
        input (OWASP A03). Every feature must be present, numbers must be finite and inside
        the range seen in training, and choices must be one of the listed options.
        Unknown keys are rejected so nothing unexpected is stored in the database.
        """
        if not isinstance(answers, dict):
            raise AnswerError("Answers must be an object.")
        known = {f["name"] for f in self.features}
        extra = set(answers) - known
        if extra:
            raise AnswerError("Unknown question(s): " + ", ".join(sorted(map(str, extra))[:3]))
        clean: dict[str, Any] = {}
        for f in self.features:
            name = f["name"]
            if name not in answers:
                raise AnswerError(f"Please answer: {f['label']}")
            value = answers[name]
            if f["type"] == "number":
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise AnswerError(f"'{f['label']}' must be a number.")
                if not f["min"] <= value <= f["max"]:
                    raise AnswerError(f"'{f['label']}' must be between {f['min']} and {f['max']}.")
                clean[name] = float(value)
            else:  # "choice"
                allowed = {o["value"] for o in f["options"]}
                if not isinstance(value, str) or value not in allowed:
                    raise AnswerError(f"'{f['label']}' must be one of: " + ", ".join(sorted(allowed)))
                clean[name] = value
        return clean

    def _encode(self, clean: dict[str, Any]) -> list[float]:
        """Turn the cleaned answers into the numeric vector the model was trained on."""
        row = []
        for col in self.columns:
            if "=" in col:                      # one-hot column, e.g. "Assignment_Load=High"
                name, option = col.split("=", 1)
                row.append(1.0 if clean.get(name) == option else 0.0)
            else:
                row.append(float(clean[col]))
        return row

    # ---------- prediction ----------
    def predict(self, answers: dict[str, Any]) -> dict:
        clean = self.validate(answers)
        x = self._encode(clean)
        # Standardise exactly as in training (so 0 means "an average student in the data").
        xs = [(v - m) / s if s else 0.0 for v, m, s in zip(x, self.mean, self.scale)]

        # logistic regression: one linear score per class, then softmax -> probabilities
        logits = [sum(w * v for w, v in zip(row, xs)) + b for row, b in zip(self.coef, self.intercept)]
        top = max(logits)
        exps = [math.exp(z - top) for z in logits]       # subtract max for numerical stability
        total = sum(exps)
        probs = [e / total for e in exps]
        best = max(range(len(probs)), key=probs.__getitem__)

        up, down = self._factors(clean, xs)
        return {
            "label": self.labels[best],
            "probabilities": {lab: round(p, 4) for lab, p in zip(self.labels, probs)},
            "confidence": round(probs[best], 4),
            "factors_up": up,
            "factors_down": down,
            "answers": clean,
        }

    def _factors(self, clean: dict[str, Any], xs: list[float]) -> tuple[list[dict], list[dict]]:
        """
        Which answers moved this student's result towards High (up) or Low (down)?

        For every question we add up (coefficient_High - coefficient_Low) x standardised value
        over its model columns. A positive number means "this answer makes High more likely
        than Low, compared with an average student in the training data".
        """
        if HIGH not in self.labels or LOW not in self.labels:
            return [], []
        hi, lo = self.labels.index(HIGH), self.labels.index(LOW)
        margin = [h - l for h, l in zip(self.coef[hi], self.coef[lo])]
        per_feature: dict[str, float] = {}
        for col, m, v in zip(self.columns, margin, xs):
            name = col.split("=", 1)[0]
            per_feature[name] = per_feature.get(name, 0.0) + m * v

        meta = {f["name"]: f for f in self.features}
        rows = []
        for name, effect in per_feature.items():
            f = meta[name]
            value = clean[name]
            if f["type"] == "number":
                shown = f"{value:g}" + (f" {f['unit']}" if f.get("unit") else "")
            else:
                shown = next((o["label"] for o in f["options"] if o["value"] == value), str(value))
            rows.append({"feature": name, "label": f["label"], "value": shown, "effect": round(effect, 3),
                         "tip": f.get("tip", "")})
        up = sorted((r for r in rows if r["effect"] > 0.05), key=lambda r: -r["effect"])[:3]
        down = sorted((r for r in rows if r["effect"] < -0.05), key=lambda r: r["effect"])[:3]
        return up, down

    # ---------- public description (for the web form and the "model card") ----------
    def public_info(self) -> dict:
        return {
            "version": self.version, "kind": self.kind, "trained_on": self.trained_on,
            "labels": self.labels, "questions": self.features, "metrics": self.metrics, "card": self.card,
        }


def load_model(path: Path = WEIGHTS_PATH) -> Optional[WellbeingModel]:
    """Load the weights file; return None (feature switched off) if it is missing or malformed."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        model = WellbeingModel(
            version=raw["version"], kind=raw["kind"], trained_on=raw["trained_on"], labels=raw["labels"],
            features=raw["features"], columns=raw["columns"], mean=raw["scaler_mean"], scale=raw["scaler_scale"],
            coef=raw["coef"], intercept=raw["intercept"], metrics=raw.get("metrics", {}), card=raw.get("card", {}),
        )
        n = len(model.columns)
        # Sanity checks so a half-written or hand-edited file can never produce silent nonsense.
        if not (len(model.mean) == len(model.scale) == n and all(len(r) == n for r in model.coef)
                and len(model.coef) == len(model.labels) == len(model.intercept)):
            return None
        return model
    except (OSError, KeyError, ValueError, TypeError):
        return None


# Loaded once when the server starts (None if the model has not been trained yet).
MODEL: Optional[WellbeingModel] = load_model()
