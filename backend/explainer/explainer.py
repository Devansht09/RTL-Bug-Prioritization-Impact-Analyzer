"""
Explainer — Stage 9
======================
Generates human-readable explanations for each scored issue.
Explanations include:
  - Signal propagation path
  - Output reachability
  - Fanout impact
  - Priority reasoning
  - Remediation suggestion
"""

from __future__ import annotations

from typing import List, Dict

from backend.scorer.scoring import ScoredIssue


# ---------------------------------------------------------------------------
# Bug type descriptions
# ---------------------------------------------------------------------------

_BUG_DESCRIPTIONS = {
    "unused_signal": "an unused signal declaration",
    "undriven_signal": "an undriven (floating) signal",
    "conflicting_assignment": "a conflicting multi-driver assignment",
    "latch_risk": "a potential latch inference",
    "external": "an externally detected issue",
}

_REMEDIATION = {
    "unused_signal": (
        "Remove the unused signal declaration or connect it to a valid logic path. "
        "Unused signals can mask integration bugs and increase confusion."
    ),
    "undriven_signal": (
        "Ensure the signal is assigned in at least one continuous or procedural block. "
        "Floating outputs in hardware result in undefined/X values."
    ),
    "conflicting_assignment": (
        "Ensure each signal has exactly one driver. "
        "Separate the logic into distinct always blocks or consolidate the assign statements. "
        "Mixed continuous+procedural drivers on the same reg will cause simulation/synthesis mismatches."
    ),
    "latch_risk": (
        "Add a default assignment before the case/if statement, or ensure all branches "
        "assign every signal. Use 'always_comb' and tools like 'full_case parallel_case' directives "
        "only with proper synthesis support."
    ),
    "external": (
        "Review the issue in context. Address it per the lint tool's recommendation."
    ),
}


# ---------------------------------------------------------------------------
# Explanation Generator
# ---------------------------------------------------------------------------

def _format_path(path: List[str]) -> str:
    if not path:
        return "(no direct path found)"
    if len(path) == 1:
        return path[0]
    return " → ".join(path)


def generate_explanation(si: ScoredIssue) -> str:
    issue = si.issue
    impact = si.impact
    bug_desc = _BUG_DESCRIPTIONS.get(issue.bug_type, issue.bug_type)
    remediation = _REMEDIATION.get(issue.bug_type, "Review and fix the issue.")

    lines: List[str] = []

    # --- Headline ---
    lines.append(
        f"⚠️  [{si.severity_label.upper()} PRIORITY] Signal '{issue.signal}' "
        f"in module '{issue.module}' has {bug_desc}."
    )
    lines.append("")

    # --- What the bug is ---
    lines.append(f"📋 Issue: {issue.description}")
    lines.append("")

    # --- Graph impact ---
    if impact.reach_output:
        path_str = _format_path(impact.signal_path)
        outputs = ", ".join(impact.affected_outputs) if impact.affected_outputs else "output"
        lines.append(
            f"📡 Propagation: This bug propagates to output port(s) [{outputs}] "
            f"via the signal path: {path_str}"
        )
        lines.append(
            f"   Distance to output: {impact.propagation_depth} hop(s). "
            f"A shorter path means a faster fault manifestation."
        )
    else:
        lines.append(
            f"📡 Propagation: This bug does NOT directly propagate to any output port. "
            f"However, it may still cause simulation mismatch or synthesis warnings."
        )

    lines.append(f"   Fanout: {impact.fanout_count} downstream signal(s) affected.")
    lines.append("")

    # --- Scoring ---
    lines.append(
        f"📊 Scores: Rule={si.rule_score:.3f} | ML={si.ml_score:.3f} | "
        f"Final={si.final_score:.3f} (70% rule + 30% ML)"
    )
    lines.append(f"   Confidence: {issue.confidence:.0%}")
    lines.append("")

    # --- Why this priority ---
    if si.severity_label == "High":
        lines.append(
            "🔴 Priority Reasoning: Flagged HIGH because this bug reaches output logic "
            "with short propagation distance and/or high fanout — directly impacts "
            "observable hardware behavior. Must fix before tapeout."
        )
    elif si.severity_label == "Medium":
        lines.append(
            "🟡 Priority Reasoning: Flagged MEDIUM — the bug may affect internal pipeline "
            "signals or has limited output propagation. Should be fixed before signoff."
        )
    else:
        lines.append(
            "🟢 Priority Reasoning: Flagged LOW — the bug is isolated and does not "
            "reach any output port under current connectivity. Low immediate risk, "
            "but should be cleaned up for code quality."
        )
    lines.append("")

    # --- Remediation ---
    lines.append(f"🔧 Remediation: {remediation}")

    return "\n".join(lines)


def explain_all(scored_issues: List[ScoredIssue]) -> List[Dict]:
    """Returns list of explanation dicts for all scored issues."""
    results = []
    for si in scored_issues:
        explanation = generate_explanation(si)
        results.append({
            "issue_id": si.issue.issue_id,
            "signal": si.issue.signal,
            "module": si.issue.module,
            "bug_type": si.issue.bug_type,
            "severity_label": si.severity_label,
            "final_score": si.final_score,
            "rule_score": si.rule_score,
            "ml_score": si.ml_score,
            "confidence": si.issue.confidence,
            "explanation": explanation,
            "signal_path": si.impact.signal_path,
            "affected_outputs": si.impact.affected_outputs,
            "fanout_count": si.impact.fanout_count,
            "propagation_depth": si.impact.propagation_depth,
            "reach_output": si.impact.reach_output,
            "location": si.issue.location,
            "description": si.issue.description,
            "features": si.features,
            "rank": si.issue.raw_details.get("rank", 0),
        })
    return results
