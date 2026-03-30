"""Map/POI retrieval tool with AMap backend and mock fallback."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List

import httpx

from app.core.config import get_settings
from app.schemas.trip import Attraction, Location
from app.tools.image_tool import ImageTool


@dataclass
class POISeed:
    name: str
    category: str
    ticket_price: int
    duration: int


MOCK_POIS = [
    POISeed("城市博物馆", "museum", 60, 120),
    POISeed("历史文化街区", "culture", 0, 150),
    POISeed("中央公园", "park", 0, 90),
    POISeed("艺术中心", "art", 80, 120),
    POISeed("地标观景台", "landmark", 120, 90),
    POISeed("非遗体验馆", "culture", 50, 100),
    POISeed("滨河步道", "outdoor", 0, 80),
    POISeed("古城墙遗址", "history", 40, 90),
]


class MapTool:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.image_tool = ImageTool()

    def _is_mock(self) -> bool:
        return self.settings.mock_mode or not self.settings.amap_api_key

    def search_attractions(self, city: str, preferences: List[str], limit: int = 8) -> List[Attraction]:
        if self._is_mock():
            return self._mock_attractions(city=city, preferences=preferences, limit=limit)

        keyword = preferences[0] if preferences else "景点"
        try:
            response = httpx.get(
                "https://restapi.amap.com/v3/place/text",
                params={
                    "key": self.settings.amap_api_key,
                    "output": "json",
                    "keywords": keyword,
                    "city": city,
                    "citylimit": "true",
                    "extensions": "all",
                    "offset": limit,
                    "page": 1,
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            pois = data.get("pois", [])
            attractions: List[Attraction] = []
            for poi in pois[:limit]:
                location = poi.get("location", "")
                lng, lat = self._parse_location(location)
                category = (poi.get("type") or "attraction").split(";")[0].strip() or "attraction"
                name = poi.get("name") or f"{city}景点"
                attractions.append(
                    Attraction(
                        name=name,
                        address=poi.get("address") or city,
                        location=Location(longitude=lng, latitude=lat),
                        visit_duration=120,
                        description=f"{city}热门景点，适合游览。",
                        category=category,
                        ticket_price=60,
                        tags=preferences,
                        image_url=self.image_tool.get_attraction_image(
                            city=city,
                            attraction_name=name,
                            category=category,
                            tags=preferences,
                        ),
                    )
                )
            if attractions:
                return attractions
        except Exception as exc:
            print(f"[map-tool-warning] real API failed, fallback to mock: {exc}")

        return self._mock_attractions(city=city, preferences=preferences, limit=limit)

    def _mock_attractions(self, city: str, preferences: List[str], limit: int) -> List[Attraction]:
        base_lng, base_lat = self._city_anchor(city)
        rows: List[Attraction] = []
        for idx, seed in enumerate(MOCK_POIS[:limit]):
            offset_lng = base_lng + (idx % 4) * 0.015
            offset_lat = base_lat + (idx // 4) * 0.012
            name = f"{city}{seed.name}"
            rows.append(
                Attraction(
                    name=name,
                    address=f"{city}核心区{idx + 1}号",
                    location=Location(longitude=offset_lng, latitude=offset_lat),
                    visit_duration=seed.duration,
                    description=f"{city}代表性{seed.category}景点。",
                    category=seed.category,
                    ticket_price=seed.ticket_price,
                    tags=preferences,
                    image_url=self.image_tool.get_attraction_image(
                        city=city,
                        attraction_name=name,
                        category=seed.category,
                        tags=preferences,
                    ),
                )
            )
        return rows

    @staticmethod
    def _parse_location(raw: str) -> tuple[float, float]:
        if "," not in raw:
            return 116.397128, 39.916527
        left, right = raw.split(",", 1)
        try:
            return float(left), float(right)
        except ValueError:
            return 116.397128, 39.916527

    @staticmethod
    def _city_anchor(city: str) -> tuple[float, float]:
        digest = hashlib.md5(city.encode("utf-8")).hexdigest()
        seed_int = int(digest[:8], 16)
        lng = 100 + (seed_int % 3000) / 100.0
        lat = 20 + ((seed_int // 3000) % 2000) / 100.0
        return lng, lat
