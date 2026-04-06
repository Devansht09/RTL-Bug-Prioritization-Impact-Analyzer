"""
Launcher — starts FastAPI + opens browser automatically.
Run: python run.py
"""
import threading, webbrowser, time, uvicorn

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

threading.Thread(target=open_browser, daemon=True).start()
uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
