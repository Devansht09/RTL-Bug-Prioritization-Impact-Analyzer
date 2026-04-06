"""
Bug Detector — Stage 2 of the Pipeline
========================================
Implements 4 rule-based bug detectors on the parsed RTLRepresentation.

Detectors:
  1. UnusedSignalDetector
  2. UndrivenSignalDetector
  3. ConflictingAssignmentDetector
  4. LatchRiskDetector
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Set, Dict
from backend.parser.rtl_parser import RTLRepresentation, Signal, Assignment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Issue Data Structure
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    issue_id: str
    bug_type: str        # 'unused_signal' | 'undriven_signal' | 'conflicting_assignment' | 'latch_risk'
    signal: str
    module: str
    location: str        # e.g. "line 14" or "always block at line 22"
    confidence: float    # 0.0 – 1.0
    description: str
    raw_details: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base Detector
# ---------------------------------------------------------------------------

class BaseDetector:
    name: str = "base"

    def detect(self, rep: RTLRepresentation) -> List[Issue]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 1. Unused Signal Detector
# ---------------------------------------------------------------------------

class UnusedSignalDetector(BaseDetector):
    """
    Finds signals declared in the module but never referenced on the
    right-hand side of any assignment (i.e. never read).
    Inputs and outputs are excluded from the 'unused' check since they
    are interface signals.
    """
    name = "unused_signal"

    def detect(self, rep: RTLRepresentation) -> List[Issue]:
        issues: List[Issue] = []

        # Build set of all RHS signals (signals that are READ)
        rhs_used: Set[str] = set()
        for asn in rep.assignments:
            for s in asn.rhs_signals:
                rhs_used.add(s)

        # Internal signals (wire/reg) that are never READ
        skipped_kinds = {'input', 'output', 'inout'}
        for sig in rep.signals:
            if sig.kind in skipped_kinds:
                continue
            if sig.name not in rhs_used:
                issues.append(Issue(
                    issue_id=f"unused_{sig.module}_{sig.name}",
                    bug_type="unused_signal",
                    signal=sig.name,
                    module=sig.module,
                    location=f"module {sig.module}",
                    confidence=0.85,
                    description=(
                        f"Signal '{sig.name}' ({sig.kind}{' '+sig.width if sig.width else ''}) "
                        f"is declared in module '{sig.module}' but never referenced on "
                        f"the right-hand side of any assignment."
                    ),
                    raw_details={"kind": sig.kind, "width": sig.width},
                ))

        return issues


# ---------------------------------------------------------------------------
# 2. Undriven Signal Detector
# ---------------------------------------------------------------------------

class UndrivenSignalDetector(BaseDetector):
    """
    Finds signals declared but never assigned (driven).
    Output ports that are never assigned are especially critical.
    """
    name = "undriven_signal"

    def detect(self, rep: RTLRepresentation) -> List[Issue]:
        issues: List[Issue] = []

        # Build set of all LHS signals (signals that are WRITTEN)
        lhs_driven: Set[str] = set()
        for asn in rep.assignments:
            lhs_driven.add(asn.lhs)

        # Signals that are never on the LHS
        for sig in rep.signals:
            if sig.kind == 'input':
                continue  # inputs are driven externally
            if sig.name not in lhs_driven:
                # Output that is undriven is critical
                is_output = sig.kind == 'output' or sig.name in rep.outputs
                conf = 0.95 if is_output else 0.80
                issues.append(Issue(
                    issue_id=f"undriven_{sig.module}_{sig.name}",
                    bug_type="undriven_signal",
                    signal=sig.name,
                    module=sig.module,
                    location=f"module {sig.module}",
                    confidence=conf,
                    description=(
                        f"Signal '{sig.name}' ({sig.kind}) in module '{sig.module}' "
                        f"is never assigned/driven. "
                        + ("This is an OUTPUT port — hardware output will be floating!" if is_output else "")
                    ),
                    raw_details={"is_output": is_output, "kind": sig.kind},
                ))

        return issues


# ---------------------------------------------------------------------------
# 3. Conflicting Assignment Detector
# ---------------------------------------------------------------------------

class ConflictingAssignmentDetector(BaseDetector):
    """
    Finds signals assigned more than once — indicating multiple drivers.
    Same signal driven by both a procedural always block AND a continuous
    assign is especially problematic.
    """
    name = "conflicting_assignment"

    def detect(self, rep: RTLRepresentation) -> List[Issue]:
        issues: List[Issue] = []

        # Group by (module, signal) and track assignment kinds
        seen: Dict[str, List[Assignment]] = {}
        for asn in rep.assignments:
            key = f"{asn.module}::{asn.lhs}"
            seen.setdefault(key, []).append(asn)

        for key, asns in seen.items():
            if len(asns) < 2:
                continue
            mod, sig = key.split("::", 1)
            kinds = [a.kind for a in asns]
            has_mixed = 'continuous' in kinds and 'procedural' in kinds
            conf = 0.95 if has_mixed else 0.75
            lines = [str(a.line) for a in asns if a.line]
            issues.append(Issue(
                issue_id=f"conflict_{mod}_{sig}",
                bug_type="conflicting_assignment",
                signal=sig,
                module=mod,
                location=f"lines {', '.join(lines)}" if lines else f"module {mod}",
                confidence=conf,
                description=(
                    f"Signal '{sig}' in module '{mod}' is assigned {len(asns)} times "
                    f"({'mixed continuous+procedural — potential multi-driver conflict!' if has_mixed else 'multiple procedural assignments'})."
                ),
                raw_details={
                    "assignment_count": len(asns),
                    "kinds": kinds,
                    "lines": lines,
                    "has_mixed_drivers": has_mixed,
                },
            ))

        return issues


# ---------------------------------------------------------------------------
# 4. Latch Risk Detector
# ---------------------------------------------------------------------------

class LatchRiskDetector(BaseDetector):
    """
    Finds always blocks that may infer latches:
    - Combinational (always @*) block where not all conditions have
      assignments for all outputs (no default/else)
    - Clock-edge blocks missing else branches
    """
    name = "latch_risk"

    def detect(self, rep: RTLRepresentation) -> List[Issue]:
        issues: List[Issue] = []

        for block in rep.always_blocks:
            # Skip if default/else found
            if block.has_default:
                continue

            # Collect signals assigned in this block
            assigned_sigs = {a.lhs for a in block.assignments}
            if not assigned_sigs:
                continue

            # Determine if this is a combinational block
            sens = block.sensitivity.lower()
            is_clocked = 'posedge' in sens or 'negedge' in sens
            is_combo = '*' in sens or 'always_comb' in sens.replace(' ', '')

            if is_clocked and not block.has_default:
                # Clocked block without full else — may create unintentional latch behavior
                for sig in assigned_sigs:
                    issues.append(Issue(
                        issue_id=f"latch_{block.module}_{sig}_line{block.line}",
                        bug_type="latch_risk",
                        signal=sig,
                        module=block.module,
                        location=f"always block at line {block.line}",
                        confidence=0.70,
                        description=(
                            f"Signal '{sig}' in clocked always block (line {block.line}) "
                            f"in module '{block.module}' may not be assigned in all "
                            f"conditions — risk of unintended latch inference."
                        ),
                        raw_details={
                            "sensitivity": block.sensitivity,
                            "is_clocked": True,
                            "line": block.line,
                        },
                    ))
            elif is_combo and not block.has_default:
                for sig in assigned_sigs:
                    issues.append(Issue(
                        issue_id=f"latch_{block.module}_{sig}_line{block.line}",
                        bug_type="latch_risk",
                        signal=sig,
                        module=block.module,
                        location=f"always @(*) block at line {block.line}",
                        confidence=0.88,
                        description=(
                            f"Signal '{sig}' in combinational always @(*) block (line {block.line}) "
                            f"in module '{block.module}' lacks a default assignment — "
                            f"this will infer a latch in synthesis!"
                        ),
                        raw_details={
                            "sensitivity": block.sensitivity,
                            "is_combo": True,
                            "line": block.line,
                        },
                    ))

        return issues


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

class BugDetector:
    """
    Runs all detectors and merges results. Also accepts external issues
    (from lint tools) and converts them to Issue format.
    """

    def __init__(self):
        self.detectors = [
            UnusedSignalDetector(),
            UndrivenSignalDetector(),
            ConflictingAssignmentDetector(),
            LatchRiskDetector(),
        ]

    def detect(
        self,
        rep: RTLRepresentation,
        external_issues: List[Dict] = None,
    ) -> List[Issue]:
        all_issues: List[Issue] = []

        # Run rule-based detectors
        for detector in self.detectors:
            found = detector.detect(rep)
            logger.info(f"[{detector.name}] found {len(found)} issues")
            all_issues.extend(found)

        # Merge externally provided issues
        if external_issues:
            for i, ext in enumerate(external_issues):
                all_issues.append(Issue(
                    issue_id=f"external_{i}_{ext.get('signal','?')}",
                    bug_type=ext.get("type", "external"),
                    signal=ext.get("signal", "unknown"),
                    module=ext.get("module", "unknown"),
                    location=ext.get("location", "external tool"),
                    confidence=float(ext.get("confidence", 0.75)),
                    description=ext.get("description", f"External issue: {ext.get('type')}"),
                    raw_details=ext,
                ))

        # Deduplicate by issue_id
        seen_ids: Set[str] = set()
        deduped: List[Issue] = []
        for issue in all_issues:
            if issue.issue_id not in seen_ids:
                seen_ids.add(issue.issue_id)
                deduped.append(issue)

        logger.info(f"Total issues after dedup: {len(deduped)}")
        return deduped
