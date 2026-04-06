"""
Pipeline Orchestrator — Full 9-Stage Pipeline
===============================================
Ties all stages together in a single call.

Usage:
    from backend.pipeline import run_pipeline
    results = run_pipeline(rtl_code="...", external_issues=[...])
"""

from __future__ import annotations

import logging
import time
from typing import List, Dict, Optional

from backend.parser.rtl_parser import parse_rtl, RTLRepresentation
from backend.detector.bug_detector import BugDetector, Issue
from backend.graph.dependency_graph import DependencyGraph, GraphImpact
from backend.scorer.scoring import HybridScorer, ScoredIssue
from backend.explainer.explainer import explain_all

logger = logging.getLogger(__name__)

# Module-level singletons
_detector = BugDetector()
_scorer: Optional[HybridScorer] = None


def _get_scorer() -> HybridScorer:
    global _scorer
    if _scorer is None:
        _scorer = HybridScorer()
    return _scorer


def run_pipeline(
    rtl_code: str,
    external_issues: List[Dict] = None,
) -> Dict:
    """
    Execute the full 9-stage RTL Bug Prioritization pipeline.

    Args:
        rtl_code       : Raw Verilog/VHDL source text
        external_issues: Optional list of pre-detected issues from lint tools

    Returns:
        Dict with keys:
          - parse_info   : Parser metadata
          - graph_stats  : Graph topology stats
          - graph_data   : Nodes + edges for visualization
          - results      : List of explained, ranked issues
          - summary      : High-level counts
          - timing_ms    : Per-stage timing
    """
    t0 = time.time()
    timing: Dict[str, float] = {}
    external_issues = external_issues or []

    # -----------------------------------------------------------------------
    # STAGE 1: RTL Parsing
    # -----------------------------------------------------------------------
    t = time.time()
    rep = parse_rtl(rtl_code)
    timing["stage1_parse"] = round((time.time() - t) * 1000, 2)
    logger.info(f"Stage 1 done in {timing['stage1_parse']}ms")

    parse_info = {
        "method": rep.parse_method,
        "modules": rep.modules,
        "signal_count": len(rep.signals),
        "assignment_count": len(rep.assignments),
        "always_block_count": len(rep.always_blocks),
        "output_signals": list(rep.outputs),
        "input_signals": list(rep.inputs),
    }

    if not rep.signals and not rep.assignments:
        return {
            "parse_info": parse_info,
            "graph_stats": {},
            "graph_data": {"nodes": [], "edges": []},
            "results": [],
            "summary": {"total": 0, "high": 0, "medium": 0, "low": 0},
            "timing_ms": timing,
            "error": "Parser extracted no signals. Check that the input is valid Verilog/VHDL.",
        }

    # -----------------------------------------------------------------------
    # STAGE 2 & 3: Bug Detection + External Issue Aggregation
    # -----------------------------------------------------------------------
    t = time.time()
    issues: List[Issue] = _detector.detect(rep, external_issues)
    timing["stage2_detect"] = round((time.time() - t) * 1000, 2)
    logger.info(f"Stage 2 done in {timing['stage2_detect']}ms — {len(issues)} issues")

    if not issues:
        dep_graph = DependencyGraph()
        dep_graph.build(rep)
        return {
            "parse_info": parse_info,
            "graph_stats": dep_graph.get_stats(),
            "graph_data": dep_graph.get_graph_data(),
            "results": [],
            "summary": {"total": 0, "high": 0, "medium": 0, "low": 0},
            "timing_ms": timing,
            "message": "No bugs detected in the provided RTL code. 🎉",
        }

    # -----------------------------------------------------------------------
    # STAGE 4: Dependency Graph
    # -----------------------------------------------------------------------
    t = time.time()
    dep_graph = DependencyGraph()
    dep_graph.build(rep)
    timing["stage3_graph"] = round((time.time() - t) * 1000, 2)

    # -----------------------------------------------------------------------
    # STAGE 5: BFS Impact Analysis
    # -----------------------------------------------------------------------
    t = time.time()
    bug_signals = list({issue.signal for issue in issues})
    impacts: Dict[str, GraphImpact] = dep_graph.analyze_all(bug_signals)
    timing["stage4_bfs"] = round((time.time() - t) * 1000, 2)

    # -----------------------------------------------------------------------
    # STAGE 6 + 7 + 8: Feature Extraction + ML Scoring + Ranking
    # -----------------------------------------------------------------------
    t = time.time()
    scorer = _get_scorer()
    scored_issues: List[ScoredIssue] = scorer.score_all(
        issues, impacts, rep.modules
    )
    timing["stage5_score"] = round((time.time() - t) * 1000, 2)

    # -----------------------------------------------------------------------
    # STAGE 9: Explanation Generation
    # -----------------------------------------------------------------------
    t = time.time()
    explained = explain_all(scored_issues)
    timing["stage6_explain"] = round((time.time() - t) * 1000, 2)
    timing["total"] = round((time.time() - t0) * 1000, 2)

    # Summary stats
    high = sum(1 for r in explained if r["severity_label"] == "High")
    med  = sum(1 for r in explained if r["severity_label"] == "Medium")
    low  = sum(1 for r in explained if r["severity_label"] == "Low")

    return {
        "parse_info": parse_info,
        "graph_stats": dep_graph.get_stats(),
        "graph_data": dep_graph.get_graph_data(),
        "results": explained,
        "summary": {
            "total": len(explained),
            "high": high,
            "medium": med,
            "low": low,
        },
        "timing_ms": timing,
    }
