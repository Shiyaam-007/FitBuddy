"""Feedback-based plan updater (Gemini Pro)."""
from .gemini_generator import PRO_MODELS, generate_text


def update_workout_plan(original_plan: str, user_feedback: str) -> str:
    """Use Gemini Pro to update the workout plan based on user feedback."""
    prompt = f"""
You are a professional fitness trainer assistant.

Here's the original 7-day workout plan:
{original_plan}

User Feedback:
"{user_feedback}"

Based on the feedback, revise the relevant parts of the workout plan. Keep the format and rest of the plan unchanged if not needed. Return the complete updated 7-day plan (Day 1 to Day 7), not just the changes.
"""
    return generate_text(PRO_MODELS, prompt)
