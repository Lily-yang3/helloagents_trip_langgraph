"""Trip planning schema definitions."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    longitude: float = Field(..., description="Longitude")
    latitude: float = Field(..., description="Latitude")


class Attraction(BaseModel):
    name: str
    address: str
    location: Location
    visit_duration: int = Field(default=120, ge=30, le=480)
    description: str = ""
    category: str = "attraction"
    rating: Optional[float] = None
    ticket_price: int = 0
    tags: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None


class Meal(BaseModel):
    type: str = Field(..., description="breakfast/lunch/dinner/snack")
    name: str
    address: Optional[str] = None
    description: str = ""
    estimated_cost: int = 0


class Hotel(BaseModel):
    name: str
    address: str = ""
    location: Optional[Location] = None
    price_range: str = ""
    rating: str = ""
    distance: str = ""
    type: str = ""
    estimated_cost: int = 0


class DayPlan(BaseModel):
    date: str
    day_index: int
    description: str
    transportation: str
    accommodation: str
    hotel: Optional[Hotel] = None
    attractions: List[Attraction] = Field(default_factory=list)
    meals: List[Meal] = Field(default_factory=list)


class WeatherInfo(BaseModel):
    date: str
    day_weather: str = ""
    night_weather: str = ""
    day_temp: int = 0
    night_temp: int = 0
    wind_direction: str = ""
    wind_power: str = ""


class Budget(BaseModel):
    total_attractions: int = 0
    total_hotels: int = 0
    total_meals: int = 0
    total_transportation: int = 0
    total: int = 0


class TripPlan(BaseModel):
    city: str
    start_date: str
    end_date: str
    days: List[DayPlan]
    weather_info: List[WeatherInfo] = Field(default_factory=list)
    overall_suggestions: str
    budget: Budget = Field(default_factory=Budget)
    personalization_explanation: List[str] = Field(default_factory=list)


class ParsedTripRequest(BaseModel):
    city: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    travel_days: Optional[int] = None
    total_budget: Optional[int] = None
    transportation: Optional[str] = None
    accommodation: Optional[str] = None
    preferences: List[str] = Field(default_factory=list)
    avoid_tags: List[str] = Field(default_factory=list)
    pace_preference: Optional[str] = None
    free_text_input: str = ""


class CandidateData(BaseModel):
    attractions: List[Attraction] = Field(default_factory=list)
    hotels: List[Hotel] = Field(default_factory=list)
    weather: List[WeatherInfo] = Field(default_factory=list)
    meals: List[Meal] = Field(default_factory=list)


class TripHistoryItem(BaseModel):
    id: str
    user_id: str
    session_id: str
    thread_id: str
    created_at: str
    assistant_message: str
    structured_plan: Optional[TripPlan] = None


class TripHistoryResponse(BaseModel):
    success: bool = True
    user_id: str
    items: List[TripHistoryItem] = Field(default_factory=list)
