"""Budget aggregation and revision helper."""

from __future__ import annotations

from copy import deepcopy
from typing import Tuple

from app.schemas.trip import Budget, TripPlan


class BudgetTool:
    def calculate_budget(self, plan: TripPlan) -> Budget:
        attractions = 0
        hotels = 0
        meals = 0
        transportation = 0

        for day in plan.days:
            attractions += sum(max(0, item.ticket_price) for item in day.attractions)
            if day.hotel:
                hotels += max(0, day.hotel.estimated_cost)
            meals += sum(max(0, meal.estimated_cost) for meal in day.meals)
            transportation += 40 if "步行" in day.transportation else 80

        total = attractions + hotels + meals + transportation
        return Budget(
            total_attractions=attractions,
            total_hotels=hotels,
            total_meals=meals,
            total_transportation=transportation,
            total=total,
        )

    def check_over_budget(self, plan: TripPlan, total_budget: int | None) -> Tuple[bool, Budget]:
        budget = self.calculate_budget(plan)
        if total_budget is None:
            return False, budget
        return budget.total > total_budget, budget

    def revise_plan_under_budget(self, plan: TripPlan, total_budget: int) -> TripPlan:
        revised = deepcopy(plan)

        # 1) Reduce hotel costs first.
        for day in revised.days:
            if day.hotel and day.hotel.estimated_cost > 0:
                day.hotel.estimated_cost = int(day.hotel.estimated_cost * 0.82)
                day.hotel.type = "预算友好型" if day.hotel.type else "预算友好型"

        # 2) Reduce meal costs.
        for day in revised.days:
            for meal in day.meals:
                meal.estimated_cost = int(meal.estimated_cost * 0.85)

        # 3) Reduce paid attraction costs for non-core spots.
        for day in revised.days:
            for idx, item in enumerate(day.attractions):
                if idx >= 1 and item.ticket_price > 0:
                    item.ticket_price = int(item.ticket_price * 0.7)

        revised.budget = self.calculate_budget(revised)

        # 4) If still over budget, shrink one attraction per day when possible.
        if revised.budget.total > total_budget:
            for day in revised.days:
                if len(day.attractions) > 2:
                    day.attractions = day.attractions[:2]
            revised.budget = self.calculate_budget(revised)

        return revised
