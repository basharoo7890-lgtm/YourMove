"""
ML Layer 3 — Motion Analysis
- RMS (Root Mean Square) per tracker
- Entropy (movement randomness)
- FFT-based dominant frequency (rhythmic vs chaotic)
- Cross-tracker correlation (coordinated vs uncoordinated)
- Classification: FATIGUE / DISTRACTION / NORMAL / HYPERACTIVE
"""

import math
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class MotionBuffer:
    """Per-session motion data buffer"""
    # Store last 60 movement_index samples per tracker group
    upper_body: List[float] = field(default_factory=list)  # arms + head
    lower_body: List[float] = field(default_factory=list)  # legs + feet
    total: List[float] = field(default_factory=list)
    WINDOW: int = 60  # 1 minute at 1Hz


class MotionAnalyzer:
    def __init__(self):
        self.sessions: Dict[int, MotionBuffer] = {}

    def get_buffer(self, session_id: int) -> MotionBuffer:
        if session_id not in self.sessions:
            self.sessions[session_id] = MotionBuffer()
        return self.sessions[session_id]

    def analyze(self, session_id: int, trackers: dict, total_movement_index: float) -> dict:
        """
        Analyze motion data from all trackers.
        trackers: {tracker_name: {x, y, z, w, accel_magnitude}, ...}
        """
        buf = self.get_buffer(session_id)

        # Split into upper/lower body
        upper_accels = []
        lower_accels = []
        for name, data in trackers.items():
            accel = data.get("accel_magnitude", 0)
            if any(k in name.upper() for k in ["H_R", "LUA", "RUA", "LRA", "RLA", "LH_R", "RH_R", "R_R"]):
                upper_accels.append(accel)
            else:
                lower_accels.append(accel)

        upper_avg = sum(upper_accels) / len(upper_accels) if upper_accels else 0
        lower_avg = sum(lower_accels) / len(lower_accels) if lower_accels else 0

        buf.upper_body.append(upper_avg)
        buf.lower_body.append(lower_avg)
        buf.total.append(total_movement_index)

        # Trim
        for lst in [buf.upper_body, buf.lower_body, buf.total]:
            while len(lst) > buf.WINDOW:
                lst.pop(0)

        result: dict[str, float | str] = {
            "rms_upper": round(self._rms(buf.upper_body), 4),
            "rms_lower": round(self._rms(buf.lower_body), 4),
            "rms_total": round(self._rms(buf.total), 4),
            "entropy_total": round(self._entropy(buf.total), 4),
            "dominant_freq_hz": round(self._dominant_frequency(buf.total), 4),
            "upper_lower_ratio": round(upper_avg / lower_avg, 3) if lower_avg > 0.01 else 0.0,
        }

        # Classify motion pattern
        result["motion_state"] = self._classify(result, len(buf.total))

        return result

    def _classify(self, features: dict, n_samples: int) -> str:
        """Classify motion pattern"""
        if n_samples < 10:
            return "INSUFFICIENT_DATA"

        rms = features["rms_total"]
        entropy = features["entropy_total"]

        # Low RMS + Low entropy = fatigue (barely moving, repetitive)
        if rms < 0.3 and entropy < 1.5:
            return "FATIGUE"

        # High RMS + High entropy = hyperactive (lots of random movement)
        if rms > 2.0 and entropy > 3.0:
            return "HYPERACTIVE"

        # Medium RMS + High entropy = distraction (unfocused movement)
        if entropy > 2.5 and rms > 0.5:
            return "DISTRACTION"

        return "NORMAL"

    def cleanup(self, session_id: int):
        self.sessions.pop(session_id, None)

    # ─── Math helpers ──────────────────────────────────

    @staticmethod
    def _rms(data: List[float]) -> float:
        if not data:
            return 0.0
        return math.sqrt(sum(x ** 2 for x in data) / len(data))

    @staticmethod
    def _entropy(data: List[float]) -> float:
        """Shannon entropy of binned movement values"""
        if len(data) < 5:
            return 0.0

        # Bin into 10 buckets
        min_v = min(data)
        max_v = max(data)
        if max_v == min_v:
            return 0.0

        n_bins = 10
        bin_width = (max_v - min_v) / n_bins
        counts = [0] * n_bins
        for v in data:
            idx = min(int((v - min_v) / bin_width), n_bins - 1)
            counts[idx] += 1

        n = len(data)
        entropy = 0.0
        for c in counts:
            if c > 0:
                p = c / n
                entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def _dominant_frequency(data: List[float]) -> float:
        """Simple DFT to find dominant frequency (Hz, assuming 1Hz sampling)"""
        n = len(data)
        if n < 10:
            return 0.0

        # Remove mean
        mean = sum(data) / n
        centered = [x - mean for x in data]

        # DFT magnitudes (skip DC component at k=0)
        max_mag = 0.0
        max_k = 1
        for k in range(1, n // 2):
            real = sum(centered[i] * math.cos(2 * math.pi * k * i / n) for i in range(n))
            imag = sum(centered[i] * math.sin(2 * math.pi * k * i / n) for i in range(n))
            mag = math.sqrt(real ** 2 + imag ** 2)
            if mag > max_mag:
                max_mag = mag
                max_k = k

        # Convert to Hz (sampling rate = 1Hz)
        return max_k / n


# Singleton
motion_analyzer = MotionAnalyzer()
