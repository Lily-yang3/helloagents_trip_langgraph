"""Hotel recommendation tool."""

from __future__ import annotations

from typing import List, Optional

from app.schemas.trip import Hotel, Location


class HotelTool:
    def recommend_hotels(
        self,
        city: str,
        budget_min: Optional[int],
        budget_max: Optional[int],
        limit: int = 5,
    ) -> List[Hotel]:
        min_price = budget_min or 180
        max_price = budget_max or 480
        step = max(40, (max_price - min_price) // max(limit, 1))

        hotels: List[Hotel] = []
        for idx in range(limit):
            price = min_price + idx * step
            hotels.append(
                Hotel(
                    name=f"{city}智选酒店{idx + 1}",
                    address=f"{city}中心区酒店路{idx + 8}号",
                    location=Location(longitude=116.30 + idx * 0.02, latitude=39.85 + idx * 0.01),
                    price_range=f"{max(120, price-40)}-{price+60}元",
                    rating=f"{4.1 + (idx % 3) * 0.2:.1f}",
                    distance=f"距离核心景点{1 + idx}公里",
                    type="舒适型酒店" if price > 260 else "经济型酒店",
                    estimated_cost=price,
                )
            )
        return hotels
