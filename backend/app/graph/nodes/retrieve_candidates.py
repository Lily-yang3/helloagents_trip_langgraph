"""Graph node: retrieve attractions/hotels/weather/food candidates."""

from __future__ import annotations

from typing import Callable, List

from app.graph.state import PlannerState
from app.schemas.trip import ParsedTripRequest
from app.schemas.user import UserProfile
from app.tools.food_tool import FoodTool
from app.tools.hotel_tool import HotelTool
from app.tools.map_tool import MapTool
from app.tools.weather_tool import WeatherTool


def make_retrieve_candidates_node(
    map_tool: MapTool,
    weather_tool: WeatherTool,
    hotel_tool: HotelTool,
    food_tool: FoodTool,
) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        parsed = ParsedTripRequest.model_validate(state.get("parsed_request") or {})
        profile = UserProfile.model_validate(
            state.get("memory_profile") or {"user_id": str(state.get("user_id") or "guest")}
        )

        city = parsed.city or "北京"
        days = parsed.travel_days or 3
        preferences: List[str] = list(dict.fromkeys([*(parsed.preferences or []), *(profile.attraction_preference or [])]))

        hotel_budget_min = profile.hotel_budget_min
        hotel_budget_max = profile.hotel_budget_max
        if parsed.total_budget and days > 0 and (hotel_budget_min is None or hotel_budget_max is None):
            per_day = max(parsed.total_budget // days, 200)
            hotel_budget_min = int(per_day * 0.35)
            hotel_budget_max = int(per_day * 0.55)

        attractions = map_tool.search_attractions(
            city=city,
            preferences=preferences,
            limit=max(days * 4, 8),
        )
        weather = weather_tool.get_weather(
            city=city,
            days=days,
            start_date=parsed.start_date,
        )
        hotels = hotel_tool.recommend_hotels(
            city=city,
            budget_min=hotel_budget_min,
            budget_max=hotel_budget_max,
            limit=max(3, min(6, days + 1)),
        )
        daily_meals = food_tool.recommend_daily_meals(
            city=city,
            preferences=preferences,
            days=days,
        )

        return {
            "candidates": {
                "attractions": [item.model_dump() for item in attractions],
                "weather": [item.model_dump() for item in weather],
                "hotels": [item.model_dump() for item in hotels],
                "daily_meals": [[meal.model_dump() for meal in day] for day in daily_meals],
            }
        }

    return node
