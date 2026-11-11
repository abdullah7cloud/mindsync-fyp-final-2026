# Wellbeing (stress-level) model

**Status (21 Oct 2026): trained on the real dataset file, integrated and tested.** Every number below comes from `backend/ml_training/wellbeing_metrics.json` (produced by `python -m ml_training.wellbeing_train`). Do not quote a number that is not in that file.

## What it is for
A student answers **8 questions** about habits (workload, sleep, social media, screen time, exercise, family support, anxiety). The model gives a **stress level (Low / Medium / High)**, the confidence for each level, and the answers that pushed the result up or down, each with a tip. A "High" result (valid for 14 days) turns on Burnout Mode and makes the study planner gentler. It is a reflection aid, **not a medical or psychological diagnosis and not a prediction of burnout**.

## The most important finding (say this in the viva before anyone asks)
The trainer tested what the dataset's label really is. Results:
1. **The stress score is an exact formula of the answers.** A plain linear regression rebuilds `Stress_Score` with R² = 1.0 and a largest error of about 1e-13. The recovered formula is
   `score = Exam_Frequency + Assignment_Load - Sleep_Hours + Social_Media_Use + Screen_Time - 2 (if you exercise) - Family_Support + Anxiety_Level`.
2. **Low / Medium / High are just cut-offs of that score** (Low <= 10, Medium 11-20, High >= 21; the score ranges of the classes do not overlap).
3. **Three of the dataset's questions have exactly zero effect on the score:** study hours, class attendance and peer pressure. Removing them does not change the validation log-loss at all (changes of -0.0004, -0.0010 and -0.0005), while removing any of the other 8 makes it worse by 0.08 to 0.39. MindSync therefore **does not ask them** (the trainer drops such questions automatically; `--keep-all-questions` switches this off).
4. **The data looks computer-generated.** All 10 whole-number columns pass a "flat distribution" test (p between 0.155 and 0.862), and the largest correlation between any two input columns is 0.041. Real questionnaires rarely look like that (screen time and social media, or anxiety and sleep, normally move together). The file cannot prove how it was made; the honest wording is "consistent with synthetic or randomly generated data; ask the authors". The dataset README says the responses were collected from undergraduates at public, private and national universities in Bangladesh.
5. The notebook shipped with the dataset (`stress_score_generation.ipynb`) shows a *different* "example" formula that does **not** reproduce the data (correlation 0.79). Use the recovered formula above, not the notebook.

**What this means for the claims.** The near-perfect test score proves the model can recover the dataset's scoring rule. It does **not** prove that the model predicts real students' stress or burnout, because the label was never measured independently. Tree and boosting models (nonlinear) score much lower on the same data (macro-F1 0.81) because the rule is linear; that is the expected signature of a linear label.

## What the percentage means
"How confident the model is that the dataset's own scoring rule would put answers like yours in this band." Calibration on the untouched test set: expected calibration error **0.073**, Brier score **0.038**. The model is slightly **under-confident** (for example, predictions made with about 70% confidence were right 100% of the time), so the percentages are cautious. It is **not** the chance that you will burn out, and it was not checked against any real-world outcome.

