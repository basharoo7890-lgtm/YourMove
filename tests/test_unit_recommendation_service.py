import asyncio

from app.services.recommendation_service import RecommendationService


class FakeRepo:
    async def get_recommendation_metrics(self, session_id: int) -> dict:
        return {
            "avg_reaction_time_ms": 820.0,
            "avg_movement_index": 2.4,
            "stress_count": 6,
            "total_classifications": 10,
        }

    async def create_ai_report(self, session_id: int, report_text: str, report_json: dict, model_used: str) -> None:
        self.saved = (session_id, report_text, report_json, model_used)


def test_recommendation_service_high_risk():
    repo = FakeRepo()
    service = RecommendationService(repo)  # type: ignore[arg-type]
    result = asyncio.run(service.build_end_session_recommendation(5))
    assert result["risk_level"] == "high"
    assert len(result["recommendations"]) >= 2
