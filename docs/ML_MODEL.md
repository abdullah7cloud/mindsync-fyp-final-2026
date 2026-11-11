# Task-fit model (EXPERIMENTAL, trained on simulated data, OFF by default)

> There are two trained models in MindSync. This one adjusts the task ranking. The other one (stress-risk, trained on real survey data) is described in `WELLBEING_MODEL.md`.

## Purpose
Predicts the probability (0-1) that a task is a good fit for the student right now (a productive, completed focus session).

## Where it sits in the system
```
tasks + latest energy check-in
        |--> formula score (0.6 x deadline urgency + 0.4 x energy match)
        |--> task-fit model probability
        v
final score = formula                                (default, ML_ENABLED=false)
final score = 0.7 x formula + 0.3 x model          (only if ML_ENABLED=true; ML_WEIGHT in .env)
        v
ranked tasks -> explanation sentences built by local code (app/explain.py)
```
* Burnout Mode is applied before scoring; the model never overrides it.
* **Default: the formula alone is used.** The model is switched off because it was trained on simulated data, so it cannot honestly claim to know what is good for a real student. A transparent rule is easier to defend than a number that only reflects our own assumptions. It stays in the project to show the full ML pipeline (split, validation, cross-validation, export, tests); `GET /models/status` marks it `used_in_ranking: false`.
* No public dataset of student task/energy/outcome records was found. If real feedback accumulates (`recommendation_feedback` table), it could be used to train a model on real labels later.

## Model
* Features (`app/ml/features.py`): difficulty, energy, gap (difficulty - energy), |gap|, log(hours to deadline), overdue flag.
* Candidates compared on a **validation set** (`ml_training/train.py`): logistic regression (C = 0.01, 0.1, 1, 10), small neural network (4, 8, 16 hidden units), gradient boosting (reference only, not exportable).
* The shipped model is chosen **on validation ROC-AUC**, refitted on train + validation, and scored **once** on the untouched test set.
* Weights are exported to `app/ml/model_weights.json` with an `evaluation` block; the web app evaluates them in plain Python (no scikit-learn at run time).

## Training data - important limitation
There is no public dataset of student study sessions, so the data is **simulated**: 20,000 rows made by `ml_training/synth_data.py` from stated assumptions (hard tasks at low energy fail more, slight boredom penalty, overdue stress, per-student resilience, noise).
1. The model learns the simulation's assumptions, not proven real behaviour.
2. The scores show the training pipeline works; they are **not** real-world accuracy.
3. The app labels this model as a prototype in "How the models work".

## Results (split 60 / 20 / 20 = 12,000 / 4,000 / 4,000 rows, seed 42; `ml_training/metrics.json`)
| Model | Validation ROC-AUC | Test ROC-AUC | Test accuracy | Test Brier (lower is better) |
|---|---|---|---|---|
| Logistic regression, C = 0.1 (shipped) | 0.7288 | 0.7225 | 0.686 | 0.205 |
| Gradient boosting (reference) | 0.7253 | 0.7162 | 0.686 | 0.206 |
| Formula used as a predictor | - | 0.5808 | 0.474 | 0.300 |

5-fold cross-validation ROC-AUC of the shipped model: 0.7246 (std 0.0092).
The formula is built to prioritise by deadline, not to predict success, so the last row is context, not a fair contest. All three learned models score about the same, which is expected for six features and noisy labels; logistic regression is shipped because it is the simplest to explain.

## Re-train
```
cd backend
pip install -r requirements-train.txt
python -m ml_training.train
```
