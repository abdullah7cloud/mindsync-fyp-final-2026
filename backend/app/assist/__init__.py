"""
MindSync "assist" package: everything behind the connected Smart Planner.

  settings_schema  - validated study settings and profile (what the student can change)
  profile          - turns a task's words into a profile (kind, difficulty, workload range, steps)
  scheduler        - the deterministic multi-task scheduler (EDF feasibility + pacing + alternatives)
  replan           - decides when a stored plan is out of date and what to propose
  summary          - dashboard numbers computed from real records only
  dates            - small natural-language date reader (used by the local fallback)
  localai          - rule-based fallbacks for every language-model feature
  routes           - the HTTP API (logged-in users) and the stateless guest twin

The language model (app/ai) only does language work. All numbers and all scheduling come from this package.
"""
