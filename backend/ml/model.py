"""
ML Model — Stage 6
====================
Random Forest Classifier trained on synthetic data.
Produces severity probability score (0.0–1.0) per issue.

Design:
  - Train once at module import (fast, ~600 samples)
  - Expose predict_severity(feature_vector) → float
  - Expose feature_importances for UI display
"""

from __future__ import annotations

import logging
import numpy as np
from typing import List, Tuple

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from backend.ml.synthetic_data import generate_synthetic_data, FEATURE_NAMES, LABEL_NAMES

logger = logging.getLogger(__name__)


class SeverityModel:
    """
    Wraps a scikit-learn Random Forest trained on synthetic RTL bug data.
    """

    def __init__(self):
        self.pipeline: Pipeline = None
        self.feature_importances_: List[float] = []
        self.train_accuracy: float = 0.0
        self._trained = False

    def train(self, n_samples: int = 600, seed: int = 42) -> None:
        """Train the model on synthetic data."""
        X, y = generate_synthetic_data(n_samples=n_samples, seed=seed)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=seed, stratify=y
        )

        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=150,
                max_depth=8,
                min_samples_leaf=3,
                random_state=seed,
                class_weight="balanced",
            )),
        ])
        self.pipeline.fit(X_train, y_train)

        # Evaluate
        y_pred = self.pipeline.predict(X_test)
        acc = float(np.mean(y_pred == y_test))
        self.train_accuracy = acc
        logger.info(f"Model trained. Test accuracy: {acc:.3f}")

        # Feature importances from RF
        rf = self.pipeline.named_steps["clf"]
        self.feature_importances_ = rf.feature_importances_.tolist()
        self._trained = True

    def predict_severity(self, features: np.ndarray) -> float:
        """
        Returns a severity score in [0, 1].
        Uses class probabilities: weighted sum Low=0, Med=0.5, High=1.0
        """
        if not self._trained:
            self.train()

        if features.ndim == 1:
            features = features.reshape(1, -1)

        proba = self.pipeline.predict_proba(features)[0]  # shape (3,)
        # Weighted score: p_low*0 + p_med*0.5 + p_high*1.0
        score = float(proba[1] * 0.5 + proba[2] * 1.0)
        return score

    def predict_batch(self, X: np.ndarray) -> List[float]:
        """Predict severity scores for a batch of feature vectors."""
        if not self._trained:
            self.train()
        probas = self.pipeline.predict_proba(X)  # shape (n, 3)
        scores = (probas[:, 1] * 0.5 + probas[:, 2] * 1.0).tolist()
        return scores

    def get_feature_importances(self) -> List[Tuple[str, float]]:
        """Return sorted (feature_name, importance) list."""
        if not self.feature_importances_:
            return []
        pairs = list(zip(FEATURE_NAMES, self.feature_importances_))
        return sorted(pairs, key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# Module-level singleton — trained once on import
# ---------------------------------------------------------------------------

_model_instance: SeverityModel = None


def get_model() -> SeverityModel:
    global _model_instance
    if _model_instance is None:
        logger.info("Initializing and training severity model...")
        _model_instance = SeverityModel()
        _model_instance.train()
    return _model_instance
