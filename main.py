"""
Top-level entry point for deployment platforms (Vercel, Render, Railway, etc.)
They look for `main.py` or `app.py` in the root directory.
"""
from backend.main import app
