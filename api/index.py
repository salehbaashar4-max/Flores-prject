"""Vercel serverless entry point for the FastAPI backend.

Vercel's Python runtime serves the module-level `app` (an ASGI application).
The backend package lives in /backend/app, so we add /backend to sys.path.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402,F401
