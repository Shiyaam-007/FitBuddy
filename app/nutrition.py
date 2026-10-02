"""Nutrition-specific helpers (offline fallback tips used when Gemini Flash is unavailable)."""

FALLBACK_TIPS = {
    "weight_loss": (
        "Fill half your plate with vegetables and include a lean protein at every meal "
        "to stay full while keeping calories in check. Drink water before meals."
    ),
    "muscle_gain": (
        "Include protein (chicken, eggs, fish, beans or Greek yogurt) in your post-workout "
        "meal, along with some carbs to refuel your muscles."
    ),
    "flexibility": (
        "Stay well hydrated and include magnesium-rich foods like nuts, seeds and leafy greens "
        "to support muscle recovery and relaxation."
    ),
    "general": (
        "Prioritise protein in every meal, eat plenty of whole foods, drink water through the "
        "day and get 7-9 hours of sleep for recovery."
    ),
}


def classify_goal(goal: str) -> str:
    g = (goal or "").lower()
    if any(k in g for k in ("loss", "lose", "fat", "slim", "cut")):
        return "weight_loss"
    if any(k in g for k in ("muscle", "gain", "bulk", "strength")):
        return "muscle_gain"
    if any(k in g for k in ("flex", "mobility", "yoga", "stretch")):
        return "flexibility"
    return "general"


def get_fallback_tip(goal: str) -> str:
    return FALLBACK_TIPS[classify_goal(goal)]
