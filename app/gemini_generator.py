"""Gemini Pro - personalised 7-day workout plan generator (plus shared Gemini client helpers).

Google retires/renames Gemini models often, so every role (pro / flash) has a *chain* of
models. The app tries them in order and automatically moves to the next one when a model is
not found (404), not allowed for your account (403) or out of quota (429).
"""
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("fitbuddy.gemini")


def _chain(env_name: str, defaults: list) -> list:
    """Model from .env (if set) goes first, then the built-in defaults, without duplicates."""
    chain = []
    for m in [os.getenv(env_name, "").strip(), *defaults]:
        m = m.replace("models/", "")
        if m and m not in chain:
            chain.append(m)
    return chain


# "Pro" role: best quality first. Ends with free-tier friendly models as a safety net.
PRO_MODELS = _chain(
    "GEMINI_PRO_MODEL",
    ["gemini-3.1-pro-preview", "gemini-pro-latest", "gemini-3-flash-preview", "gemini-flash-latest"],
)
# "Flash" role: fast + cheap first.
FLASH_MODELS = _chain(
    "GEMINI_FLASH_MODEL",
    ["gemini-3-flash-preview", "gemini-flash-latest", "gemini-3.5-flash", "gemini-2.5-flash"],
)

# Kept for backwards compatibility / display
PRO_MODEL = PRO_MODELS[0]
FLASH_MODEL = FLASH_MODELS[0]

# Errors that mean "try a different model"
_SKIP_MODEL = ("404", "NOT_FOUND", "403", "PERMISSION_DENIED", "429", "RESOURCE_EXHAUSTED")
# Errors that are worth retrying on the same model
_TRANSIENT = ("500", "503", "UNAVAILABLE", "INTERNAL", "DEADLINE")


class GeminiError(Exception):
    """Raised when a Gemini call fails or the API key is missing."""


_client = None
_working = {}  # remembers which model worked, so later calls skip dead models


def get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key or key.startswith("your_"):
            raise GeminiError(
                "Gemini API key not found. Create a .env file with GOOGLE_API_KEY=<your key>."
            )
        _client = genai.Client(api_key=key)
    return _client


def _call(client, model: str, prompt: str, retries: int = 3) -> str:
    last = None
    for attempt in range(retries):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            text = (response.text or "").strip()
            if not text:
                raise GeminiError("Gemini returned an empty response (it may have been blocked).")
            return text
        except GeminiError:
            raise
        except Exception as exc:
            last = exc
            msg = str(exc)
            if any(c in msg for c in _TRANSIENT) and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise
    raise last  # pragma: no cover


def generate_text(models, prompt: str) -> str:
    """Call Gemini using a model chain (a list, or a single model name)."""
    chain = [models] if isinstance(models, str) else list(models)
    key = tuple(chain)
    if key in _working and _working[key] in chain:  # try the last good model first
        chain.remove(_working[key])
        chain.insert(0, _working[key])

    client = get_client()
    errors = []
    for model in chain:
        try:
            text = _call(client, model, prompt)
            _working[key] = model
            logger.info("Gemini model used: %s", model)
            return text
        except GeminiError:
            raise
        except Exception as exc:
            msg = str(exc)
            errors.append(f"{model}: {msg[:160]}")
            logger.warning("Model %s failed: %s", model, msg[:200])
            if not any(c in msg for c in _SKIP_MODEL):
                break  # not a model-availability problem (e.g. bad key) - stop trying
    raise GeminiError(
        "Gemini request failed. Tried -> " + " | ".join(errors)
        + "  (Check your API key and set GEMINI_PRO_MODEL / GEMINI_FLASH_MODEL in .env "
        "to a model your account can use.)"
    )


def generate_workout_gemini(user_input: dict) -> str:
    """Generate a structured 7-day workout plan with Gemini Pro.

    user_input keys: goal, intensity (required); age, weight (optional, improve personalisation).
    """
    profile = ""
    if user_input.get("age"):
        profile += f" The person is {user_input['age']} years old"
        if user_input.get("weight"):
            profile += f" and weighs {user_input['weight']} kg"
        profile += "."

    prompt = f"""
You are a professional fitness trainer.

Create a personalized, structured 7-day workout plan for someone with the goal of **{user_input['goal']}**, and prefers **{user_input['intensity']} intensity** workouts.{profile}

Each day must include:
- A warm-up (5-10 mins)
- Main workout (targeted exercises, sets & reps)
- Cooldown or recovery tip

Format:
Day 1:
Warm-up: ...
Main Workout: ...
Cooldown: ...
(Repeat for Day 2-7)

Include at least one rest or active-recovery day. End with a one-line reminder to consult a doctor before starting a new routine.
"""
    return generate_text(PRO_MODELS, prompt)
