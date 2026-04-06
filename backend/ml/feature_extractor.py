"""
Feature Extractor — Stage 5
==============================
Converts (Issue + GraphImpact) → 7-dimensional feature vector
suitable for the ML model.
"""

from __future__ import annotations

import numpy as np
from typing import List, Dict, Optional

from backend.detector.bug_detector import Issue
from backend.graph.dependency_graph import GraphImpact
from backend.ml.synthetic_data import BUG_TYPE_ENCODING, FEATURE_NAMES


def compute_module_importance(module: str, all_modules: List[str]) -> float:
    """
    Heuristic module importance:
    - First module (top-level) = 1.0
    - Others scaled by position
    """
    if not all_modules or module not in all_modules:
        return 0.5
    idx = all_modules.index(module)
    return max(0.1, 1.0 - idx * 0.2)


def extract_features(
    issue: Issue,
    impact: GraphImpact,
    all_modules: List[str],
) -> np.ndarray:
    """
    Produces a float32 feature vector of length 7:
    [bug_type_enc, reach_output, prop_depth_norm, fanout_norm,
     timing_flag, module_importance, confidence]
    """
    bug_type_enc = float(BUG_TYPE_ENCODING.get(issue.bug_type, 4))

    reach_output = 1.0 if impact.reach_output else 0.0

    depth = impact.propagation_depth
    prop_depth_norm = 1.0 / depth if (depth > 0 and depth < 999) else 0.0

    fanout_norm = min(impact.fanout_count / 20.0, 1.0)

    timing_flag = 1.0 if issue.bug_type in ("latch_risk",) else 0.0
    # Also flag if sensitivity contains clock
    if "clk" in issue.signal.lower() or "clock" in issue.signal.lower():
        timing_flag = 1.0

    module_importance = compute_module_importance(issue.module, all_modules)

    confidence = float(issue.confidence)

    return np.array([
        bug_type_enc,
        reach_output,
        prop_depth_norm,
        fanout_norm,
        timing_flag,
        module_importance,
        confidence,
    ], dtype=np.float32)


def extract_all_features(
    issues: List[Issue],
    impacts: Dict[str, GraphImpact],
    all_modules: List[str],
) -> np.ndarray:
    """Returns feature matrix shape (n_issues, 7)."""
    rows = []
    for issue in issues:
        impact = impacts.get(issue.signal, GraphImpact(
            signal=issue.signal,
            reach_output=False,
            propagation_depth=999,
            fanout_count=0,
        ))
        rows.append(extract_features(issue, impact, all_modules))
    return np.vstack(rows) if rows else np.empty((0, 7), dtype=np.float32)
