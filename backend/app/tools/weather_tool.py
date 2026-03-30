"""Weather lookup tool with AMap backend and mock fallback."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import httpx

from app.core.config import get_settings
from app.schemas.trip import WeatherInfo


MOCK_WEATHER = [
    ("晴", "多云", 28, 18),
    ("多云", "小雨", 26, 17),
    ("阴", "阴", 24, 16),
    ("晴", "晴", 30, 20),
]


class WeatherTool:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _is_mock(self) -> bool:
        return self.settings.mock_mode or not self.settings.amap_api_key

    def get_weather(self, city: str, days: int, start_date: str | None = None) -> List[WeatherInfo]:
        if self._is_mock():
            return self._mock_weather(days=days, start_date=start_date)

        try:
            response = httpx.get(
                "https://restapi.amap.com/v3/weather/weatherInfo",
                params={
                    "key": self.settings.amap_api_key,
                    "output": "json",
                    "city": city,
                    "extensions": "all",
                },
                timeout=12,
            )
            response.raise_for_status()
            data = response.json()
            forecasts = data.get("forecasts", [])
            casts = forecasts[0].get("casts", []) if forecasts else []
            rows: List[WeatherInfo] = []
            for item in casts[:days]:
                rows.append(
                    WeatherInfo(
                        date=item.get("date", ""),
                        day_weather=item.get("dayweather", ""),
                        night_weather=item.get("nightweather", ""),
                        day_temp=int(item.get("daytemp", 0) or 0),
                        night_temp=int(item.get("nighttemp", 0) or 0),
                        wind_direction=item.get("daywind", ""),
                        wind_power=item.get("daypower", ""),
                    )
                )
            if rows:
                return rows
        except Exception as exc:
            print(f"[weather-tool-warning] real API failed, fallback to mock: {exc}")

        return self._mock_weather(days=days, start_date=start_date)

    @staticmethod
    def _mock_weather(days: int, start_date: str | None = None) -> List[WeatherInfo]:
        if start_date:
            cursor = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            cursor = datetime.now()

        rows: List[WeatherInfo] = []
        for idx in range(days):
            day_weather, night_weather, day_temp, night_temp = MOCK_WEATHER[idx % len(MOCK_WEATHER)]
            rows.append(
                WeatherInfo(
                    date=(cursor + timedelta(days=idx)).strftime("%Y-%m-%d"),
                    day_weather=day_weather,
                    night_weather=night_weather,
                    day_temp=day_temp,
                    night_temp=night_temp,
                    wind_direction="东南风",
                    wind_power="3级",
                )
            )
        return rows
