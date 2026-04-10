"""
ML Orchestrator — Combines all ML layers into a single analysis pipeline
Also computes PSI (Patient Stability Index)

PSI = weighted combination of:
  - Stress state (0.30)
  - Movement stability (0.25)
  - Reaction time consistency (0.20)
  - Gaze stability (0.15)
  - Motion pattern (0.10)

Scale: 0-100 (100 = perfectly stable)
"""

from typing import Optional
from app.services.ml_statistical import statistical_analyzer
from app.services.ml_classifier import stress_classifier
from app.services.ml_motion import motion_analyzer


class MLOrchestrator:
    def __init__(self):
        self.stat = statistical_analyzer
        self.classifier = stress_classifier
        self.motion = motion_analyzer

    def process_motion(self, session_id: int, trackers: dict, total_movement_index: float, is_baseline: bool) -> dict:
        """Full ML pipeline for motion data"""
        # Layer 1: Statistical
        stat_result = self.stat.update_motion(session_id, total_movement_index, is_baseline)

        # Layer 3: Motion analysis
        motion_result = self.motion.analyze(session_id, trackers, total_movement_index)

        # Layer 2: Classify (needs accumulated features)
        features = {**stat_result}
        classification = self.classifier.classify(session_id, features)

        # PSI
        psi = self._compute_psi(session_id, classification, stat_result, motion_result)

        # AI command check
        ai_cmd = self.classifier.get_ai_command(session_id)

        return {
            "statistical": stat_result,
            "motion": motion_result,
            "classification": classification,
            "psi": psi,
            "ai_command": ai_cmd,
        }

    def process_game_event(self, session_id: int, rt_ms: Optional[float], is_baseline: bool) -> dict:
        """ML pipeline for game events with reaction time"""
        if rt_ms is None:
            return {}

        stat_result = self.stat.update_reaction_time(session_id, rt_ms, is_baseline)

        # Re-classify with updated RT features
        s = self.stat.get_session(session_id)
        features = {
            "ewma_movement": s.ewma_movement,
            "z_score_movement": self.stat._z_score(
                s.ewma_movement, s.baseline_movement_mean, s.baseline_movement_std, s.movement_history
            ) if s.movement_history else 0,
            "cv_movement": self.stat._cv(s.movement_history),
            **stat_result,
        }
        classification = self.classifier.classify(session_id, features)
        ai_cmd = self.classifier.get_ai_command(session_id)

        return {
            "statistical": stat_result,
            "classification": classification,
            "ai_command": ai_cmd,
        }

    def process_gaze(self, session_id: int, angle: float) -> dict:
        """ML pipeline for gaze data"""
        return self.stat.update_gaze(session_id, angle)

    def finalize_baseline(self, session_id: int):
        self.stat.finalize_baseline(session_id)

    def cleanup(self, session_id: int):
        self.stat.cleanup(session_id)
        self.classifier.cleanup(session_id)
        self.motion.cleanup(session_id)

    def snapshot_state(self, session_id: int) -> dict:
        """Serialize current ML state for DB persistence (restart recovery)."""
        s = self.stat.get_session(session_id)
        c = self.classifier.get_state(session_id)
        return {
            "stat": {
                "ewma_movement": s.ewma_movement,
                "ewma_rt": s.ewma_rt,
                "ewma_gaze_angle": s.ewma_gaze_angle,
                "initialized": s.initialized,
                "movement_history": s.movement_history[-60:],
                "rt_history": s.rt_history[-60:],
                "gaze_history": s.gaze_history[-60:],
                "baseline_movement_mean": s.baseline_movement_mean,
                "baseline_movement_std": s.baseline_movement_std,
                "baseline_rt_mean": s.baseline_rt_mean,
                "baseline_rt_std": s.baseline_rt_std,
            },
            "classifier": {
                "current_state": c.current_state,
                "confidence": c.confidence,
                "consecutive_stress_count": c.consecutive_stress_count,
                "history": c.history[-30:],
            },
        }

    def restore_state(self, session_id: int, state: dict):
        """Restore ML state from DB snapshot (after server restart)."""
        if not state:
            return

        stat_data = state.get("stat", {})
        if stat_data:
            s = self.stat.get_session(session_id)
            s.ewma_movement = stat_data.get("ewma_movement", 0.0)
            s.ewma_rt = stat_data.get("ewma_rt", 0.0)
            s.ewma_gaze_angle = stat_data.get("ewma_gaze_angle", 0.0)
            s.initialized = stat_data.get("initialized", False)
            s.movement_history = stat_data.get("movement_history", [])
            s.rt_history = stat_data.get("rt_history", [])
            s.gaze_history = stat_data.get("gaze_history", [])
            s.baseline_movement_mean = stat_data.get("baseline_movement_mean")
            s.baseline_movement_std = stat_data.get("baseline_movement_std")
            s.baseline_rt_mean = stat_data.get("baseline_rt_mean")
            s.baseline_rt_std = stat_data.get("baseline_rt_std")

        cls_data = state.get("classifier", {})
        if cls_data:
            c = self.classifier.get_state(session_id)
            c.current_state = cls_data.get("current_state", "CALM")
            c.confidence = cls_data.get("confidence", 0.5)
            c.consecutive_stress_count = cls_data.get("consecutive_stress_count", 0)
            c.history = cls_data.get("history", [])

    def _compute_psi(self, session_id: int, classification: dict, stat: dict, motion: dict) -> dict:
        """Patient Stability Index: 0-100"""
        state = classification.get("state", "CALM")

        # Component 1: Stress state (30%)
        state_scores = {"CALM": 95, "ENGAGED": 85, "STRESSED": 40, "OVERWHELMED": 10}
        stress_component = state_scores.get(state, 50)

        # Component 2: Movement stability (25%) — low CV = stable
        cv_mov = stat.get("cv_movement", 0)
        movement_component = max(0, 100 - cv_mov * 100)

        # Component 3: RT consistency (20%) — low CV = consistent
        cv_rt = stat.get("cv_rt", 0) if "cv_rt" in stat else 0
        rt_component = max(0, 100 - cv_rt * 100)

        # Component 4: Gaze stability (15%) — low gaze angle = focused
        gaze_angle = stat.get("ewma_gaze_angle", 0) if "ewma_gaze_angle" in stat else 0
        gaze_s = self.stat.get_session(session_id)
        gaze_cv = self.stat._cv(gaze_s.gaze_history) if gaze_s.gaze_history else 0
        gaze_component = max(0, 100 - gaze_cv * 80 - (gaze_angle / 45) * 20)

        # Component 5: Motion pattern (10%)
        motion_state = motion.get("motion_state", "NORMAL")
        motion_scores = {"NORMAL": 90, "FATIGUE": 50, "DISTRACTION": 35, "HYPERACTIVE": 20, "INSUFFICIENT_DATA": 70}
        motion_component = motion_scores.get(motion_state, 50)

        # Weighted sum
        psi = (
            stress_component * 0.30 +
            movement_component * 0.25 +
            rt_component * 0.20 +
            gaze_component * 0.15 +
            motion_component * 0.10
        )

        return {
            "score": round(max(0, min(100, psi)), 1),
            "components": {
                "stress": round(stress_component, 1),
                "movement_stability": round(movement_component, 1),
                "rt_consistency": round(rt_component, 1),
                "gaze_stability": round(gaze_component, 1),
                "motion_pattern": round(motion_component, 1),
            },
            "weights": {"stress": 0.30, "movement": 0.25, "rt": 0.20, "gaze": 0.15, "motion": 0.10},
        }


# Singleton
ml_orchestrator = MLOrchestrator()
