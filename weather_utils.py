import requests
import os
import streamlit as st
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class WeatherObservation:
    city: str
    lat: float
    lon: float
    observed_at: datetime
    temp_c: float
    feels_like_c: float
    humidity: int
    wind_speed: float
    description: str
    condition: str
    icon: str

@st.cache_data(ttl=600)
def get_weather(city: str, api_key: str) -> Optional[WeatherObservation]:
    """
    Fetches weather data for a given city from OpenWeatherMap API.
    """
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "kr"
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        return WeatherObservation(
            city=data["name"],
            lat=data["coord"]["lat"],
            lon=data["coord"]["lon"],
            observed_at=datetime.fromtimestamp(data["dt"]),
            temp_c=data["main"]["temp"],
            feels_like_c=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            wind_speed=data["wind"]["speed"],
            description=data["weather"][0]["description"],
            condition=data["weather"][0]["main"],
            icon=data["weather"][0]["icon"]
        )
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None
