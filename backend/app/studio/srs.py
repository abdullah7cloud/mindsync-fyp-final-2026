"""
Spaced repetition, deterministic and AI-free (a simple Leitner box system, easy to explain):

  box 0  new card, due today
  box 1  see again in 1 day      box 2  in 3 days     box 3  in 7 days     box 4  in 14 days     box 5  in 30 days

  Easy      -> up two boxes        Okay -> up one box        Difficult -> back to box 1 (see it again tomorrow)

A card in box 4 or 5 counts as "well known". This measures how the student rated their own recall; it is not a test of mastery.
"""
from datetime import date, timedelta

INTERVAL_DAYS = {0: 0, 1: 1, 2: 3, 3: 7, 4: 14, 5: 30}
RATINGS = ("easy", "okay", "difficult")
WELL_KNOWN_BOX = 4


def next_state(box: int, rating: str, today: date) -> tuple:
    """(new box, next due date, lapsed?)"""
    if rating not in RATINGS:
        raise ValueError("rating")
    new = 1 if rating == "difficult" else min(5, box + (2 if rating == "easy" else 1))
    return new, today + timedelta(days=INTERVAL_DAYS[new]), rating == "difficult" and box >= 2
