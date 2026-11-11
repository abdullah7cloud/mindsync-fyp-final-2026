"""
The language-model layer. A model is used ONLY for language work (understanding free text, explaining a plan, answering a
question, wording the weekly review). It never schedules, never calculates and never changes stored data. Everything it
returns is validated here before anyone sees it, and every feature has a rule-based fallback in app/assist/localai.py.
"""
