"""FitBuddy - FastAPI entry point.  Run:  uvicorn app.main:app --reload"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routes import router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

init_db()  # creates fitbuddy.db + tables on first run

app = FastAPI(
    title="FitBuddy - AI Fitness Plan Generator",
    description="Personalised 7-day workout plans and nutrition tips powered by Google Gemini.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(router)


@app.get("/health", tags=["API"])
def health():
    return {"status": "ok"}
