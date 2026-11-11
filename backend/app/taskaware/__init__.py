"""
Task-aware planning engine (update 19).

Pipeline: classify -> difficulty (intrinsic and for this student) -> workload range and stages ->
history calibration -> constraint-based schedule -> explanations. When too little is known the engine
returns up to three follow-up questions instead of a plan.

Everything here is deterministic Python with no network access, no external AI and no randomness: the
same input always gives the same output (tested). See docs/TASK_AWARE_ENGINE.md.
"""
