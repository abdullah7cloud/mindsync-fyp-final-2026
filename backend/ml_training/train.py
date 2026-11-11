"""
Train, evaluate and export the MindSync TASK-FIT model (a prototype trained on SIMULATED data).

Run from the backend/ folder:

    pip install -r requirements-train.txt
    python -m ml_training.train

What it does
  1. Generates synthetic study-attempt data (see synth_data.py - read its honesty note).
  2. Splits it 60 % TRAIN / 20 % VALIDATION / 20 % TEST (stratified, fixed seed).
  3. Trains candidate models on the TRAIN part and compares them on the VALIDATION part only:
     logistic regression (several regularisation strengths C), a small neural network (MLP) with
     different sizes, and gradient boosting (reference only).
  4. Refits the winner on train + validation, then evaluates it ONCE on the untouched TEST part,
     next to the hand-written heuristic used as a baseline. Also runs 5-fold cross-validation.
  5. Exports the model (scaler + weights) to app/ml/model_weights.json so the web app can use it
     without scikit-learn, and writes ml_training/metrics.json for the report.

Why the validation set exists: if we picked the best model by looking at the TEST scores, the test
score would be optimistic ("peeking"). Validation is for choosing, test is for reporting once.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from app.heuristic import compute_deadline_score, compute_energy_match_score, DEADLINE_WEIGHT, ENERGY_MATCH_WEIGHT
from app.ml.features import FEATURE_NAMES
from ml_training.synth_data import generate

SEED = 42
N_SAMPLES = 20000
ROOT = Path(__file__).resolve().parent
WEIGHTS_OUT = ROOT.parent / "app" / "ml" / "model_weights.json"
METRICS_OUT = ROOT / "metrics.json"


def heuristic_score_column(X: np.ndarray) -> np.ndarray:
    """The existing heuristic's score for each row, used as a baseline predictor."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scores = []
    for row in X:
        difficulty, energy = int(row[0]), int(row[1])
        # recover hours_left from log1p (and the overdue flag)
        hours = float(np.expm1(row[4]))
        if row[5] == 1.0:
            hours = -1.0
        dl = compute_deadline_score(now + timedelta(hours=hours), now)
        em = compute_energy_match_score(difficulty, energy)
        scores.append(DEADLINE_WEIGHT * dl + ENERGY_MATCH_WEIGHT * em)
    return np.array(scores)


def metrics(y_true, proba):
    pred = (proba >= 0.5).astype(int)
    return {
        "roc_auc": round(float(roc_auc_score(y_true, proba)), 4),
        "accuracy": round(float(accuracy_score(y_true, pred)), 4),
        "brier": round(float(brier_score_loss(y_true, proba)), 4),
    }


def export(model, scaler, kind: str, trained_on: str, evaluation: dict | None = None) -> dict:
    if kind == "logistic_regression":
        layers = [{"weights": model.coef_.T.tolist(), "bias": model.intercept_.tolist()}]
    else:
        layers = [
            {"weights": w.tolist(), "bias": b.tolist()}
            for w, b in zip(model.coefs_, model.intercepts_)
        ]
    return {
        "version": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "kind": kind,
        "trained_on": trained_on,
        "feature_names": FEATURE_NAMES,
        # evaluation numbers are stored with the model so the app's "How the models work" panel can show them
        "evaluation": evaluation or {},
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "layers": layers,
    }


def main() -> None:
    X_list, y_list = generate(N_SAMPLES, SEED)
    X, y = np.array(X_list), np.array(y_list)

    # 60 / 20 / 20 split: first cut off 20 % for TEST, then 25 % of the remainder (= 20 % of all) for VALIDATION.
    X_trva, X_te, y_trva, y_te = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    X_tr, X_va, y_tr, y_va = train_test_split(X_trva, y_trva, test_size=0.25, random_state=SEED, stratify=y_trva)

    # The scaler is fitted on TRAIN only and re-used for validation (no information leaks from validation).
    scaler = StandardScaler().fit(X_tr)
    Xs_tr, Xs_va = scaler.transform(X_tr), scaler.transform(X_va)

    candidates = {}
    for C in (0.01, 0.1, 1.0, 10.0):
        candidates[f"logistic_regression_C={C}"] = LogisticRegression(C=C, max_iter=1000)
    for h in (4, 8, 16):
        candidates[f"mlp_{h}_hidden"] = MLPClassifier(hidden_layer_sizes=(h,), activation="relu", max_iter=600,
                                                      random_state=SEED, early_stopping=True)
    candidates["gradient_boosting_reference"] = GradientBoostingClassifier(random_state=SEED)

    validation = {}
    for name, model in candidates.items():
        model.fit(Xs_tr, y_tr)
        validation[name] = metrics(y_va, model.predict_proba(Xs_va)[:, 1])

    exportable = [k for k in validation if k.startswith(("logistic_regression", "mlp"))]
    best_name = max(exportable, key=lambda k: validation[k]["roc_auc"])
    kind = "logistic_regression" if best_name.startswith("logistic") else "mlp"

    # Refit the chosen model on train + validation, then look at the TEST set exactly once.
    final_scaler = StandardScaler().fit(X_trva)
    final = candidates[best_name].__class__(**candidates[best_name].get_params())
    final.fit(final_scaler.transform(X_trva), y_trva)
    Xs_te = final_scaler.transform(X_te)
    test = {"shipped_model": metrics(y_te, final.predict_proba(Xs_te)[:, 1])}
    # baseline: the hand-written heuristic used as if it were a predictor (not a like-for-like contest)
    test["existing_heuristic_baseline"] = metrics(y_te, heuristic_score_column(X_te))
    ref = GradientBoostingClassifier(random_state=SEED).fit(final_scaler.transform(X_trva), y_trva)
    test["gradient_boosting_reference"] = metrics(y_te, ref.predict_proba(Xs_te)[:, 1])

    cv_scores = cross_val_score(candidates[best_name].__class__(**candidates[best_name].get_params()),
                                final_scaler.transform(X_trva), y_trva, scoring="roc_auc",
                                cv=StratifiedKFold(5, shuffle=True, random_state=SEED))

    trained_on = (f"synthetic data, n={N_SAMPLES}, seed={SEED} (simulated study attempts - "
                  f"see ml_training/synth_data.py)")
    evaluation = {
        "held_out_test_set": test["shipped_model"],
        "heuristic_baseline_on_same_test_set": test["existing_heuristic_baseline"],
        "cross_validation_roc_auc_mean": round(float(cv_scores.mean()), 4),
        "split_rows": {"train": int(len(y_tr)), "validation": int(len(y_va)), "test": int(len(y_te))},
        "data_is_simulated": True,
    }
    WEIGHTS_OUT.write_text(json.dumps(export(final, final_scaler, kind, trained_on, evaluation)), encoding="utf-8")

    report = {
        "n_samples": N_SAMPLES,
        "split_rows": {"train": int(len(y_tr)), "validation": int(len(y_va)), "test": int(len(y_te))},
        "positive_rate": round(float(y.mean()), 4),
        "feature_names": FEATURE_NAMES,
        "validation_set_results": validation,
        "chosen_by_validation": best_name,
        "test_set_results": test,
        "cross_validation_roc_auc": {"mean": round(float(cv_scores.mean()), 4), "std": round(float(cv_scores.std()), 4), "folds": 5},
        "shipped_model": kind,
        "note": "Labels are simulated from stated assumptions; scores show the pipeline works, "
                "not real-world accuracy.",
    }
    METRICS_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nShipped model: {best_name} -> {WEIGHTS_OUT}")


if __name__ == "__main__":
    main()
