from app.repositories.telemetry_repository import TelemetryRepository


class RecommendationService:
    """
    Local rule-based recommendation generator (free, no external API).
    """

    def __init__(self, repo: TelemetryRepository):
        self.repo = repo

    async def build_end_session_recommendation(self, session_id: int) -> dict:
        metrics = await self.repo.get_recommendation_metrics(session_id)
        avg_rt = metrics["avg_reaction_time_ms"]
        avg_movement = metrics["avg_movement_index"]
        stress_count = metrics["stress_count"]
        total_cls = metrics["total_classifications"]

        recommendations: list[str] = []
        risk_level = "low"

        if total_cls > 0 and (stress_count / total_cls) >= 0.5:
            risk_level = "high"
            recommendations.append("تقليل صعوبة الأنشطة في الجلسة القادمة بنسبة 20-30%.")
            recommendations.append("إضافة فترات راحة قصيرة كل 5-7 دقائق.")
        elif stress_count >= 2:
            risk_level = "medium"
            recommendations.append("المتابعة بنفس الخطة مع تعزيز فترات التهدئة.")

        if avg_rt is not None and avg_rt > 700:
            recommendations.append("سرعة الاستجابة بطيئة؛ استخدم تعليمات أبسط ومهام أقصر.")
        elif avg_rt is not None and avg_rt < 350:
            recommendations.append("الاستجابة جيدة؛ يمكن رفع الصعوبة تدريجيًا.")

        if avg_movement is not None and avg_movement > 2.0:
            recommendations.append("ارتفاع الحركة ملحوظ؛ جرّب بيئة أقل محفزات حسية.")
        elif avg_movement is not None and avg_movement < 0.5:
            recommendations.append("الحركة منخفضة؛ أضف نشاطًا حركيًا خفيفًا لزيادة التفاعل.")

        if not recommendations:
            recommendations.append("المؤشرات مستقرة؛ استمر بنفس خطة الجلسة الحالية.")

        result = {
            "type": "recommendation",
            "session_id": session_id,
            "risk_level": risk_level,
            "recommendations": recommendations,
            "metrics": metrics,
            "source": "local_rule_engine",
        }

        report_text = " | ".join(recommendations)
        await self.repo.create_ai_report(
            session_id=session_id,
            report_text=report_text,
            report_json=result,
            model_used="local_rule_engine_v1",
        )
        return result
