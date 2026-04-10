import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.repositories.telemetry_repository import TelemetryRepository
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger("yourmove.final_report")


class FinalReportService:
    def __init__(self, repo: TelemetryRepository):
        self.repo = repo
        self.settings = get_settings()

    async def generate(self, session_id: int) -> dict[str, Any]:
        context = await self.repo.get_report_context(session_id)
        recommendation = await RecommendationService(self.repo).build_end_session_recommendation(session_id)

        prompt = (
            "You are an assistant generating a clinical-style but non-diagnostic session summary.\n"
            "Do not provide medical diagnosis or medication advice.\n"
            "Write concise and practical recommendations for next session.\n\n"
            f"Session context: {context}\n"
            f"Recommendation engine output: {recommendation}\n\n"
            "Return plain text with sections:\n"
            "1) Overall Summary\n"
            "2) Behavioral Observations\n"
            "3) Risk Interpretation\n"
            "4) Next Session Recommendations\n"
            "5) Safety Notes"
        )

        llm_text = await self._generate_with_gemini(prompt)
        model_used = "gemini_api" if llm_text else "local_rule_engine"
        if not llm_text:
            llm_text = self._build_local_text(context, recommendation)

        result = {
            "type": "final_report",
            "session_id": session_id,
            "model_used": model_used,
            "summary": llm_text,
            "recommendation": recommendation,
            "context": context,
        }
        await self.repo.create_ai_report(session_id, llm_text, result, model_used)
        return result

    async def get_latest(self, session_id: int) -> dict[str, Any] | None:
        report = await self.repo.get_latest_ai_report(session_id)
        if not report:
            return None
        return {
            "type": "final_report",
            "session_id": session_id,
            "generated_at": str(report.generated_at),
            "model_used": report.model_used,
            "summary": report.report_text,
            "data": report.report_json,
        }

    async def _generate_with_gemini(self, prompt: str) -> str | None:
        api_key = self.settings.GOOGLE_API_KEY
        if not api_key:
            return None

        model = self.settings.GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json=payload, headers={"x-goog-api-key": api_key})
                if response.status_code != 200:
                    logger.warning("Gemini API failed with status %s", response.status_code)
                    return None
                data = response.json()
                return (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text")
                )
        except Exception:
            logger.exception("Gemini API call failed")
            return None

    @staticmethod
    def _build_local_text(context: dict[str, Any], recommendation: dict[str, Any]) -> str:
        lines = [
            "Overall Summary:",
            f"- Session status: {context.get('session_status')}",
            f"- Data points: events={context.get('events_count')}, motion={context.get('motion_count')}, gaze={context.get('gaze_count')}",
            f"- Latest state: {context.get('latest_state')} (confidence={context.get('latest_confidence')})",
            "",
            "Behavioral Observations:",
            "- Observations were generated from movement, reaction-time, and gaze telemetry.",
            "",
            "Risk Interpretation:",
            f"- Risk level from recommendation engine: {recommendation.get('risk_level')}",
            "",
            "Next Session Recommendations:",
        ]
        for item in recommendation.get("recommendations", []):
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "Safety Notes:",
                "- This is an assistive summary, not a medical diagnosis.",
            ]
        )
        return "\n".join(lines)
