"""Graph node: personalize and rerank generated plan using user profile."""

from __future__ import annotations

from copy import deepcopy
from typing import Callable, List

from app.graph.state import PlannerState
from app.schemas.trip import ParsedTripRequest, TripPlan
from app.schemas.user import UserProfile


PACE_LIMITS = {
    "dense": 4,
    "balanced": 3,
    "relaxed": 2,
    "slow": 2,
}


def _contains_any(text: str, tokens: set[str]) -> bool:
    if not text:
        return False
    return any(token and token in text for token in tokens)


def make_personalize_rerank_node() -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        plan = TripPlan.model_validate(state.get("raw_plan") or {})
        parsed = ParsedTripRequest.model_validate(state.get("parsed_request") or {})
        profile = UserProfile.model_validate(
            state.get("memory_profile") or {"user_id": str(state.get("user_id") or "guest")}
        )

        output = deepcopy(plan)
        explanations: List[str] = []

        prefer_tokens = set(parsed.preferences or []) | set(profile.attraction_preference or [])
        avoid_tokens = set(parsed.avoid_tags or []) | set(profile.avoid_tags or [])
        pace = parsed.pace_preference or profile.pace_preference or "balanced"
        max_daily_items = PACE_LIMITS.get(pace, 3)

        for day in output.days:
            filtered = []
            for item in day.attractions:
                haystack = f"{item.name} {item.category} {item.description} {' '.join(item.tags or [])}"
                if avoid_tokens and _contains_any(haystack, avoid_tokens):
                    continue
                filtered.append(item)
            if filtered:
                day.attractions = filtered

            if prefer_tokens:
                day.attractions.sort(
                    key=lambda item: (
                        _contains_any(f"{item.name} {item.category} {item.description}", prefer_tokens),
                        item.ticket_price > 0,
                    ),
                    reverse=True,
                )

            if len(day.attractions) > max_daily_items:
                day.attractions = day.attractions[:max_daily_items]

        if prefer_tokens:
            explanations.append(
                f"结合你的兴趣偏好（{', '.join(sorted(prefer_tokens)[:4])}），优先安排了匹配景点。"
            )

        if avoid_tokens:
            explanations.append(f"根据你的避雷偏好（{', '.join(sorted(avoid_tokens)[:4])}），已减少不喜欢的景点类型。")

        if profile.hotel_budget_min or profile.hotel_budget_max:
            explanations.append(
                f"根据你的酒店预算区间 {profile.hotel_budget_min or '-'}-{profile.hotel_budget_max or '-'} 元，优先筛选预算匹配酒店。"
            )

        if pace in {"relaxed", "slow"}:
            explanations.append("你偏好慢节奏行程，每天景点数量已适当减少并保留休息窗口。")
        elif pace == "dense":
            explanations.append("你偏好高密度探索，已提高每天景点覆盖率。")

        output.personalization_explanation = explanations

        return {
            "personalized_plan": output.model_dump(),
            "personalization_explanation": explanations,
        }

    return node
