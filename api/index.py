"""
Vercel serverless entry point for FitBuddy FastAPI app.
Vercel looks for the `app` object in api/index.py
"""
import sys
import os

# Make the parent directory importable so `app` package is found
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app  # noqa: F401 – Vercel needs this exported as `app`
