"""
Feature engineering for the trained "task fit" model.

This file is shared by BOTH the offline training script
(ml_training/train.py) and the live API (app/ml/predictor.py), so the model
always sees exactly the same features at training time and at prediction
time (a classic source of silent bugs when they are written twice).

Pure Python - no numpy - so the running web app needs no extra packages.
"""
import math
from datetime import datetime

FEATURE_NAMES = [
    "difficulty",       # 1..5, set by the student when creating the task
    "energy",           # 1..5, latest energy check-in
    "gap",              # difficulty - energy  (positive = task harder than energy)
    "abs_gap",          # |difficulty - energy|
    "log_hours_left",   # log1p(hours until deadline), clipped to [0, 30 days]
    "overdue",          # 1.0 if the deadline has already passed
]

_MAX_HOURS = 24.0 * 30.0


def hours_until(deadline: datetime, now: datetime) -> float:
    return (deadline - now).total_seconds() / 3600.0


def build_features(difficulty: int, energy: int, hours_left: float) -> list[float]:
    # Why these features? A task is a good fit when its difficulty matches the student's energy
    # (gap), and urgency matters on a log scale: the difference between 1 h and 10 h left is big,
    # between 300 h and 310 h it is not. Overdue is a separate flag because it feels different.
    overdue = 1.0 if hours_left < 0 else 0.0
    clipped = min(max(hours_left, 0.0), _MAX_HOURS)
    gap = float(difficulty - energy)
    return [
        float(difficulty),
        float(energy),
        gap,
        abs(gap),
        math.log1p(clipped),
        overdue,
    ]
