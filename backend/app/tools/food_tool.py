"""Food recommendation tool."""

from __future__ import annotations

from typing import List

from app.schemas.trip import Meal


FOOD_THEME = {
    "美食": ["本地老字号", "特色小馆", "夜市档口"],
    "清淡": ["粥铺", "蒸菜馆", "家常菜馆"],
    "辣": ["川味馆", "湘味馆", "火锅店"],
}


class FoodTool:
    def recommend_daily_meals(self, city: str, preferences: List[str], days: int) -> List[List[Meal]]:
        theme = ["本地老字号", "特色小馆", "夜市档口"]
        for key, values in FOOD_THEME.items():
            if any(key in pref for pref in preferences):
                theme = values
                break

        meal_plans: List[List[Meal]] = []
        for idx in range(days):
            meal_plans.append(
                [
                    Meal(type="breakfast", name=f"{city}{theme[0]}早餐", description="低负担补能量", estimated_cost=25),
                    Meal(type="lunch", name=f"{city}{theme[1]}午餐", description="午间补给", estimated_cost=55),
                    Meal(type="dinner", name=f"{city}{theme[2]}晚餐", description="特色风味体验", estimated_cost=75),
                ]
            )
        return meal_plans
