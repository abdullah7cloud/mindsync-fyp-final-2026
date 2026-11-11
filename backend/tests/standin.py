"""
Synthetic STAND-IN survey data used ONLY by the automated tests (and for pipeline development).

It copies the shape of the real survey file (column names; a mix of number and text columns; a
Stress_Score column and a Stress_Level label derived from it) so the training script, the exported
JSON and the inference code can be tested without the real dataset. It must NEVER be used to
produce the model shipped with the app.
"""
import numpy as np
import pandas as pd


def make_standin_csv(path, n: int = 900, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    sleep = rng.uniform(4, 9, n).round(1)
    study = rng.uniform(1, 9, n).round(1)
    screen = rng.uniform(1, 9, n).round(1)
    social = rng.uniform(0, 6, n).round(1)
    exercise = rng.integers(0, 6, n)
    attendance = rng.integers(50, 101, n)
    exams = rng.integers(1, 6, n)
    anxiety = rng.integers(1, 11, n)
    load = rng.choice(["Low", "Medium", "High"], n)
    peer = rng.choice(["Low", "Medium", "High"], n)
    family = rng.choice(["Low", "Medium", "High"], n)
    to_num = {"Low": 0, "Medium": 1, "High": 2}
    score = (
        -1.2 * (sleep - 6.5) + 0.5 * (study - 5) + 0.3 * (screen - 5) + 0.2 * social - 0.3 * exercise
        - 0.02 * (attendance - 80) + 0.4 * exams + 0.5 * anxiety
        + 1.0 * np.vectorize(to_num.get)(load) + 0.6 * np.vectorize(to_num.get)(peer) - 0.6 * np.vectorize(to_num.get)(family)
        + rng.normal(0, 1.5, n)
    )
    cuts = np.quantile(score, [0.4, 0.75])
    level = np.where(score < cuts[0], "Low", np.where(score < cuts[1], "Medium", "High"))
    pd.DataFrame({
        "Age": rng.integers(19, 25, n), "Gender": rng.choice(["Male", "Female"], n),
        "University_Type": rng.choice(["Public", "Private", "National"], n),
        "Study_Hours": study, "Class_Attendance": attendance, "Exam_Frequency": exams, "Assignment_Load": load,
        "Tuition": rng.choice(["Yes", "No"], n), "Sleep_Hours": sleep, "Social_Media_Use": social, "Screen_Time": screen,
        "Physical_Exercise": exercise, "Family_Income_Level": rng.choice(["Low", "Medium", "High"], n),
        "Peer_Pressure": peer, "Family_Support": family, "Anxiety_Level": anxiety,
        "Stress_Score": score.round(2), "Stress_Level": level,
    }).to_csv(path, index=False)
