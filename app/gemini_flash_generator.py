"""Gemini Flash - fast nutrition / recovery tips."""
import logging

from .gemini_generator import FLASH_MODELS, GeminiError, generate_text
from .nutrition import get_fallback_tip

logger = logging.getLogger("fitbuddy.gemini")


def generate_nutrition_tip_with_flash(goal: str) -> str:
    """Generate a nutrition or recovery tip using Gemini Flash based on the user's fitness goal.

    Args:
        goal: e.g. "weight loss", "muscle gain", "general fitness".
    Returns:
        A short tip. If Gemini is unavailable, a built-in fallback tip is returned so the
        page still works (the tip is a bonus, the plan is the main result).
    """
    prompt = (
        f"Give one clear, helpful nutrition or recovery tip for someone focused on '{goal}'. "
        "The tip should be practical, friendly, and easy to understand. "
        "Keep it to 2-3 sentences, plain text, no markdown."
    )
    try:
        return generate_text(FLASH_MODELS, prompt)
    except GeminiError as exc:
        logger.warning("Using fallback nutrition tip: %s", exc)
        return get_fallback_tip(goal)
