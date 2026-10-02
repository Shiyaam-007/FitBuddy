"""FitBuddy tests. Gemini is mocked, so no API key or internet is needed.

Run:  pytest -v
"""
import os
import tempfile

# Use a throwaway database BEFORE the app is imported.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

import pytest
from fastapi.testclient import TestClient

from app import routes
from app.gemini_generator import GeminiError
from app.main import app

client = TestClient(app)

FORM = {
    "username": "Asha", "user_id": "1", "age": "25",
    "weight": "60", "goal": "weight loss", "intensity": "medium",
}


@pytest.fixture(autouse=True)
def mock_gemini(monkeypatch):
    monkeypatch.setattr(routes, "generate_workout_gemini", lambda d: f"Day 1: PLAN for {d['goal']} ({d['intensity']})")
    monkeypatch.setattr(routes, "generate_nutrition_tip_with_flash", lambda goal: f"TIP for {goal}")
    monkeypatch.setattr(routes, "update_workout_plan", lambda orig, fb: f"UPDATED: {fb}")


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_home_page():
    r = client.get("/")
    assert r.status_code == 200 and "FitBuddy" in r.text


def test_generate_workout_form_and_admin_view():
    r = client.post("/generate-workout", data=FORM)
    assert r.status_code == 200
    assert "PLAN for weight loss (medium)" in r.text and "TIP for weight loss" in r.text
    admin = client.get("/view-all-users")
    assert "Asha" in admin.text and "Not updated" in admin.text


def test_feedback_updates_plan():
    client.post("/generate-workout", data=FORM)
    r = client.post("/submit-feedback", data={"user_id": "1", "feedback": "more cardio"})
    assert r.status_code == 200
    assert "UPDATED: more cardio" in r.text and "Plan updated successfully" in r.text
    assert "UPDATED: more cardio" in client.get("/view-all-users").text


def test_feedback_unknown_user():
    r = client.post("/submit-feedback", data={"user_id": "999", "feedback": "more cardio"})
    assert r.status_code == 404 and "No plan found" in r.text


def test_validation_error_shows_message():
    bad = {**FORM, "intensity": "extreme"}
    r = client.post("/generate-workout", data=bad)
    assert r.status_code == 422 and "intensity" in r.text


def test_gemini_failure_is_reported(monkeypatch):
    def boom(_):
        raise GeminiError("API key missing")
    monkeypatch.setattr(routes, "generate_workout_gemini", boom)
    r = client.post("/generate-workout", data={**FORM, "user_id": "7"})
    assert r.status_code == 502 and "API key missing" in r.text
    assert routes.get_user(7) is None  # nothing saved on failure


def test_json_api_flow():
    payload = {"username": "Ravi", "user_id": 2, "age": 30, "weight": 75.5,
               "goal": "muscle gain", "intensity": "HIGH"}
    r = client.post("/generate-plan", json=payload)
    assert r.status_code == 200 and "workout_plan" in r.json()
    r = client.post("/update-plan/2", json={"feedback": "add yoga"})
    assert r.json() == {"updated_plan": "UPDATED: add yoga"}
    assert client.post("/update-plan/404", json={"feedback": "add yoga"}).status_code == 404
    r = client.post("/generate-workout/gemini", json={"goal": "muscle gain", "intensity": "low"})
    assert r.json()["model"] == "gemini-pro"
    r = client.post("/generate-nutrition-tip", json={"goal": "muscle gain"})
    assert r.json()["nutrition_tip"] == "TIP for muscle gain"
    assert any(u["id"] == 2 for u in client.get("/users").json())


def test_delete_user():
    client.post("/generate-workout", data={**FORM, "user_id": "55", "username": "DeleteMe"})
    r = client.post("/delete-user/55", follow_redirects=False)
    assert r.status_code == 303
    assert "DeleteMe" not in client.get("/view-all-users").text


def test_fallback_tip_when_flash_fails(monkeypatch):
    from app import gemini_flash_generator as gf
    def boom(model, prompt):
        raise GeminiError("down")
    monkeypatch.setattr(gf, "generate_text", boom)
    assert "protein" in gf.generate_nutrition_tip_with_flash("muscle gain").lower()


# ---------------------------------------------------------- model fallback
def test_model_fallback_on_404_and_quota(monkeypatch):
    """Retired model (404) and quota-limited model (429) are skipped automatically."""
    from app import gemini_generator as gg

    calls = []

    class FakeResp:
        text = "OK PLAN"

    class FakeModels:
        def generate_content(self, model, contents):
            calls.append(model)
            if model == "old-model":
                raise Exception("404 NOT_FOUND. model no longer available to new users")
            if model == "paid-model":
                raise Exception("429 RESOURCE_EXHAUSTED. limit: 0")
            return FakeResp()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gg, "get_client", lambda: FakeClient())
    gg._working.clear()
    assert gg.generate_text(["old-model", "paid-model", "good-model"], "hi") == "OK PLAN"
    assert calls == ["old-model", "paid-model", "good-model"]
    calls.clear()
    gg.generate_text(["old-model", "paid-model", "good-model"], "hi")  # remembers good model
    assert calls == ["good-model"]


def test_bad_key_stops_immediately_and_all_fail_message(monkeypatch):
    from app import gemini_generator as gg

    class FakeModels:
        def generate_content(self, model, contents):
            raise Exception("400 INVALID_ARGUMENT API key not valid")

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gg, "get_client", lambda: FakeClient())
    gg._working.clear()
    with pytest.raises(GeminiError) as e:
        gg.generate_text(["a", "b"], "hi")
    assert "API key not valid" in str(e.value)


def test_stale_env_model_is_still_followed_by_working_defaults(monkeypatch):
    from app import gemini_generator as gg
    monkeypatch.setenv("GEMINI_PRO_MODEL", "gemini-2.5-pro")
    chain = gg._chain("GEMINI_PRO_MODEL", ["gemini-3.1-pro-preview", "gemini-3-flash-preview"])
    assert chain[0] == "gemini-2.5-pro" and "gemini-3-flash-preview" in chain
