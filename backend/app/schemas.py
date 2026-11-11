"""
Pydantic schemas: the application-level validation layer.

This is the first line of defence mentioned in the project contract's risk
analysis ("strict validation of schemas (Pydantic/Zod)") — every request
body is parsed and type/range-checked here before it ever reaches the
database or, for recommendation text, before anything is handed to the LLM.
"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator


# ---------- Auth ----------

def _check_password_strength(v: str) -> str:
    """The one password rule used by sign-up, password reset and password change."""
    if not any(ch.isalpha() for ch in v) or not any(ch.isdigit() for ch in v):
        raise ValueError("Password must contain at least one letter and one number")
    return v


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return _check_password_strength(v)

    @field_validator("display_name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


class ChangeEmail(BaseModel):
    new_email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Message(BaseModel):
    message: str
    # "email" = a real mail server is configured; "demo" = no mail server, the message was saved to backend/outbox.
    # This describes the SERVER, never a particular account, so it does not reveal whether an address is registered.
    delivery: Optional[Literal["email", "demo"]] = None


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    display_name: str
    email_alerts: bool = True


# ---------- Tasks ----------

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="general", max_length=100)
    difficulty: int = Field(ge=1, le=5, default=3)
    deadline: datetime


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=100)
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    deadline: Optional[datetime] = None
    status: Optional[Literal["pending", "completed"]] = None

    @model_validator(mode="after")
    def _no_explicit_nulls(self):
        # Every field here is optional ("leave unchanged" = omit it), but none
        # of them may be set to null: the database columns are NOT NULL, so an
        # explicit null would otherwise reach the DB and cause a 500 error.
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str
    category: str
    difficulty: int
    deadline: datetime
    status: Literal["pending", "completed"]
    created_at: datetime
    completed_at: Optional[datetime] = None


# ---------- Energy check-ins ----------

class EnergyCheckinCreate(BaseModel):
    energy_level: int = Field(ge=1, le=5)


class EnergyCheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    energy_level: int
    created_at: datetime


# ---------- Recommendation ----------

class RecommendedTask(BaseModel):
    task: TaskOut
    score: float
    score_breakdown: dict[str, float | str]


class RecommendationOut(BaseModel):
    """
    The response returned by GET /recommend.

    Everything here is produced by LOCAL code: the heuristic ranks the tasks
    (app/heuristic.py), the trained task-fit model adds a probability
    (app/ml), and app/explain.py turns the numbers into a sentence. No
    external AI service is involved.
    """
    ranked_tasks: list[RecommendedTask]
    top_task: Optional[RecommendedTask]
    explanation: str
    explanation_source: Literal["local_rules", "no_tasks"]
    burnout_mode: bool
    # Why Burnout Mode is on: a low energy check-in, or a High result in the wellbeing check.
    burnout_reason: Optional[Literal["low_energy", "high_stress_risk"]] = None
    # Which trained model (if any) contributed to the ranking, e.g.
    # "logistic_regression"; None when the plain heuristic was used.
    ml_model: Optional[str] = None


# ---------- Feedback and account ----------

class FeedbackCreate(BaseModel):
    """Situation numbers only (no task text) plus the student's yes/no answer."""
    helpful: bool
    energy_level: int = Field(ge=1, le=5)
    difficulty: int = Field(ge=1, le=5)
    hours_left: float = Field(ge=-8760, le=8760)   # negative = overdue; +/- one year is plenty
    burnout_mode: bool = False


class FeedbackSummary(BaseModel):
    total: int
    helpful: int
    helpful_percent: Optional[float] = None


class DeleteAccount(BaseModel):
    """Deleting an account needs the password again, so a stolen token cannot erase everything."""
    password: str = Field(min_length=1, max_length=128)
