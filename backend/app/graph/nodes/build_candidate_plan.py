"""Graph node: assemble an initial trip plan from retrieved candidates."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, List

from app.graph.state import PlannerState
from app.schemas.trip import Attraction, DayPlan, Hotel, Meal, ParsedTripRequest, TripPlan, WeatherInfo
from app.schemas.user import UserProfile


PACE_TO_ATTRACTION_COUNT = {
    "dense": 4,
    "balanced": 3,
    "relaxed": 2,
    "slow": 2,
}


def _safe_date(date_str: str | None) -> datetime:
    if not date_str:
        return datetime.now()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return datetime.now()


def _chunk_attractions(rows: List[Attraction], days: int, each_day: int) -> List[List[Attraction]]:
    if not rows:
        return [[] for _ in range(days)]

    chunks: List[List[Attraction]] = []
    index = 0
    for _ in range(days):
        day_rows: List[Attraction] = []
        for _ in range(each_day):
            day_rows.append(rows[index % len(rows)])
            index += 1
        chunks.append(day_rows)
    return chunks


def make_build_candidate_plan_node() -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        parsed = ParsedTripRequest.model_validate(state.get("parsed_request") or {})
        profile = UserProfile.model_validate(
            state.get("memory_profile") or {"user_id": str(state.get("user_id") or "guest")}
        )
        candidates = dict(state.get("candidates") or {})

        city = parsed.city or "北京"
        start_date = parsed.start_date or datetime.now().strftime("%Y-%m-%d")
        days = parsed.travel_days or 3
        end_date = parsed.end_date or (_safe_date(start_date) + timedelta(days=days - 1)).strftime("%Y-%m-%d")

        pace = parsed.pace_preference or profile.pace_preference or "balanced"
        each_day = PACE_TO_ATTRACTION_COUNT.get(pace, 3)

        attraction_rows = [Attraction.model_validate(item) for item in candidates.get("attractions") or []]
        hotel_rows = [Hotel.model_validate(item) for item in candidates.get("hotels") or []]
        weather_rows = [WeatherInfo.model_validate(item) for item in candidates.get("weather") or []]

        raw_meal_rows = candidates.get("daily_meals") or []
        meal_rows: List[List[Meal]] = []
        for day in raw_meal_rows:
            meal_rows.append([Meal.model_validate(meal) for meal in day])

        split_attractions = _chunk_attractions(attraction_rows, days=days, each_day=each_day)

        day_plans: List[DayPlan] = []
        base_date = _safe_date(start_date)
        for idx in range(days):
            day_date = (base_date + timedelta(days=idx)).strftime("%Y-%m-%d")
            hotel = hotel_rows[min(idx, len(hotel_rows) - 1)] if hotel_rows else None
            meals = meal_rows[idx] if idx < len(meal_rows) else []
            daily_attractions = split_attractions[idx] if idx < len(split_attractions) else []

            transportation = parsed.transportation or profile.transport_preference or "地铁+步行"
            accommodation = parsed.accommodation or (hotel.type if hotel else "舒适型酒店")

            description = f"第{idx + 1}天：围绕{', '.join(item.name for item in daily_attractions[:2])}展开城市探索。"
            day_plans.append(
                DayPlan(
                    date=day_date,
                    day_index=idx,
                    description=description,
                    transportation=transportation,
                    accommodation=accommodation,
                    hotel=hotel,
                    attractions=daily_attractions,
                    meals=meals,
                )
            )

        overall_suggestions = (
            "建议提前预订热门景点门票并留出机动时间；"
            "午后可安排休息，夜间优先体验城市美食与轻松散步。"
        )

        plan = TripPlan(
            city=city,
            start_date=start_date,
            end_date=end_date,
            days=day_plans,
            weather_info=weather_rows,
            overall_suggestions=overall_suggestions,
            personalization_explanation=[],
        )

        return {"raw_plan": plan.model_dump()}

    return node
