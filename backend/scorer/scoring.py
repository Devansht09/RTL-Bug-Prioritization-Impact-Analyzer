"""
Hybrid Scorer — Stage 7 & 8
==============================
Combines rule-based score and ML-based score into a final severity score.
Ranks issues and assigns labels (High / Medium / Low).

Scoring formula:
  rule_score  = 0.40 * reach_output
              + 0.25 * (1 / propagation_depth)
              + 0.20 * fanout_norm
              + 0.15 * timing_risk

  final_score = 0.70 * rule_score + 0.30 * ml_score

Labels:
  High   ≥ 0.60
  Medium ≥ 0.35
  Low    < 0.35
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Dict

import numpy as np

from backend.detector.bug_detector import Issue
from backend.graph.dependency_graph import GraphImpact
from backend.ml.feature_extractor import extract_all_features
from backend.ml.model import get_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scored Issue
# ---------------------------------------------------------------------------

@dataclass
class ScoredIssue:
    issue: Issue
    impact: GraphImpact
    rule_score: float
    ml_score: float
    final_score: float
    severity_label: str        # 'High' | 'Medium' | 'Low'
    features: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scoring Logic
# ---------------------------------------------------------------------------

def _rule_score(impact: GraphImpact, issue: Issue) -> float:
    reach = 1.0 if impact.reach_output else 0.0

    depth = impact.propagation_depth
    if depth == 0:
        # Bug IS directly on an output port — maximum urgency
        depth_score = 1.0
    elif 0 < depth < 999:
        depth_score = 1.0 / depth
    else:
        depth_score = 0.0

    fanout_norm = min(impact.fanout_count / 20.0, 1.0)

    timing = 1.0 if issue.bug_type in ("latch_risk",) else 0.0
    if "clk" in issue.signal.lower() or "clock" in issue.signal.lower():
        timing = 1.0

    # Confidence multiplier
    conf = issue.confidence

    base = (
        0.40 * reach
        + 0.25 * depth_score
        + 0.20 * fanout_norm
        + 0.15 * timing
    )
    return float(min(1.0, base * conf))


def _label_from_score(score: float) -> str:
    if score >= 0.60:
        return "High"
    elif score >= 0.35:
        return "Medium"
    else:
        return "Low"


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class HybridScorer:
    """
    Scores all issues using hybrid rule + ML approach.
    """

    def __init__(self):
        self.model = get_model()

    def score_all(
        self,
        issues: List[Issue],
        impacts: Dict[str, GraphImpact],
        all_modules: List[str],
    ) -> List[ScoredIssue]:
        if not issues:
            return []

        # Extract feature matrix
        feat_matrix = extract_all_features(issues, impacts, all_modules)

        # ML scores (batch predict)
        ml_scores = self.model.predict_batch(feat_matrix)

        scored: List[ScoredIssue] = []
        for i, issue in enumerate(issues):
            impact = impacts.get(issue.signal, GraphImpact(
                signal=issue.signal,
                reach_output=False,
                propagation_depth=999,
                fanout_count=0,
            ))

            rs = _rule_score(impact, issue)
            ms = ml_scores[i]
            fs = 0.70 * rs + 0.30 * ms

            # Feature dict for display
            feat_dict = {
                "bug_type_encoded": float(feat_matrix[i][0]),
                "reach_output": float(feat_matrix[i][1]),
                "propagation_depth_norm": float(feat_matrix[i][2]),
                "fanout_norm": float(feat_matrix[i][3]),
                "timing_flag": float(feat_matrix[i][4]),
                "module_importance": float(feat_matrix[i][5]),
                "confidence": float(feat_matrix[i][6]),
            }

            scored.append(ScoredIssue(
                issue=issue,
                impact=impact,
                rule_score=round(rs, 4),
                ml_score=round(ms, 4),
                final_score=round(fs, 4),
                severity_label=_label_from_score(fs),
                features=feat_dict,
            ))

        # Sort descending by final_score
        scored.sort(key=lambda s: s.final_score, reverse=True)

        # Assign rank
        for rank, si in enumerate(scored, 1):
            si.issue.raw_details["rank"] = rank

        logger.info(
            f"Scored {len(scored)} issues. "
            f"High={sum(1 for s in scored if s.severity_label=='High')}, "
            f"Medium={sum(1 for s in scored if s.severity_label=='Medium')}, "
            f"Low={sum(1 for s in scored if s.severity_label=='Low')}"
        )
        return scored
