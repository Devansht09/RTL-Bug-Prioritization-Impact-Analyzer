"""
FastAPI Backend — RTL Bug Prioritization & Impact Analyzer
============================================================
Serves the HTML frontend at GET / and provides API endpoints.
"""

from __future__ import annotations

import os
import logging
import pathlib
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.pipeline import run_pipeline
from backend.ml.model import get_model
from backend.ml.synthetic_data import FEATURE_NAMES

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RTL Bug Prioritization & Impact Analyzer",
    description=(
        "An EDA intelligence tool that combines RTL static analysis, "
        "graph-based dependency traversal, and ML-based bug prioritization."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve local static assets (plotly, etc.) for offline use
_static_dir = pathlib.Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ExternalIssue(BaseModel):
    type: str
    signal: str
    module: str = "unknown"
    location: str = ""
    confidence: float = 0.75
    description: str = ""


class AnalyzeRequest(BaseModel):
    rtl_code: str
    external_issues: List[ExternalIssue] = []


# ---------------------------------------------------------------------------
# Startup: warm the ML model
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    logger.info("Warming up ML model...")
    get_model()
    logger.info("ML model ready.")


@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serve the main HTML frontend."""
    html_path = pathlib.Path(__file__).parent.parent / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(html_path), media_type="text/html")

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/model/info", tags=["ML"])
def model_info():
    """Return model accuracy and feature importances."""
    model = get_model()
    return {
        "train_accuracy": model.train_accuracy,
        "feature_importances": model.get_feature_importances(),
        "feature_names": FEATURE_NAMES,
    }


@app.get("/examples", tags=["Examples"])
def list_examples():
    """List available bundled example Verilog files."""
    base = pathlib.Path(__file__).parent.parent / "examples"
    files = [f.name for f in base.glob("*.v")]
    return {"examples": files}


@app.get("/examples/{filename}", tags=["Examples"])
def get_example(filename: str):
    """Return the content of a bundled example file."""
    base = pathlib.Path(__file__).parent.parent / "examples"
    path = base / filename
    if not path.exists() or path.suffix not in (".v", ".json"):
        raise HTTPException(status_code=404, detail="Example not found.")
    return {"filename": filename, "content": path.read_text(encoding="utf-8")}


@app.post("/analyze", tags=["Analysis"])
def analyze(request: AnalyzeRequest):
    """
    Run the full 9-stage RTL analysis pipeline.

    Accepts:
      - rtl_code: Verilog/VHDL source as a string
      - external_issues: Optional list of pre-detected issues from lint tools

    Returns ranked issues with severity scores, propagation analysis, and explanations.
    """
    if not request.rtl_code or len(request.rtl_code.strip()) < 10:
        raise HTTPException(status_code=400, detail="rtl_code is empty or too short.")

    ext_list = [ei.dict() for ei in request.external_issues]

    try:
        result = run_pipeline(
            rtl_code=request.rtl_code,
            external_issues=ext_list,
        )
    except Exception as e:
        logger.exception("Pipeline error")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    return result


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
