"""Extract stable preference signals from user inputs and feedback."""

from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trip import ParsedTripRequest


STYLE_HINTS = {
    "慢": "slow",
    "悠闲": "slow",
    "紧凑": "dense",
    "高密度": "dense",
    "亲子": "family",
    "美食": "foodie",
}

TRANSPORT_HINTS = ["地铁", "打车", "步行", "自驾", "公交"]


class PreferenceSummarizer:
    """Rule-based preference summarizer.

    TODO: replace with model-assisted summarization once enough feedback data is available.
    """

    def from_request(self, parsed_request: ParsedTripRequest, raw_text: str) -> Dict[str, Any]:
        patch: Dict[str, Any] = {}
        text = raw_text or ""

        for key, value in STYLE_HINTS.items():
            if key in text:
                patch["travel_style"] = value
                patch.setdefault("confidence_scores", {})["travel_style"] = 0.6
                break

        if parsed_request.pace_preference:
            patch["pace_preference"] = parsed_request.pace_preference
            patch.setdefault("confidence_scores", {})["pace_preference"] = 0.8

        if parsed_request.preferences:
            patch["attraction_preference"] = parsed_request.preferences
            patch.setdefault("confidence_scores", {})["attraction_preference"] = 0.7

        if parsed_request.avoid_tags:
            patch["avoid_tags"] = parsed_request.avoid_tags
            patch.setdefault("confidence_scores", {})["avoid_tags"] = 0.7

        if parsed_request.transportation:
            patch["transport_preference"] = parsed_request.transportation
            patch.setdefault("confidence_scores", {})["transport_preference"] = 0.7
        else:
            for hint in TRANSPORT_HINTS:
                if hint in text:
                    patch["transport_preference"] = hint
                    patch.setdefault("confidence_scores", {})["transport_preference"] = 0.55
                    break

        if parsed_request.total_budget:
            # Assume 40%-60% budget range around total budget for hotel share inference.
            per_day_hotel_guess = max(parsed_request.total_budget // max(parsed_request.travel_days or 1, 1) // 2, 120)
            patch["hotel_budget_min"] = int(per_day_hotel_guess * 0.8)
            patch["hotel_budget_max"] = int(per_day_hotel_guess * 1.2)
            patch.setdefault("confidence_scores", {})["hotel_budget_range"] = 0.5

        return patch

    def from_feedback(self, feedback_text: str, rating: int | None = None) -> Dict[str, Any]:
        text = feedback_text or ""
        patch: Dict[str, Any] = {}

        if any(token in text for token in ["太赶", "太累", "太紧", "走不动"]):
            patch["pace_preference"] = "relaxed"
            patch.setdefault("confidence_scores", {})["pace_preference"] = 0.8

        if any(token in text for token in ["节奏太慢", "不够丰富", "多安排"]):
            patch["pace_preference"] = "dense"
            patch.setdefault("confidence_scores", {})["pace_preference"] = 0.75

        if "不喜欢" in text:
            # naive extraction: split by punctuation after "不喜欢"
            tail = text.split("不喜欢", 1)[1]
            candidates = [x.strip() for x in tail.replace("。", "，").split("，") if x.strip()]
            if candidates:
                patch["avoid_tags"] = candidates[:3]
                patch.setdefault("confidence_scores", {})["avoid_tags"] = 0.65

        if rating is not None and rating <= 2:
            patch.setdefault("confidence_scores", {})["global_preference_confidence_decay"] = 0.2

        return patch
