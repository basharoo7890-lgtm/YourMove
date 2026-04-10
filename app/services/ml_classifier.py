"""
ML Layer 2 — Stress State Classifier
States: CALM / ENGAGED / STRESSED / OVERWHELMED

Phase 1 (now): Rule-based using Layer 1 statistics
Phase 2 (after 20+ sessions): Train Random Forest on labeled data
Phase 3 (after 100+ sessions): XGBoost with full feature set

Input features (8):
  1. ewma_movement
  2. z_score_movement
  3. cv_movement
  4. ewma_rt
  5. z_score_rt
  6. cv_rt
  7. ewma_gaze_angle
  8. trend_movement (encoded: -1/0/1)
"""

from typing import Dict, Optional
from dataclasses import dataclass, field


STATES = ["CALM", "ENGAGED", "STRESSED", "OVERWHELMED"]


@dataclass
class ClassifierState:
    """Per-session classifier memory"""
    current_state: str = "CALM"
    confidence: float = 0.5
    consecutive_stress_count: int = 0
    history: list = field(default_factory=list)  # last N predictions
    MAX_HISTORY: int = 30


class StressClassifier:
    def __init__(self):
        self.sessions: Dict[int, ClassifierState] = {}

    def get_state(self, session_id: int) -> ClassifierState:
        if session_id not in self.sessions:
            self.sessions[session_id] = ClassifierState()
        return self.sessions[session_id]

    def classify(self, session_id: int, features: dict) -> dict:
        """
        Rule-based classification using statistical features.
        Returns: {state, confidence, features_used, feature_importance}
        """
        s = self.get_state(session_id)

        z_mov = features.get("z_score_movement", 0)
        z_rt = features.get("z_score_rt", 0)
        cv_mov = features.get("cv_movement", 0)
        cv_rt = features.get("cv_rt", 0)
        ewma_gaze = features.get("ewma_gaze_angle", 0)
        trend = features.get("trend_movement", "stable")

        trend_num = {"increasing": 1, "stable": 0, "decreasing": -1}.get(trend, 0)

        # ─── Scoring system ────────────────────────────
        stress_score = 0.0
        importance = {}

        # High movement Z-Score → stress
        if z_mov > 2.0:
            stress_score += 3.0
            importance["z_score_movement"] = 0.3
        elif z_mov > 1.0:
            stress_score += 1.5
            importance["z_score_movement"] = 0.15
        elif z_mov < -1.0:
            stress_score -= 1.0  # very still = calm or disengaged
            importance["z_score_movement"] = 0.1

        # High RT Z-Score → overwhelmed or disengaged
        if z_rt > 2.0:
            stress_score += 2.0
            importance["z_score_rt"] = 0.25
        elif z_rt > 1.0:
            stress_score += 1.0
            importance["z_score_rt"] = 0.12

        # High CV → erratic behavior
        if cv_mov > 0.5:
            stress_score += 1.5
            importance["cv_movement"] = 0.15
        if cv_rt > 0.5:
            stress_score += 1.0
            importance["cv_rt"] = 0.1

        # Gaze instability
        if ewma_gaze > 25:
            stress_score += 1.0
            importance["ewma_gaze_angle"] = 0.1

        # Increasing movement trend
        if trend_num == 1:
            stress_score += 0.5
            importance["trend"] = 0.05

        # ─── Map score to state ────────────────────────
        if stress_score >= 5.0:
            state = "OVERWHELMED"
            confidence = min(0.95, 0.7 + (stress_score - 5) * 0.05)
        elif stress_score >= 2.5:
            state = "STRESSED"
            confidence = min(0.9, 0.6 + (stress_score - 2.5) * 0.06)
        elif stress_score >= 0.5:
            state = "ENGAGED"
            confidence = 0.7
        else:
            state = "CALM"
            confidence = max(0.5, 0.8 - abs(stress_score) * 0.1)

        # ─── Smoothing (avoid flicker) ─────────────────
        s.history.append(state)
        if len(s.history) > s.MAX_HISTORY:
            s.history.pop(0)

        # Need 3 consecutive same-state to switch
        if len(s.history) >= 3 and len(set(s.history[-3:])) == 1:
            s.current_state = state
            s.confidence = confidence
        # Exception: OVERWHELMED triggers immediately
        elif state == "OVERWHELMED" and stress_score >= 6.0:
            s.current_state = state
            s.confidence = confidence

        # Track consecutive stress for AI commands
        if s.current_state in ("STRESSED", "OVERWHELMED"):
            s.consecutive_stress_count += 1
        else:
            s.consecutive_stress_count = 0

        return {
            "state": s.current_state,
            "confidence": round(s.confidence, 3),
            "raw_state": state,
            "stress_score": round(stress_score, 3),
            "consecutive_stress": s.consecutive_stress_count,
            "feature_importance": importance,
        }

    def get_ai_command(self, session_id: int) -> Optional[dict]:
        """
        Generate automatic AI command if stress persists.
        Returns None or {command, value, reason}
        """
        s = self.get_state(session_id)

        if s.current_state == "OVERWHELMED" and s.consecutive_stress_count >= 5:
            s.consecutive_stress_count = 0  # reset after command
            return {
                "type": "ai_command",
                "command": "AUTO_EMERGENCY_STOP",
                "value": "true",
                "reason": "OVERWHELMED state sustained for 5+ readings"
            }

        if s.current_state == "STRESSED" and s.consecutive_stress_count >= 10:
            s.consecutive_stress_count = 0
            return {
                "type": "ai_command",
                "command": "AUTO_REDUCE_DIFFICULTY",
                "value": "-1",
                "reason": "STRESSED state sustained for 10+ readings"
            }

        if s.current_state == "STRESSED" and s.consecutive_stress_count == 7:
            # Don't reset counter — allow escalation to AUTO_REDUCE_DIFFICULTY at 10
            return {
                "type": "ai_command",
                "command": "AUTO_SUGGEST_BREAK",
                "value": "30",
                "reason": "STRESSED state sustained for 7+ readings"
            }

        return None

    def cleanup(self, session_id: int):
        self.sessions.pop(session_id, None)


# Singleton
stress_classifier = StressClassifier()
