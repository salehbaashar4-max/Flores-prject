"""Vercel serverless entry point for the FastAPI backend.

Vercel's Python runtime serves the module-level `app` (an ASGI application).
The backend package lives in /backend/app, so we add /backend to sys.path.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Earth Engine reads its service-account credentials from a key file on disk,
# which a serverless deployment cannot ship. The key JSON arrives in the
# GEE_KEY_JSON env var and is written to /tmp here, before app.config reads
# GEE_KEY_FILE at import time.
_key_json = os.environ.get("GEE_KEY_JSON", "").strip()
try:
    json.loads(_key_json)
    with open("/tmp/gee-key.json", "w", encoding="utf-8") as fh:
        fh.write(_key_json)
    os.environ["GEE_KEY_FILE"] = "/tmp/gee-key.json"
except Exception as exc:
    print(f"GEE_KEY_JSON not usable ({exc}); Earth Engine will use fallback layers.")

from app.main import app  # noqa: E402,F401
