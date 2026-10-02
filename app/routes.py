"""All FitBuddy routes: HTML pages (Jinja2) and JSON API endpoints."""
import os

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from .database import (
    delete_user,
    get_all_plans,
    get_all_users,
    get_original_plan,
    get_plan,
    get_user,
    save_plan,
    save_user,
    update_plan,
)
from .gemini_flash_generator import generate_nutrition_tip_with_flash
from .gemini_generator import GeminiError, generate_workout_gemini
from .schemas import FeedbackRequest, NutritionRequest, UserInput, WorkoutRequest
from .updated_plan import update_workout_plan

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

router = APIRouter()


# ----------------------------------------------------------------- helpers
def _validation_message(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"]) or "input"
        msg = err["msg"].replace("Value error, ", "")
        parts.append(f"{field}: {msg}")
    return "; ".join(parts)


def _render_index(request: Request, error: str = None, form: dict = None, status: int = 200):
    return templates.TemplateResponse(
        request, "index.html", {"error": error, "form": form or {}}, status_code=status
    )


def _render_result(
    request: Request,
    user: dict,
    plan: dict,
    nutrition_tip: str = "",
    message: str = None,
    error: str = None,
    status: int = 200,
):
    is_updated = bool(plan.get("updated_plan"))
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "username": user["name"],
            "user_id": user["id"],
            "age": user["age"],
            "weight": user["weight"],
            "goal": user["goal"],
            "intensity": user["intensity"],
            "workout_plan": plan["updated_plan"] if is_updated else plan["original_plan"],
            "original_plan": plan["original_plan"],
            "is_updated": is_updated,
            "nutrition_tip": nutrition_tip,
            "message": message,
            "error": error,
        },
        status_code=status,
    )


# ------------------------------------------------------------- web routes
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Home page with the input form."""
    return _render_index(request)


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout(
    request: Request,
    username: str = Form(...),
    user_id: str = Form(...),
    age: str = Form(...),
    weight: str = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
):
    """Validate form -> Gemini Pro plan + Gemini Flash tip -> save -> result page."""
    form = dict(
        username=username, user_id=user_id, age=age, weight=weight, goal=goal, intensity=intensity
    )
    try:
        data = UserInput(**form)
    except ValidationError as exc:
        return _render_index(request, _validation_message(exc), form, 422)

    try:
        plan_text = generate_workout_gemini(
            {
                "goal": data.goal,
                "intensity": data.intensity,
                "age": data.age,
                "weight": data.weight,
            }
        )
    except GeminiError as exc:
        return _render_index(request, str(exc), form, 502)

    nutrition_tip = generate_nutrition_tip_with_flash(data.goal)

    save_user(
        user_id=data.user_id,
        name=data.username,
        age=data.age,
        weight=data.weight,
        goal=data.goal,
        intensity=data.intensity,
    )
    save_plan(data.user_id, plan_text)

    return _render_result(
        request,
        get_user(data.user_id),
        get_plan(data.user_id),
        nutrition_tip,
        message="Your personalised 7-day plan is ready!",
    )


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(request: Request, user_id: str = Form(...), feedback: str = Form(...)):
    """Send original plan + feedback to Gemini Pro, store the updated plan, show result."""
    try:
        uid = int(user_id)
    except ValueError:
        return _render_index(request, "User ID must be a number.", status=422)

    user, plan = get_user(uid), get_plan(uid)
    if not user or not plan:
        return _render_index(request, f"No plan found for User ID {uid}. Generate one first.", status=404)

    try:
        fb = FeedbackRequest(feedback=feedback)
    except ValidationError as exc:
        return _render_result(request, user, plan, error=_validation_message(exc), status=422)

    try:
        updated = update_workout_plan(get_original_plan(uid), fb.feedback)
    except GeminiError as exc:
        return _render_result(request, user, plan, error=str(exc), status=502)

    update_plan(uid, updated)
    nutrition_tip = generate_nutrition_tip_with_flash(user["goal"])
    return _render_result(
        request,
        user,
        get_plan(uid),
        nutrition_tip,
        message="Plan updated successfully based on your feedback!",
    )


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request):
    """Admin dashboard: every user with original + updated plan."""
    plans_by_user = {p["user_id"]: p for p in get_all_plans()}
    user_data = []
    for u in get_all_users():
        plan = plans_by_user.get(u["id"])
        user_data.append(
            {
                **u,
                "original_plan": plan["original_plan"] if plan else "N/A",
                "updated_plan": plan["updated_plan"] if plan and plan["updated_plan"] else "Not updated",
            }
        )
    return templates.TemplateResponse(request, "all_users.html", {"users": user_data})


@router.post("/delete-user/{user_id}")
def delete_user_route(user_id: int):
    """Admin action: delete a user and their plans."""
    delete_user(user_id)
    return RedirectResponse(url="/view-all-users", status_code=303)


# --------------------------------------------------------- JSON API routes
@router.post("/generate-workout/gemini", tags=["API"])
def api_generate_workout(request: WorkoutRequest):
    """Generate a workout plan with Gemini Pro (nothing is stored)."""
    try:
        result = generate_workout_gemini({"goal": request.goal, "intensity": request.intensity})
        return {"model": "gemini-pro", "workout_plan": result}
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/generate-nutrition-tip", tags=["API"])
def api_generate_tip(request: NutritionRequest):
    """Generate a nutrition/recovery tip with Gemini Flash."""
    return {"model": "gemini-flash", "nutrition_tip": generate_nutrition_tip_with_flash(request.goal)}


@router.post("/generate-plan", tags=["API"])
def api_generate_plan(user_data: UserInput):
    """Save the user, generate a plan with Gemini Pro and store it."""
    try:
        plan = generate_workout_gemini(
            {
                "goal": user_data.goal,
                "intensity": user_data.intensity,
                "age": user_data.age,
                "weight": user_data.weight,
            }
        )
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    save_user(
        user_id=user_data.user_id,
        name=user_data.username,
        age=user_data.age,
        weight=user_data.weight,
        goal=user_data.goal,
        intensity=user_data.intensity,
    )
    save_plan(user_data.user_id, plan)
    return {"message": "Workout plan generated and saved successfully!", "workout_plan": plan}


@router.post("/update-plan/{user_id}", tags=["API"])
def api_update_plan(user_id: int, data: FeedbackRequest):
    """Update a stored plan using feedback."""
    original = get_original_plan(user_id)
    if not original:
        raise HTTPException(status_code=404, detail="Original plan not found for this user.")
    try:
        updated = update_workout_plan(original, data.feedback)
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    update_plan(user_id, updated)
    return {"updated_plan": updated}


@router.get("/users", tags=["API"])
def api_list_users():
    """List all users with their plans as JSON."""
    plans = {p["user_id"]: p for p in get_all_plans()}
    return [
        {**u, "original_plan": plans.get(u["id"], {}).get("original_plan"),
         "updated_plan": plans.get(u["id"], {}).get("updated_plan")}
        for u in get_all_users()
    ]
