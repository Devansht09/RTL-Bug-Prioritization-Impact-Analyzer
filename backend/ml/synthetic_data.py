"""
Synthetic Training Data Generator
====================================
Generates ~600 labeled samples for training the RF model.
Each sample is a feature vector with a severity label.

Features:
  [bug_type_enc, reach_output, propagation_depth_norm,
   fanout_norm, timing_flag, module_importance, confidence]

Labels:
  0 = Low, 1 = Medium, 2 = High
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Tuple

# Bug type encoding
BUG_TYPE_ENCODING = {
    "unused_signal": 0,
    "undriven_signal": 1,
    "conflicting_assignment": 2,
    "latch_risk": 3,
    "external": 4,
}


def generate_synthetic_data(n_samples: int = 600, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic feature matrix X and label vector y.

    Feature columns:
      0: bug_type_enc       (0-4)
      1: reach_output       (0 or 1)
      2: propagation_depth  (normalized: 1/depth, 0 if no path)
      3: fanout_count       (normalized: fanout/20, capped at 1.0)
      4: timing_flag        (1 if latch_risk or clocked signal)
      5: module_importance  (0.0 - 1.0, random for synthetic)
      6: confidence         (0.0 - 1.0)

    Label:
      0 = Low, 1 = Medium, 2 = High
    """
    rng = np.random.RandomState(seed)
    X = []
    y = []

    for _ in range(n_samples):
        bug_type = rng.randint(0, 5)
        reach_output = rng.randint(0, 2)
        prop_depth = rng.randint(1, 15) if reach_output else 999
        prop_depth_norm = 1.0 / prop_depth if prop_depth < 999 else 0.0
        fanout = rng.randint(0, 25)
        fanout_norm = min(fanout / 20.0, 1.0)
        timing_flag = 1 if bug_type == 3 else rng.randint(0, 2) * rng.randint(0, 2)
        module_importance = rng.uniform(0.1, 1.0)
        confidence = rng.uniform(0.5, 1.0)

        feat = [
            bug_type,
            reach_output,
            prop_depth_norm,
            fanout_norm,
            timing_flag,
            module_importance,
            confidence,
        ]

        # Heuristic label assignment
        score = (
            0.40 * reach_output
            + 0.25 * prop_depth_norm
            + 0.20 * fanout_norm
            + 0.15 * timing_flag
        )
        # Boost for critical bug types
        if bug_type == 2:   # conflicting assignment
            score += 0.15
        if bug_type == 3:   # latch risk
            score += 0.10
        if bug_type == 1:   # undriven
            score += 0.05
        score = score * confidence + rng.uniform(-0.05, 0.05)
        score = max(0.0, min(1.0, score))

        if score >= 0.60:
            label = 2   # High
        elif score >= 0.35:
            label = 1   # Medium
        else:
            label = 0   # Low

        X.append(feat)
        y.append(label)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


FEATURE_NAMES = [
    "bug_type_encoded",
    "reach_output",
    "propagation_depth_norm",
    "fanout_norm",
    "timing_flag",
    "module_importance",
    "confidence",
]

LABEL_NAMES = ["Low", "Medium", "High"]