## Dataset
University Student Stress Dataset, Mendeley Data, DOI 10.17632/rc5htd5dfr.1, licence **CC BY 4.0** (reuse allowed with attribution; cite it in the report). Local copy: `backend/data/university_student_stress_dataset.csv` (3,000 rows, 18 columns, no missing values, no duplicates; the original download stays in your Desktop folder). Documentation copied to `backend/data/source_docs/` (README, variable table, the authors' code). Note the variable table says `Physical_Exercise` is "days per week" but the file contains **Yes/No**, so MindSync asks "Do you exercise regularly?".

## Questionnaire versus the training features (checked)
| Question in MindSync | Training column | Used? |
|---|---|---|
| Exams (1-10) | Exam_Frequency | yes |
| Assignment workload (1-10) | Assignment_Load | yes |
| Sleep hours | Sleep_Hours | yes |
| Social media hours | Social_Media_Use | yes |
| Screen hours | Screen_Time | yes |
| Exercise regularly (Yes/No) | Physical_Exercise | yes |
| Family support (1-10) | Family_Support | yes |
| Anxiety (1-10) | Anxiety_Level | yes |
| (removed) study hours, class attendance, peer pressure | Study_Hours, Class_Attendance, Peer_Pressure | **no: zero effect on the label** |

The form is generated from the weights file, so what the student sees can never differ from what the model was trained on. Allowed ranges are the ranges seen in the data (for example exams 1-9), and the API rejects anything else.

## Training method (`ml_training/wellbeing_train.py`)
1. Load and clean (3,000 rows, nothing removed).
2. Candidate features: the 11 habit/workload columns. Demographics (age, gender, university type, tuition, family income) are never inputs.
3. **Question screening** on validation data (drop a question if removing it does not make validation log-loss worse by at least 0.01).
4. **Stratified split 60 / 20 / 20** (1,800 / 600 / 600), seed 42.
5. Scaler fitted on the training part only.
6. Candidates compared on the **validation** set: majority class, decision tree, random forest, gradient boosting, logistic regression with C = 0.01, 0.1, 1, 10. The simplest model within 0.005 of the best macro-F1 is chosen: **logistic regression, C = 1**.
7. Refit on train + validation; **test set used once**.
8. Honesty checks: `Stress_Score` as a feature gives accuracy 1.0 (leakage, so it is excluded); with and without demographics macro-F1 is identical (0.9936), so demographics add nothing; 5-fold cross-validation; calibration; bootstrap confidence intervals; the dataset checks above.
9. Export scaler, coefficients, questionnaire, metrics and limitations to `app/ml/wellbeing_weights.json`.

## Results (held-out test set, 600 students)
| Model | Accuracy | Macro-F1 | ROC-AUC (one-vs-rest) |
|---|---|---|---|
| Always guess the most common class | 0.4767 | 0.2152 | 0.5000 |
| Decision tree (depth 3) | 0.6333 | 0.4476 | 0.7866 |
| Random forest | 0.8517 | 0.8062 | 0.9652 |
| Gradient boosting | 0.8767 | 0.8137 | 0.9701 |
| **Logistic regression (shipped)** | **0.9967** | **0.9936** | **1.0000** |

Shipped model details: 95% bootstrap interval for accuracy 0.9917-1.0000 and macro-F1 0.9841-1.0000; 5-fold cross-validation macro-F1 0.9952 (std 0.0039); log-loss 0.0858.
Per class (precision / recall / F1, students): Low 1.000 / 1.000 / 1.000 (249); Medium 0.993 / 1.000 / 0.997 (286); High 1.000 / 0.969 / 0.984 (65). Confusion matrix (rows = true, columns = predicted: Low, Medium, High): [[249, 0, 0], [0, 286, 0], [0, 2, 63]]. The only 2 mistakes were High students rated Medium at the band edge.

## Inference in the app
`app/ml/wellbeing_model.py` loads the JSON and does standardise -> linear scores -> softmax in plain Python (microseconds, no scikit-learn). The explanation for each answer is `sum((coef_High - coef_Low) x standardised value)`; the top 3 up and top 3 down are shown.

## Re-train
```
cd backend
pip install -r requirements-train.txt
python -m ml_training.wellbeing_train --inspect --csv data/university_student_stress_dataset.csv   # look first
python -m ml_training.wellbeing_train --csv data/university_student_stress_dataset.csv
```
On Windows double-click `train-wellbeing.bat` (log in `_update_backup\logs\`). Then restart the backend.

## Limitations (shown in the app and to say in the viva)
* The label is a rule applied to the answers, so the model reproduces the rule rather than measuring stress.
* The dataset looks generated, not collected from real people (evidence above); it cannot support claims about real students.
* Population described as Bangladeshi undergraduates; never tested on DMU or Niels Brock students.
* Association only, no causation; probabilities can be wrong for any individual.
* Real validation would need students' own later outcomes (for example a validated stress questionnaire such as the PSS-10 completed alongside MindSync); the "Was this helpful?" feedback is a first step.

## Tests
`backend/tests/test_wellbeing.py` (25 tests) runs the real trainer on a **synthetic stand-in** CSV (`tests/standin.py`) to prove the pipeline. `backend/tests/test_wellbeing_real_model.py` (5 tests) checks the **shipped** model: 8 questions match the features; it agrees with the recovered scoring rule on at least 97% of 600 random answer sets; extreme answers give High / Low; probabilities sum to 1; the card does not over-claim. Stand-in weights are never shipped.
