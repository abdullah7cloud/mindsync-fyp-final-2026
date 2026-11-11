"""
Train, evaluate and export the MindSync WELLBEING (stress-risk) model.

Run from the backend/ folder:

    pip install -r requirements-train.txt
    python -m ml_training.wellbeing_train --csv data/university_student_stress.csv

WHAT THIS SCRIPT DOES, STEP BY STEP (read this before the viva)
----------------------------------------------------------------
 1. LOAD the public survey data (3,000 university students, CC BY 4.0, see docs/WELLBEING_MODEL.md).
 2. CHECK it: required columns, missing values, duplicate rows, class balance.
 3. CHOOSE FEATURES: only habits and workload a student can see and change (sleep, study hours ...).
    Demographics (age, gender, income ...) are left out on purpose: they are sensitive, the student
    cannot change them, and the script PROVES they add (almost) nothing (ablation in step 8).
 4. SPLIT the rows into TRAIN 60 % / VALIDATION 20 % / TEST 20 %, stratified so every part has the
    same share of Low / Medium / High. The test part is locked away until the very end.
 5. PREPROCESS: text answers -> one-hot columns; numbers -> standardised (mean 0, spread 1).
    The scaler is fitted on the TRAIN rows only - fitting it on all rows would leak information
    from the validation/test rows into training ("data leakage").
 6. TRAIN several models and pick the best on the VALIDATION set only:
       majority-class guess (baseline), decision tree, random forest, gradient boosting (reference),
       and multinomial logistic regression with several regularisation strengths C.
 7. FINAL MODEL: logistic regression (explainable: one coefficient per answer and class), refitted on
    train + validation, then evaluated ONCE on the untouched TEST set. Also 5-fold cross-validation.
 8. HONESTY CHECKS: (a) a model that is also given the dataset's own Stress_Score column - it should
    score ~100 %, which shows why that column must NOT be a feature; (b) a model with the demographic
    columns added - to show they are not needed; (c) how close the simple model gets to the best
    complex one.
 9. EXPORT the numbers the web app needs to a small JSON file (app/ml/wellbeing_weights.json) plus a
    metrics file (ml_training/wellbeing_metrics.json) that is copied into the report.

ALSO REPORTED (so every claim in the app has evidence behind it)
  * precision / recall / F1 for each class, the confusion matrix, 95 % bootstrap intervals;
  * CALIBRATION: do "70 %" predictions really come true about 70 % of the time? (reliability table + ECE);
  * how deterministic the dataset's own stress score is (can a plain formula rebuild it from the answers?),
    which tells us whether the model learns real-world stress or just the survey's scoring rule.

Other mode:   python -m ml_training.wellbeing_train --csv data/file.csv --inspect
  prints a profile of every column (type, range, values) WITHOUT training - use it to check that the
  questionnaire wording in ml_training/wellbeing_questions.json matches the real data.

The web app never imports scikit-learn: it only reads the JSON (see app/ml/wellbeing_model.py).
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

SEED = 42
SCREEN_MIN_GAIN = 0.01          # a question must improve validation log-loss by at least this much to be kept
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT.parent
DEFAULT_WEIGHTS = BACKEND / "app" / "ml" / "wellbeing_weights.json"
DEFAULT_METRICS = ROOT / "wellbeing_metrics.json"
DEFAULT_QUESTIONS = ROOT / "wellbeing_questions.json"

TARGET = "Stress_Level"
LEAKY = "Stress_Score"            # the label was computed from this score -> never a feature
LABEL_ORDER = ["Low", "Medium", "High"]

# Habits and workload the student can answer and change. (Demographic columns are deliberately absent.)
MODIFIABLE = [
    "Study_Hours", "Class_Attendance", "Exam_Frequency", "Assignment_Load", "Sleep_Hours",
    "Social_Media_Use", "Screen_Time", "Physical_Exercise", "Peer_Pressure", "Family_Support", "Anxiety_Level",
]
DEMOGRAPHIC = ["Age", "Gender", "University_Type", "Tuition", "Family_Income_Level"]


# --------------------------------------------------------------------------- loading and checking
def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    if TARGET not in df.columns:
        sys.exit(f"The CSV must contain a '{TARGET}' column. Found: {list(df.columns)}")
    df[TARGET] = df[TARGET].astype(str).str.strip().str.title()
    bad = set(df[TARGET].unique()) - set(LABEL_ORDER)
    if bad:
        sys.exit(f"Unexpected values in {TARGET}: {sorted(bad)} (expected {LABEL_ORDER})")
    return df


def data_checks(df: pd.DataFrame, features: list[str]) -> dict:
    """Basic data-quality report that goes into the metrics file (and the report)."""
    counts = df[TARGET].value_counts().reindex(LABEL_ORDER).fillna(0).astype(int)
    return {
        "rows": int(len(df)),
        "missing_values_in_used_columns": int(df[features + [TARGET]].isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "class_counts": {k: int(v) for k, v in counts.items()},
        "class_share": {k: round(float(v) / len(df), 4) for k, v in counts.items()},
    }


# --------------------------------------------------------------------------- questionnaire description
def prettify(name: str) -> str:
    return name.replace("_", " ").strip().capitalize()


def describe_features(df: pd.DataFrame, features: list[str], questions_file: Path) -> list[dict]:
    """
    Describe every question (type, allowed range or options, human wording).

    The ranges/options come from the DATA, so validation in the app matches what the model has
    actually seen. The wording (label, help text, unit, tip) comes from wellbeing_questions.json,
    which is written by hand from the dataset documentation.
    """
    wording = json.loads(questions_file.read_text(encoding="utf-8")) if questions_file.exists() else {}
    out = []
    for name in features:
        col = df[name]
        w = wording.get(name, {})
        item = {"name": name, "label": w.get("label", prettify(name)), "help": w.get("help", ""),
                "tip": w.get("tip", ""), "unit": w.get("unit", "")}
        if pd.api.types.is_numeric_dtype(col):
            lo, hi = float(col.min()), float(col.max())
            integers = bool(np.all(np.mod(col.dropna(), 1) == 0))
            item.update(type="number", min=lo, max=hi, step=1 if integers else 0.5)
        else:
            values = sorted(col.dropna().astype(str).str.strip().unique(),
                            key=lambda v: (["Low", "Medium", "High"].index(v) if v in ("Low", "Medium", "High") else 99, v))
            labels = w.get("options", {})
            item.update(type="choice", options=[{"value": v, "label": labels.get(v, v)} for v in values])
        out.append(item)
    return out


def encode(df: pd.DataFrame, features_meta: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """Numbers stay numbers; each text answer becomes one 0/1 column called  'Feature=Value'."""
    cols, data = [], {}
    for f in features_meta:
        if f["type"] == "number":
            data[f["name"]] = df[f["name"]].astype(float).to_numpy()
            cols.append(f["name"])
        else:
            for opt in f["options"]:
                key = f"{f['name']}={opt['value']}"
                data[key] = (df[f["name"]].astype(str).str.strip() == opt["value"]).astype(float).to_numpy()
                cols.append(key)
    return pd.DataFrame(data, index=df.index)[cols], cols


# --------------------------------------------------------------------------- metrics
def evaluate(model, X, y_idx, n_classes: int) -> dict:
    """Accuracy, macro-F1, per-class P/R/F1, confusion matrix, log-loss and one-vs-rest ROC-AUC."""
    proba = model.predict_proba(X)
    pred = proba.argmax(axis=1)
    p, r, f1, support = precision_recall_fscore_support(y_idx, pred, labels=list(range(n_classes)), zero_division=0)
    try:
        auc = float(roc_auc_score(y_idx, proba, multi_class="ovr", average="macro"))
    except ValueError:
        auc = float("nan")
    return {
        "accuracy": round(float(accuracy_score(y_idx, pred)), 4),
        "macro_f1": round(float(f1_score(y_idx, pred, average="macro")), 4),
        "log_loss": round(float(log_loss(y_idx, proba, labels=list(range(n_classes)))), 4),
        "roc_auc_ovr": None if math.isnan(auc) else round(auc, 4),
        "per_class": {LABEL_ORDER[i]: {"precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4),
                                       "f1": round(float(f1[i]), 4), "n": int(support[i])} for i in range(n_classes)},
        "confusion_matrix_rows_true_cols_pred": confusion_matrix(y_idx, pred, labels=list(range(n_classes))).tolist(),
    }


def calibration(proba: np.ndarray, y_idx: np.ndarray, n_classes: int, bins: int = 10) -> dict:
    """
    Does a stated probability mean what it says?

    Top-label reliability: group predictions by their confidence (the probability of the class we
    predicted); in each group compare the average confidence with how often the prediction was right.
    ECE (expected calibration error) = weighted average gap. A small ECE means "70 %" is about 70 %.
    Brier score = mean squared error of the probabilities (0 = perfect; lower is better).
    """
    conf = proba.max(axis=1)
    pred = proba.argmax(axis=1)
    right = (pred == y_idx).astype(float)
    edges = np.linspace(1.0 / n_classes, 1.0, bins + 1)
    table, ece = [], 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf > lo) & (conf <= hi) if lo > edges[0] else (conf >= lo) & (conf <= hi)
        if mask.sum() == 0:
            continue
        gap = abs(conf[mask].mean() - right[mask].mean())
        ece += gap * mask.mean()
        table.append({"confidence_range": [round(float(lo), 3), round(float(hi), 3)], "n": int(mask.sum()),
                      "mean_confidence": round(float(conf[mask].mean()), 4), "observed_accuracy": round(float(right[mask].mean()), 4)})
    onehot = np.eye(n_classes)[y_idx]
    brier = float(((proba - onehot) ** 2).sum(axis=1).mean())
    return {"expected_calibration_error": round(float(ece), 4), "brier_score_multiclass": round(brier, 4), "reliability_table": table}


def bootstrap_ci(y_true, proba, n_boot: int = 1000, seed: int = SEED) -> dict:
    """95 % bootstrap intervals for accuracy and macro-F1: resample the test rows with replacement 1000 times."""
    rng = np.random.default_rng(seed)
    pred = proba.argmax(axis=1)
    accs, f1s = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y_true), len(y_true))
        accs.append(accuracy_score(y_true[idx], pred[idx]))
        f1s.append(f1_score(y_true[idx], pred[idx], average="macro"))
    q = lambda a: [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)]
    return {"accuracy_95ci": q(accs), "macro_f1_95ci": q(f1s)}


def score_structure(df: pd.DataFrame, X_all: pd.DataFrame, features: list[str]) -> dict:
    """
    How deterministic is the dataset's own Stress_Score?  Answers the question "does the model learn real
    stress, or only the survey authors' scoring rule?".
      * R^2 of a plain linear formula rebuilding Stress_Score from the answers (1.0 = perfectly rule-made);
      * the score range of each Low / Medium / High class (non-overlapping ranges mean the label is just
        score cut-offs).
    """
    if LEAKY not in df.columns or not pd.api.types.is_numeric_dtype(df[LEAKY]):
        return {}
    score = df[LEAKY].astype(float).to_numpy()
    out = {}
    out["r2_score_from_modifiable_answers_linear"] = round(float(LinearRegression().fit(X_all, score).score(X_all, score)), 4)
    others = [c for c in df.columns if c not in features + [TARGET, LEAKY]]
    if others:
        Xf = pd.concat([X_all, pd.get_dummies(df[others], dtype=float)], axis=1)
        out["r2_score_from_all_other_columns_linear"] = round(float(LinearRegression().fit(Xf, score).score(Xf, score)), 4)
    ranges = {lab: [round(float(df.loc[df[TARGET] == lab, LEAKY].min()), 3), round(float(df.loc[df[TARGET] == lab, LEAKY].max()), 3)]
              for lab in LABEL_ORDER if (df[TARGET] == lab).any()}
    out["score_range_per_class"] = ranges
    spans = sorted(ranges.values())
    out["classes_are_score_cutoffs"] = all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1))
    out["note"] = ("If the classes are pure score cut-offs and a linear formula rebuilds the score almost exactly, the label is a "
                   "rule applied to the answers. The model then predicts the survey's scoring rule, not independently measured stress.")
    return out



def screen_features(df: pd.DataFrame, meta: list[dict], y_idx: np.ndarray) -> dict:
    """
    Does each question carry any information about the label?  (Ablation test, validation set only.)

    For every question: refit a logistic regression WITHOUT its column(s) and see how much the validation
    log-loss gets worse.  A question whose removal changes nothing adds no information, so asking the student
    for it would be pointless.  Uses the same 60/20/20 row split as the real training (the split depends only on
    the labels and the seed), and never touches the test set.
    """
    X_all, _ = encode(df, meta)
    X_trva, _X_te, y_trva, _ = train_test_split(X_all, y_idx, test_size=0.20, random_state=SEED, stratify=y_idx)
    X_tr, X_va, y_tr, y_va = train_test_split(X_trva, y_trva, test_size=0.25, random_state=SEED, stratify=y_trva)

    def val_loss(cols):
        m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(X_tr[cols], y_tr)
        return float(log_loss(y_va, m.predict_proba(X_va[cols]), labels=[0, 1, 2]))
    full = val_loss(list(X_tr.columns))
    out = {}
    for f in meta:
        mine = [c for c in X_tr.columns if c == f["name"] or c.startswith(f["name"] + "=")]
        rest = [c for c in X_tr.columns if c not in mine]
        out[f["name"]] = {"validation_logloss_increase_when_removed": round(val_loss(rest) - full, 4)}
    return out


def dataset_forensics(df: pd.DataFrame, X_all: pd.DataFrame, features: list[str]) -> dict:
    """
    Is this dataset what it claims to be (a real survey)?  Three cheap checks, all reported honestly.

      1. Recovered scoring formula: a plain linear regression of Stress_Score on the answers. Coefficients that
         are whole numbers, with a residual near 0, mean the score is an exact integer formula of the answers.
      2. Uniformity: a chi-square test on each whole-number column. Real survey answers are rarely flat.
      3. Independence: the largest correlation between any two input columns. In real surveys related habits
         (screen time and social media, anxiety and sleep) usually correlate; here nothing does.
    None of this proves how the data was made. It shows how the model must be described.
    """
    from scipy import stats
    out: dict = {}
    if LEAKY in df.columns and pd.api.types.is_numeric_dtype(df[LEAKY]):
        score = df[LEAKY].astype(float).to_numpy()
        lin = LinearRegression().fit(X_all, score)
        coefs = {c: round(float(v), 4) for c, v in zip(X_all.columns, lin.coef_)}
        out["recovered_score_formula"] = {
            "coefficients_per_answer_column": coefs, "intercept": round(float(lin.intercept_), 4),
            "r2": round(float(lin.score(X_all, score)), 6),
            "max_abs_residual": float(np.abs(score - lin.predict(X_all)).max()),
            "columns_with_zero_weight": [c for c, v in coefs.items() if abs(v) < 1e-6],
        }
    nums = [c for c in features + [c for c in DEMOGRAPHIC if c in df.columns] if pd.api.types.is_numeric_dtype(df[c])]
    uni, n_whole = {}, 0
    for c in nums:
        col = df[c]
        if np.all(np.mod(col, 1) == 0) and col.nunique() <= 12:
            n_whole += 1
            uni[c] = round(float(stats.chisquare(col.value_counts().to_numpy())[1]), 3)
    out["uniformity_chi2_p_values"] = uni
    out["columns_consistent_with_uniform"] = f"{sum(p > 0.05 for p in uni.values())} of {len(uni)}"
    corr = df[nums].corr().abs().to_numpy().copy()
    np.fill_diagonal(corr, 0)
    out["largest_correlation_between_two_inputs"] = round(float(corr.max()), 3) if corr.size else None
    rec = out.get("recovered_score_formula", {})
    out["suspected_generated_data"] = bool(
        rec.get("r2", 0) > 0.999 and uni and all(p > 0.01 for p in uni.values()) and (out["largest_correlation_between_two_inputs"] or 1) < 0.1)
    out["interpretation"] = (
        "The stress score is an exact formula of the answers and the inputs look like independent, flat random numbers. "
        "That pattern is typical of computer-generated data and very unusual for a real questionnaire. It cannot be proven from the file "
        "alone (ask the dataset authors). Either way the model has learned the dataset's scoring rule, not independently measured stress."
        if out["suspected_generated_data"] else
        "No sign that the score is an exact formula of the answers.")
    return out


def inspect_csv(df: pd.DataFrame) -> None:
    """--inspect: print what is really in the file so the questionnaire wording can be checked against it."""
    print(f"ROWS: {len(df)}   COLUMNS: {len(df.columns)}\n")
    for c in df.columns:
        col = df[c]
        if pd.api.types.is_numeric_dtype(col):
            print(f"{c:22s} number  min={col.min():g}  max={col.max():g}  mean={col.mean():.2f}  distinct={col.nunique()}  missing={int(col.isna().sum())}")
        else:
            vals = col.astype(str).str.strip().value_counts().to_dict()
            print(f"{c:22s} text    values={vals}  missing={int(col.isna().sum())}")
    print("\nEXPECTED FEATURE COLUMNS PRESENT:", {c: (c in df.columns) for c in MODIFIABLE})


def check_wording(meta: list[dict], questions_file: Path) -> list[str]:
    """Warn when the hand-written wording file and the data disagree (a questionnaire that does not match the model)."""
    if not questions_file.exists():
        return [f"{questions_file.name} not found: questions will use plain column names."]
    wording = json.loads(questions_file.read_text(encoding="utf-8"))
    names = {m["name"] for m in meta}
    notes = [f"wording for '{k}' has no matching feature column" for k in wording if k not in names]
    notes += [f"feature '{n}' has no wording entry" for n in names if n not in wording]
    for m in meta:
        w = wording.get(m["name"], {})
        if m["type"] == "choice":
            missing = [o["value"] for o in m["options"] if o["value"] not in w.get("options", {})]
            if missing:
                notes.append(f"'{m['name']}': options without a label: {missing}")
    return notes


def fit_eval(model, Xtr, ytr, Xva, yva, n):
    model.fit(Xtr, ytr)
    return evaluate(model, Xva, yva, n)


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, type=Path, help="the downloaded dataset (see docs/WELLBEING_MODEL.md)")
    ap.add_argument("--weights-out", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--metrics-out", type=Path, default=DEFAULT_METRICS)
    ap.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    ap.add_argument("--dataset-name", default="University Student Stress Dataset (Mendeley Data, DOI 10.17632/rc5htd5dfr.1, CC BY 4.0)")
    ap.add_argument("--keep-all-questions", action="store_true", help="do not drop questions that carry no information")
    ap.add_argument("--inspect", action="store_true", help="only print a profile of the CSV columns, then stop")
    ap.add_argument("--standin", action="store_true", help="mark the output as SYNTHETIC stand-in data (pipeline tests only)")
    args = ap.parse_args()

    df = load_data(args.csv)
    if args.inspect:
        inspect_csv(df)
        return
    features = [c for c in MODIFIABLE if c in df.columns]
    missing = [c for c in MODIFIABLE if c not in df.columns]
    if missing:
        print(f"WARNING: these expected columns are not in the CSV and are skipped: {missing}")
    if len(features) < 3:
        sys.exit("Too few usable feature columns found.")
    df = df.dropna(subset=features + [TARGET]).drop_duplicates().reset_index(drop=True)
    checks = data_checks(df, features)
    print("DATA CHECKS:", json.dumps(checks))

    meta = describe_features(df, features, args.questions)
    wording_notes = check_wording(meta, args.questions)
    for note in wording_notes:
        print("QUESTIONNAIRE CHECK:", note)
    y_idx = df[TARGET].map({lab: i for i, lab in enumerate(LABEL_ORDER)}).to_numpy()
    n_classes = len(LABEL_ORDER)

    # ---- step 3b: drop questions that carry no information about the label (ablation on validation data) ----
    # Dataset forensics use ALL candidate questions, before anything is dropped.
    forensics = dataset_forensics(df, encode(df, meta)[0], features)
    screening = screen_features(df, meta, y_idx)
    for n, v in screening.items():
        print(f"SCREENING {n:20s} validation log-loss increase when removed: {v['validation_logloss_increase_when_removed']}")
    no_signal = [n for n, v in screening.items() if v["validation_logloss_increase_when_removed"] < SCREEN_MIN_GAIN]
    if no_signal and not args.keep_all_questions and len(features) - len(no_signal) >= 3:
        print("DROPPED (no information about the label in this dataset):", no_signal)
        features = [f for f in features if f not in no_signal]
        meta = describe_features(df, features, args.questions)
        wording_notes = check_wording(meta, args.questions)
    else:
        no_signal = []
    X_all, columns = encode(df, meta)
    print("DATASET FORENSICS:", json.dumps({k: v for k, v in forensics.items() if k != "interpretation"})[:900])

    # ---- step 4: split 60 / 20 / 20 (stratified; fixed seed = reproducible) ----
    X_trva, X_te, y_trva, y_te = train_test_split(X_all, y_idx, test_size=0.20, random_state=SEED, stratify=y_idx)
    X_tr, X_va, y_tr, y_va = train_test_split(X_trva, y_trva, test_size=0.25, random_state=SEED, stratify=y_trva)
    split = {"train": int(len(y_tr)), "validation": int(len(y_va)), "test": int(len(y_te))}

    # ---- steps 5-6: candidate models, compared on the VALIDATION set only ----
    # make_pipeline(StandardScaler(), model) fits the scaler on whatever data the model is fitted on
    # (here: train only) and re-uses it for the validation rows - no leakage.
    candidates = {"majority_class_baseline": make_pipeline(StandardScaler(), DummyClassifier(strategy="most_frequent")),
                  "decision_tree_depth3": make_pipeline(StandardScaler(), DecisionTreeClassifier(max_depth=3, random_state=SEED)),
                  "random_forest": make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1)),
                  "gradient_boosting_reference": make_pipeline(StandardScaler(), GradientBoostingClassifier(random_state=SEED))}
    for C in (0.01, 0.1, 1.0, 10.0):
        candidates[f"logistic_regression_C={C}"] = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000))
    validation = {name: fit_eval(m, X_tr, y_tr, X_va, y_va, n_classes) for name, m in candidates.items()}
    lr_names = [k for k in validation if k.startswith("logistic_regression")]
    # Prefer the simplest (most regularised) model whose validation macro-F1 is within 0.005 of the best one.
    top_f1 = max(validation[k]["macro_f1"] for k in lr_names)
    best_lr = min((k for k in lr_names if validation[k]["macro_f1"] >= top_f1 - 0.005), key=lambda k: float(k.split("=")[1]))
    best_C = float(best_lr.split("=")[1])
    print("VALIDATION macro-F1:", {k: v["macro_f1"] for k, v in validation.items()}, "-> chosen:", best_lr)

    # ---- step 7: final model = chosen logistic regression, refitted on train + validation ----
    scaler = StandardScaler().fit(X_trva)
    final = LogisticRegression(C=best_C, max_iter=2000).fit(scaler.transform(X_trva), y_trva)

    class _Wrap:  # lets evaluate() call predict_proba on raw (unscaled) rows
        def predict_proba(self, X):
            return final.predict_proba(scaler.transform(X))
    test_metrics = evaluate(_Wrap(), X_te, y_te, n_classes)          # the ONE look at the test set
    cv = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(C=best_C, max_iter=2000)), X_trva, y_trva,
                         cv=StratifiedKFold(5, shuffle=True, random_state=SEED), scoring="f1_macro")
    test_proba = _Wrap().predict_proba(X_te)
    calib = calibration(test_proba, y_te, n_classes)
    ci = bootstrap_ci(y_te, test_proba)
    print("CALIBRATION: ECE =", calib["expected_calibration_error"], " Brier =", calib["brier_score_multiclass"], " CI:", ci)
    print("TEST:", json.dumps({k: test_metrics[k] for k in ("accuracy", "macro_f1", "log_loss", "roc_auc_ovr")}))

    # Same test set for the other models (refitted on train+validation too) so the comparison is fair.
    test_compare = {}
    for name in ("majority_class_baseline", "decision_tree_depth3", "random_forest", "gradient_boosting_reference"):
        test_compare[name] = fit_eval(candidates[name], X_trva, y_trva, X_te, y_te, n_classes)
        test_compare[name] = {k: test_compare[name][k] for k in ("accuracy", "macro_f1", "log_loss", "roc_auc_ovr")}
    test_compare["logistic_regression_shipped"] = {k: test_metrics[k] for k in ("accuracy", "macro_f1", "log_loss", "roc_auc_ovr")}

    # ---- step 8: honesty checks ----
    checks_extra = {}
    if LEAKY in df.columns and pd.api.types.is_numeric_dtype(df[LEAKY]):
        Xl = X_all.assign(**{LEAKY: df[LEAKY].astype(float)})
        a, b, c, d = train_test_split(Xl, y_idx, test_size=0.2, random_state=SEED, stratify=y_idx)
        m = make_pipeline(StandardScaler(), DecisionTreeClassifier(max_depth=4, random_state=SEED)).fit(a, c)
        checks_extra["with_stress_score_column_accuracy"] = round(float(accuracy_score(d, m.predict(b))), 4)
        checks_extra["with_stress_score_note"] = ("If this accuracy is close to 1.0, the label was computed from that score, "
                                                  "so Stress_Score must NOT be a feature (it would just hand the model the answer).")
    demo_cols = [c for c in DEMOGRAPHIC if c in df.columns]
    if demo_cols:
        extra = pd.get_dummies(df[demo_cols], dtype=float)
        Xd = pd.concat([X_all, extra], axis=1)
        a, b, c, d = train_test_split(Xd, y_idx, test_size=0.2, random_state=SEED, stratify=y_idx)
        m = make_pipeline(StandardScaler(), LogisticRegression(C=best_C, max_iter=2000)).fit(a, c)
        a2, b2, c2, d2 = train_test_split(X_all, y_idx, test_size=0.2, random_state=SEED, stratify=y_idx)
        m2 = make_pipeline(StandardScaler(), LogisticRegression(C=best_C, max_iter=2000)).fit(a2, c2)
        checks_extra["with_demographics_macro_f1"] = round(float(f1_score(d, m.predict(b), average="macro")), 4)
        checks_extra["without_demographics_macro_f1"] = round(float(f1_score(d2, m2.predict(b2), average="macro")), 4)
        checks_extra["demographics_note"] = "If these two numbers are close, the demographic columns add little, which supports leaving them out."

    structure = score_structure(df, X_all, features)
    if structure:
        print("SCORE STRUCTURE:", json.dumps({k: v for k, v in structure.items() if k != "note"}))

    # ---- step 9: export ----
    classes = final.classes_.tolist()                  # [0, 1, 2] -> Low, Medium, High
    assert classes == list(range(n_classes))
    trained_on = f"{args.dataset_name}; n={checks['rows']} rows after cleaning; seed={SEED}"
    if args.standin:
        trained_on = "SYNTHETIC STAND-IN DATA - NOT REAL - for pipeline tests only; " + trained_on
    top_test = {k: test_metrics[k] for k in ("accuracy", "macro_f1", "log_loss", "roc_auc_ovr")}
    weights = {
        "version": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "kind": "multinomial_logistic_regression",
        "trained_on": trained_on,
        "labels": LABEL_ORDER,
        "features": meta,
        "columns": columns,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coef": final.coef_.tolist(),
        "intercept": final.intercept_.tolist(),
        "metrics": {"held_out_test_set": top_test, "per_class": test_metrics["per_class"],
                    "confusion_matrix_rows_true_cols_pred": test_metrics["confusion_matrix_rows_true_cols_pred"],
                    "cross_validation_macro_f1_mean": round(float(cv.mean()), 4),
                    "cross_validation_macro_f1_std": round(float(cv.std()), 4),
                    "calibration": {"expected_calibration_error": calib["expected_calibration_error"],
                                    "brier_score_multiclass": calib["brier_score_multiclass"]},
                    "bootstrap_95_ci": ci,
                    "split": split, "majority_baseline_accuracy": test_compare["majority_class_baseline"]["accuracy"]},
        "card": {
            "intended_use": "Shows which stress-load band a survey scoring rule would give to your answers, and which answers contribute most. A reflection aid for the student, not a prediction of burnout.",
            "probability_meaning": (
                f"Each percentage is how confident the model is that the dataset's own scoring rule would put answers like yours in "
                f"the Low, Medium or High band. On held-out rows the average gap between stated confidence and how often the model "
                f"was right (calibration error) was {calib['expected_calibration_error']:.3f} (0 would be perfect). "
                f"It is not the chance that you will burn out, and it was not checked against any real-world outcome."),
            "not_for": "Medical or psychological diagnosis, grading, or any decision about a person.",
            "limitations": [
                "Trained on one dataset described as a survey of undergraduates at universities in Bangladesh; results may not transfer to other countries or courses.",
                "The dataset's stress label is a score the authors computed from the answers. The model learns that scoring rule, not clinically measured stress.",
                *([forensics["interpretation"]] if forensics.get("suspected_generated_data") else []),
                *([f"Questions dropped because they carry no information in this dataset: {', '.join(no_signal)}."] if no_signal else []),
                "Answers are self-reported and the data is a snapshot, so the model shows association, not cause.",
                "Probabilities are model estimates and can be wrong for any individual student.",
            ],
        },
    }
    args.weights_out.write_text(json.dumps(weights), encoding="utf-8")
    report = {
        "dataset": trained_on, "data_checks": checks, "features_used": features, "features_left_out": [c for c in df.columns if c not in features + [TARGET]],
        "split_rows": split, "validation_set_results": {k: {m: v[m] for m in ("accuracy", "macro_f1", "log_loss")} for k, v in validation.items()},
        "chosen_by_validation": best_lr, "test_set_results_all_models": test_compare, "shipped_model_test_details": test_metrics,
        "cross_validation_macro_f1": {"mean": round(float(cv.mean()), 4), "std": round(float(cv.std()), 4), "folds": 5},
        "honesty_checks": checks_extra, "feature_screening_validation": screening, "questions_dropped_no_signal": no_signal,
        "dataset_forensics": forensics,
        "score_structure": structure, "calibration_test_set": calib, "bootstrap_95_ci_test_set": ci,
        "questionnaire_wording_warnings": wording_notes,
        "coefficients_high_vs_low": {c: round(float(h - l), 4) for c, h, l in zip(columns, final.coef_[2], final.coef_[0])},
    }
    args.metrics_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"honesty_checks": checks_extra, "test": top_test}, indent=2))
    print(f"\nWrote {args.weights_out} and {args.metrics_out}")


if __name__ == "__main__":
    main()
