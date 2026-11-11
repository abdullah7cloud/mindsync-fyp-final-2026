"""
Synthetic training data generator for the MindSync task-fit model.

IMPORTANT (be upfront about this in the report): there is no real dataset of
student study sessions available for this project, so the data here is
SIMULATED. Each row is one imaginary "study attempt": a task with a
difficulty and a deadline, a student with an energy level, and an outcome
label saying whether the student completed a productive focused session
(1) or not (0).

The outcome is generated from documented, research-motivated assumptions:

  1. Tasks harder than the student's energy are much less likely to go well
     (cognitive load vs. fatigue).
  2. Tasks far easier than the student's energy go slightly worse too
     (boredom / low engagement) - a much smaller effect.
  3. A close deadline adds a little "pressure to perform" but an already
     overdue task adds stress, lowering success a bit.
  4. Every student has their own random resilience, plus random noise on
     each attempt, so the labels are not perfectly predictable.

Because the labels come from these assumptions, the trained model learns
THESE assumptions, not real-world truth. The honest value of the model is
(a) a complete, reproducible ML pipeline (data -> train -> evaluate ->
deploy) and (b) a mechanism that can be retrained on REAL completion data
collected by the app later. This limitation must appear in Chapter 4/5.
"""
import math
import random

from app.ml.features import build_features


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def true_success_probability(difficulty: int, energy: int, hours_left: float, resilience: float) -> float:
    gap = difficulty - energy
    z = 1.2 + resilience
    z -= 0.95 * max(0, gap)          # harder than energy: strong penalty
    z -= 0.25 * max(0, -gap)         # easier than energy: mild penalty
    if hours_left < 0:
        z -= 0.5                     # overdue stress
    elif hours_left < 48:
        z += 0.3                     # mild deadline-driven focus
    return _sigmoid(z)


def generate(n: int = 20000, seed: int = 42):
    """Returns (X, y) as plain Python lists."""
    rng = random.Random(seed)
    X, y = [], []
    n_students = max(50, n // 200)
    resilience = [rng.gauss(0.0, 0.5) for _ in range(n_students)]
    for _ in range(n):
        student = rng.randrange(n_students)
        difficulty = rng.randint(1, 5)
        energy = rng.randint(1, 5)
        # deadlines from 3 days overdue to ~3 weeks away
        hours_left = rng.uniform(-72.0, 24.0 * 21)
        p = true_success_probability(difficulty, energy, hours_left, resilience[student])
        label = 1 if rng.random() < p else 0
        X.append(build_features(difficulty, energy, hours_left))
        y.append(label)
    return X, y
