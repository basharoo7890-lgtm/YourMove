from app.services.ml_classifier import StressClassifier


def test_classifier_returns_stressed_for_high_scores():
    classifier = StressClassifier()
    features = {
        "z_score_movement": 2.5,
        "z_score_rt": 2.1,
        "cv_movement": 0.8,
        "cv_rt": 0.7,
        "ewma_gaze_angle": 30,
        "trend_movement": "increasing",
    }
    result = classifier.classify(1, features)
    assert result["raw_state"] in {"STRESSED", "OVERWHELMED"}
    assert result["stress_score"] > 2


def test_classifier_ai_command_trigger():
    classifier = StressClassifier()
    state = classifier.get_state(9)
    state.current_state = "OVERWHELMED"
    state.consecutive_stress_count = 5
    cmd = classifier.get_ai_command(9)
    assert cmd is not None
    assert cmd["command"] == "AUTO_EMERGENCY_STOP"
