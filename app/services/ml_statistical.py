"""
ML Layer 1 — Statistical Analysis (Real-time, no training)
- EWMA (Exponentially Weighted Moving Average) α=0.3
- Z-Score anomaly detection
- CV (Coefficient of Variation)
- OLS trend detection
- Runs every incoming data point
"""

import math
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SessionStats:
    """Rolling statistics for one session"""
    # EWMA state
    ewma_movement: float = 0.0
    ewma_rt: float = 0.0
    ewma_gaze_angle: float = 0.0
    alpha: float = 0.3
    initialized: bool = False

    # Raw history (last N samples for Z-Score / CV)
    movement_history: List[float] = field(default_factory=list)
    rt_history: List[float] = field(default_factory=list)
    gaze_history: List[float] = field(default_factory=list)

    # Baseline reference
    baseline_movement_mean: Optional[float] = None
    baseline_movement_std: Optional[float] = None
    baseline_rt_mean: Optional[float] = None
    baseline_rt_std: Optional[float] = None

    MAX_HISTORY: int = 120  # ~2 min at 1Hz


class StatisticalAnalyzer:
    def __init__(self):
        self.sessions: Dict[int, SessionStats] = {}

    def get_session(self, session_id: int) -> SessionStats:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionStats()
        return self.sessions[session_id]

    def update_motion(self, session_id: int, total_movement_index: float, is_baseline: bool) -> dict:
        s = self.get_session(session_id)

        # EWMA
        if not s.initialized:
            s.ewma_movement = total_movement_index
            s.initialized = True
        else:
            s.ewma_movement = s.alpha * total_movement_index + (1 - s.alpha) * s.ewma_movement

        # History
        s.movement_history.append(total_movement_index)
        if len(s.movement_history) > s.MAX_HISTORY:
            s.movement_history.pop(0)

        # Z-Score (vs baseline if available, else vs rolling)
        z_score = self._z_score(
            total_movement_index,
            s.baseline_movement_mean,
            s.baseline_movement_std,
            s.movement_history,
        )

        # CV
        cv = self._cv(s.movement_history)

        # Trend (last 30 samples)
        trend = self._trend(s.movement_history[-30:])

        return {
            "ewma_movement": round(s.ewma_movement, 3),
            "z_score_movement": round(z_score, 3),
            "cv_movement": round(cv, 3),
            "trend_movement": trend,
            "raw": round(total_movement_index, 3),
        }

    def update_reaction_time(self, session_id: int, rt_ms: float, is_baseline: bool) -> dict:
        s = self.get_session(session_id)

        s.ewma_rt = s.alpha * rt_ms + (1 - s.alpha) * s.ewma_rt if s.rt_history else rt_ms

        s.rt_history.append(rt_ms)
        if len(s.rt_history) > s.MAX_HISTORY:
            s.rt_history.pop(0)

        z_score = self._z_score(rt_ms, s.baseline_rt_mean, s.baseline_rt_std, s.rt_history)
        cv = self._cv(s.rt_history)

        return {
            "ewma_rt": round(s.ewma_rt, 3),
            "z_score_rt": round(z_score, 3),
            "cv_rt": round(cv, 3),
            "raw_rt": round(rt_ms, 3),
        }

    def update_gaze(self, session_id: int, angle: float) -> dict:
        s = self.get_session(session_id)

        s.ewma_gaze_angle = s.alpha * angle + (1 - s.alpha) * s.ewma_gaze_angle if s.gaze_history else angle

        s.gaze_history.append(angle)
        if len(s.gaze_history) > s.MAX_HISTORY:
            s.gaze_history.pop(0)

        return {
            "ewma_gaze_angle": round(s.ewma_gaze_angle, 3),
            "cv_gaze": round(self._cv(s.gaze_history), 3),
        }

    def finalize_baseline(self, session_id: int):
        """Called when baseline ends — lock baseline stats"""
        s = self.get_session(session_id)
        if s.movement_history:
            s.baseline_movement_mean = self._mean(s.movement_history)
            s.baseline_movement_std = self._std(s.movement_history)
        if s.rt_history:
            s.baseline_rt_mean = self._mean(s.rt_history)
            s.baseline_rt_std = self._std(s.rt_history)

    def cleanup(self, session_id: int):
        self.sessions.pop(session_id, None)

    # ─── Math helpers ──────────────────────────────────

    @staticmethod
    def _mean(data: List[float]) -> float:
        return sum(data) / len(data) if data else 0.0

    @staticmethod
    def _std(data: List[float]) -> float:
        if len(data) < 2:
            return 0.0
        m = sum(data) / len(data)
        variance = sum((x - m) ** 2 for x in data) / (len(data) - 1)
        return math.sqrt(variance)

    def _z_score(self, value: float, baseline_mean: Optional[float], baseline_std: Optional[float], history: List[float]) -> float:
        if baseline_mean is not None and baseline_std and baseline_std > 0:
            return (value - baseline_mean) / baseline_std
        if len(history) >= 5:
            m = self._mean(history)
            s = self._std(history)
            if s > 0:
                return (value - m) / s
        return 0.0

    def _cv(self, data: List[float]) -> float:
        if len(data) < 3:
            return 0.0
        m = self._mean(data)
        if m == 0:
            return 0.0
        return self._std(data) / abs(m)

    @staticmethod
    def _trend(data: List[float]) -> str:
        """Simple OLS slope direction"""
        n = len(data)
        if n < 5:
            return "stable"
        x_mean = (n - 1) / 2
        y_mean = sum(data) / n
        num = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        if den == 0:
            return "stable"
        slope = num / den
        # Normalize slope relative to mean
        if y_mean != 0:
            rel_slope = slope / abs(y_mean)
        else:
            rel_slope = slope
        if rel_slope > 0.02:
            return "increasing"
        elif rel_slope < -0.02:
            return "decreasing"
        return "stable"


# Singleton
statistical_analyzer = StatisticalAnalyzer()
