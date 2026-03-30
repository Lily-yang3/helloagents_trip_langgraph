"""Rule-based parser for user trip requests with multi-turn merge support."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.schemas.trip import ParsedTripRequest


COMMON_CITIES = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "南京",
    "苏州",
    "成都",
    "重庆",
    "西安",
    "武汉",
    "长沙",
    "青岛",
    "厦门",
    "三亚",
    "昆明",
    "大理",
    "丽江",
    "哈尔滨",
    "天津",
    "福州",
    "郑州",
    "洛阳",
    "桂林",
    "珠海",
]

TRANSPORT_KEYWORDS = {
    "地铁": "地铁",
    "打车": "打车",
    "出租": "打车",
    "步行": "步行",
    "公交": "公交",
    "自驾": "自驾",
}

ACCOMMODATION_KEYWORDS = ["经济型酒店", "舒适型酒店", "豪华酒店", "民宿", "青旅", "酒店"]

PREFERENCE_KEYWORDS = [
    "美食",
    "历史",
    "文化",
    "博物馆",
    "自然",
    "风景",
    "艺术",
    "购物",
    "亲子",
    "夜景",
    "徒步",
    "海边",
]

PACE_KEYWORDS = {
    "慢节奏": "relaxed",
    "悠闲": "relaxed",
    "轻松": "relaxed",
    "紧凑": "dense",
    "高密度": "dense",
    "特种兵": "dense",
    "适中": "balanced",
}

MANDATORY_FIELDS = {
    "city": "目的地城市",
    "start_date": "出发日期",
    "travel_days": "旅行天数",
    "total_budget": "总预算",
}


class RequestParser:
    """Merge parser output into current request state for multi-turn clarification."""

    def parse(self, message: str, previous: Dict[str, object] | None = None) -> ParsedTripRequest:
        text = (message or "").strip()
        data: Dict[str, object] = dict(previous or {})

        city = self._extract_city(text)
        if city:
            data["city"] = city

        travel_days = self._extract_travel_days(text)
        if travel_days:
            data["travel_days"] = travel_days

        total_budget = self._extract_budget(text)
        if total_budget:
            data["total_budget"] = total_budget

        transportation = self._extract_transportation(text)
        if transportation:
            data["transportation"] = transportation

        accommodation = self._extract_accommodation(text)
        if accommodation:
            data["accommodation"] = accommodation

        pace_preference = self._extract_pace(text)
        if pace_preference:
            data["pace_preference"] = pace_preference

        prefs = self._extract_preferences(text)
        if prefs:
            data["preferences"] = self._merge_unique_list(data.get("preferences"), prefs)

        avoid_tags = self._extract_avoid_tags(text)
        if avoid_tags:
            data["avoid_tags"] = self._merge_unique_list(data.get("avoid_tags"), avoid_tags)

        dates = self._extract_dates(text)
        if len(dates) >= 2:
            start_date = min(dates[0], dates[1])
            end_date = max(dates[0], dates[1])
            data["start_date"] = start_date.strftime("%Y-%m-%d")
            data["end_date"] = end_date.strftime("%Y-%m-%d")
            data["travel_days"] = (end_date - start_date).days + 1
        elif len(dates) == 1:
            data["start_date"] = dates[0].strftime("%Y-%m-%d")

        self._normalize_dates(data)

        if text:
            prev_text = str(data.get("free_text_input") or "")
            data["free_text_input"] = f"{prev_text}\n{text}".strip()

        return ParsedTripRequest.model_validate(data)

    def identify_missing_fields(self, parsed: ParsedTripRequest) -> List[str]:
        missing: List[str] = []
        payload = parsed.model_dump()
        for key in MANDATORY_FIELDS:
            value = payload.get(key)
            if value in (None, "", []):
                missing.append(key)
        return missing

    def build_missing_labels(self, missing_fields: List[str]) -> List[str]:
        labels: List[str] = []
        for key in missing_fields:
            labels.append(MANDATORY_FIELDS.get(key, key))
        return labels

    @staticmethod
    def _merge_unique_list(current: object, incoming: List[str]) -> List[str]:
        current_list = current if isinstance(current, list) else []
        result = list(dict.fromkeys([*current_list, *incoming]))
        return [item for item in result if item]

    @staticmethod
    def _extract_city(text: str) -> Optional[str]:
        for city in COMMON_CITIES:
            if city in text:
                return city

        patterns = [
            r"去([\u4e00-\u9fa5]{2,8})(?:玩|旅游|旅行|出差|逛)",
            r"到([\u4e00-\u9fa5]{2,8})(?:玩|旅游|旅行)",
            r"([\u4e00-\u9fa5]{2,8})市",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            city = match.group(1).strip()
            if city.endswith("市"):
                city = city[:-1]
            if 1 < len(city) <= 8:
                return city
        return None

    @staticmethod
    def _extract_dates(text: str) -> List[datetime]:
        rows: List[datetime] = []

        full_date_pattern = r"(20\d{2})[\-/年\.](\d{1,2})[\-/月\.](\d{1,2})日?"
        for y, m, d in re.findall(full_date_pattern, text):
            try:
                rows.append(datetime(int(y), int(m), int(d)))
            except ValueError:
                continue

        md_pattern = r"(\d{1,2})月(\d{1,2})日"
        current_year = datetime.now().year
        for m, d in re.findall(md_pattern, text):
            try:
                rows.append(datetime(current_year, int(m), int(d)))
            except ValueError:
                continue

        dedup: List[datetime] = []
        seen = set()
        for item in sorted(rows):
            key = item.strftime("%Y-%m-%d")
            if key in seen:
                continue
            seen.add(key)
            dedup.append(item)
        return dedup

    @staticmethod
    def _extract_travel_days(text: str) -> Optional[int]:
        match = re.search(r"(\d{1,2})\s*(?:天|日)", text)
        if not match:
            return None
        value = int(match.group(1))
        if 1 <= value <= 30:
            return value
        return None

    @staticmethod
    def _extract_budget(text: str) -> Optional[int]:
        budget_patterns = [
            r"预算[^\d]{0,8}(\d{3,6})",
            r"总预算[^\d]{0,8}(\d{3,6})",
            r"(\d{3,6})\s*元",
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            value = int(match.group(1))
            if 300 <= value <= 500000:
                return value
        return None

    @staticmethod
    def _extract_transportation(text: str) -> Optional[str]:
        for key, value in TRANSPORT_KEYWORDS.items():
            if key in text:
                return value
        return None

    @staticmethod
    def _extract_accommodation(text: str) -> Optional[str]:
        for token in ACCOMMODATION_KEYWORDS:
            if token in text:
                return token
        return None

    @staticmethod
    def _extract_preferences(text: str) -> List[str]:
        return [token for token in PREFERENCE_KEYWORDS if token in text]

    @staticmethod
    def _extract_pace(text: str) -> Optional[str]:
        for key, value in PACE_KEYWORDS.items():
            if key in text:
                return value
        return None

    @staticmethod
    def _extract_avoid_tags(text: str) -> List[str]:
        avoid_tags: List[str] = []
        for trigger in ["不喜欢", "不要", "避免"]:
            if trigger not in text:
                continue
            tail = text.split(trigger, 1)[1]
            tokens = re.split(r"[，,。；;、\s]+", tail)
            avoid_tags.extend([token.strip() for token in tokens if token.strip()][:3])
        return avoid_tags

    @staticmethod
    def _normalize_dates(data: Dict[str, object]) -> None:
        start_raw = data.get("start_date")
        end_raw = data.get("end_date")
        days_raw = data.get("travel_days")

        start_date = RequestParser._parse_date_str(start_raw)
        end_date = RequestParser._parse_date_str(end_raw)
        days = int(days_raw) if isinstance(days_raw, int) else None

        if start_date and end_date and (not days or days <= 0):
            data["travel_days"] = (end_date - start_date).days + 1
            days = data["travel_days"]

        if start_date and days and not end_date:
            data["end_date"] = (start_date + timedelta(days=days - 1)).strftime("%Y-%m-%d")
            return

        if start_date and end_date and days:
            normalized_days = (end_date - start_date).days + 1
            if normalized_days > 0 and normalized_days != days:
                data["travel_days"] = normalized_days

    @staticmethod
    def _parse_date_str(value: object) -> Optional[datetime]:
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
