"""Pydantic models used to validate user input."""
from pydantic import BaseModel, ConfigDict, Field, field_validator

INTENSITIES = ("low", "medium", "high")


def _check_intensity(v: str) -> str:
    v = v.strip().lower()
    if v not in INTENSITIES:
        raise ValueError("must be one of: low, medium, high")
    return v


class WorkoutRequest(BaseModel):
    """Body for POST /generate-workout/gemini."""

    model_config = ConfigDict(str_strip_whitespace=True)

    goal: str = Field(..., min_length=2, max_length=100, examples=["muscle gain"])
    intensity: str = Field(..., examples=["medium"])

    _v_intensity = field_validator("intensity")(_check_intensity)


class NutritionRequest(BaseModel):
    """Body for POST /generate-nutrition-tip."""

    model_config = ConfigDict(str_strip_whitespace=True)

    goal: str = Field(..., min_length=2, max_length=100, examples=["weight loss"])


class UserInput(BaseModel):
    """Full profile used to generate and store a plan."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(..., min_length=1, max_length=100)
    user_id: int = Field(..., gt=0)
    age: int = Field(..., ge=10, le=100)
    weight: float = Field(..., gt=20, le=400, description="kg")
    goal: str = Field(..., min_length=2, max_length=100)
    intensity: str

    _v_intensity = field_validator("intensity")(_check_intensity)


class FeedbackRequest(BaseModel):
    """Feedback used to refine an existing plan."""

    model_config = ConfigDict(str_strip_whitespace=True)

    feedback: str = Field(..., min_length=3, max_length=1000, examples=["more focus on cardio"])
