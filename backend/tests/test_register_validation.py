"""Sign-up validation gives specific, human-readable reasons."""
import pytest
from pydantic import ValidationError

from app.schemas import UserRegister


def _msgs(**kw):
    base = dict(email="a@example.com", password="Study-pass-1", display_name="Abi")
    base.update(kw)
    with pytest.raises(ValidationError) as e:
        UserRegister(**base)
    return " | ".join(err["msg"] for err in e.value.errors())


def test_valid_registration_passes_and_trims_name():
    assert UserRegister(email="a@example.com", password="Study-pass-1", display_name="  Abi ").display_name == "Abi"


def test_password_needs_a_letter_and_a_number():
    assert "letter and one number" in _msgs(password="onlyletters")
    assert "letter and one number" in _msgs(password="12345678")


def test_short_password_and_bad_email_and_blank_name_are_rejected():
    assert "at least 8" in _msgs(password="a1")
    assert "email" in _msgs(email="not-an-email").lower()
    assert "blank" in _msgs(display_name="   ").lower()
