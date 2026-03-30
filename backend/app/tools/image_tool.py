"""Attraction image resolver with Unsplash lookup and deterministic SVG fallback."""

from __future__ import annotations

from typing import Iterable
from urllib.parse import quote

import httpx

from app.core.config import get_settings


CATEGORY_QUERY_MAP = {
    "museum": "museum architecture",
    "culture": "historic street travel",
    "park": "city park landscape",
    "art": "art museum gallery",
    "landmark": "famous landmark skyline",
    "history": "ancient architecture travel",
    "outdoor": "riverwalk outdoors travel",
    "attraction": "travel destination",
}

CATEGORY_COLOR_MAP = {
    "museum": ("#183a5b", "#376996"),
    "culture": ("#7d4b22", "#c98737"),
    "park": ("#195f44", "#47a36d"),
    "art": ("#5c2b73", "#a164bf"),
    "landmark": ("#704b16", "#d0a14d"),
    "history": ("#4f3422", "#986d43"),
    "outdoor": ("#175a68", "#48a4bb"),
    "attraction": ("#204d4f", "#4b8f93"),
}


class ImageTool:
    """Resolve attraction images for frontend presentation.

    When Unsplash is configured, fetch a matching landscape image.
    Otherwise, return a themed SVG placeholder so the UI still looks complete.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._cache: dict[str, str] = {}

    def get_attraction_image(
        self,
        city: str,
        attraction_name: str,
        category: str,
        tags: Iterable[str] | None = None,
    ) -> str:
        cache_key = f"{city}|{attraction_name}|{category}|{'/'.join(tags or [])}".lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        image_url = self._search_unsplash(city=city, attraction_name=attraction_name, category=category, tags=tags)
        if not image_url:
            image_url = self._build_placeholder(city=city, attraction_name=attraction_name, category=category)

        self._cache[cache_key] = image_url
        return image_url

    def _search_unsplash(
        self,
        city: str,
        attraction_name: str,
        category: str,
        tags: Iterable[str] | None = None,
    ) -> str | None:
        if not self.settings.unsplash_access_key:
            return None

        query = self._build_query(city=city, attraction_name=attraction_name, category=category, tags=tags)
        try:
            response = httpx.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": query,
                    "orientation": "landscape",
                    "per_page": 1,
                    "content_filter": "high",
                },
                headers={
                    "Authorization": f"Client-ID {self.settings.unsplash_access_key}",
                    "Accept-Version": "v1",
                },
                timeout=8,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                return None
            urls = results[0].get("urls", {})
            return urls.get("regular") or urls.get("small") or urls.get("thumb")
        except Exception as exc:
            print(f"[image-tool-warning] unsplash lookup failed, fallback to placeholder: {exc}")
            return None

    def _build_query(
        self,
        city: str,
        attraction_name: str,
        category: str,
        tags: Iterable[str] | None = None,
    ) -> str:
        leading_tag = next(iter(tags or []), "")
        mapped_category = CATEGORY_QUERY_MAP.get(category, CATEGORY_QUERY_MAP["attraction"])
        # Prefer a broad travel-photo query so we are more likely to get a useful landscape image.
        return " ".join(part for part in [city, attraction_name, leading_tag, mapped_category] if part)

    def _build_placeholder(self, city: str, attraction_name: str, category: str) -> str:
        start_color, end_color = CATEGORY_COLOR_MAP.get(category, CATEGORY_COLOR_MAP["attraction"])
        badge = category.upper()[:10] if category else "TRAVEL"
        svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-label="{attraction_name}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{start_color}"/>
      <stop offset="100%" stop-color="{end_color}"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="720" fill="url(#g)" rx="36"/>
  <circle cx="1040" cy="120" r="160" fill="#ffffff18"/>
  <circle cx="160" cy="620" r="220" fill="#ffffff10"/>
  <rect x="72" y="72" width="210" height="54" rx="27" fill="#ffffff20"/>
  <text x="177" y="108" text-anchor="middle" font-size="26" font-family="Arial, sans-serif" fill="#ffffff" font-weight="700">{badge}</text>
  <text x="72" y="420" font-size="72" font-family="Arial, sans-serif" fill="#ffffff" font-weight="700">{city}</text>
  <text x="72" y="500" font-size="42" font-family="Arial, sans-serif" fill="#ffffff" font-weight="600">{attraction_name}</text>
  <text x="72" y="566" font-size="28" font-family="Arial, sans-serif" fill="#f3f7f7">Personalized Trip Highlight</text>
</svg>
""".strip()
        return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"
