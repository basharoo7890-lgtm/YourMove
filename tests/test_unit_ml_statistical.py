from app.services.ml_statistical import StatisticalAnalyzer


def test_motion_ewma_sequence():
    analyzer = StatisticalAnalyzer()
    session_id = 101

    first = analyzer.update_motion(session_id, total_movement_index=1.0, is_baseline=True)
    second = analyzer.update_motion(session_id, total_movement_index=2.0, is_baseline=True)
    third = analyzer.update_motion(session_id, total_movement_index=3.0, is_baseline=True)

    # alpha = 0.3
    # ewma1 = 1.0
    # ewma2 = 0.3*2 + 0.7*1 = 1.3
    # ewma3 = 0.3*3 + 0.7*1.3 = 1.81
    assert first["ewma_movement"] == 1.0
    assert second["ewma_movement"] == 1.3
    assert third["ewma_movement"] == 1.81
