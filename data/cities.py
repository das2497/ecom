"""Sri Lankan city presets (WGS84). Default: Negombo."""

from __future__ import annotations

from typing import TypedDict


class City(TypedDict):
    name: str
    lat: float
    lon: float


CITIES: list[City] = [
    {"name": "Negombo", "lat": 7.2083, "lon": 79.8358},
    {"name": "Colombo", "lat": 6.9271, "lon": 79.8612},
    {"name": "Kandy", "lat": 7.2906, "lon": 80.6337},
    {"name": "Galle", "lat": 6.0535, "lon": 80.2210},
    {"name": "Jaffna", "lat": 9.6615, "lon": 80.0255},
    {"name": "Anuradhapura", "lat": 8.3114, "lon": 80.4037},
    {"name": "Batticaloa", "lat": 7.7102, "lon": 81.6853},
    {"name": "Matara", "lat": 5.9549, "lon": 80.5550},
    {"name": "Kurunegala", "lat": 7.4863, "lon": 80.3623},
    {"name": "Ratnapura", "lat": 6.7056, "lon": 80.3847},
]

DEFAULT_CITY_NAME = "Negombo"

CITIES_BY_NAME: dict[str, City] = {c["name"]: c for c in CITIES}


def get_city(name: str) -> City:
    if name not in CITIES_BY_NAME:
        raise KeyError(f"Unknown city: {name}")
    return CITIES_BY_NAME[name]


def default_city() -> City:
    return get_city(DEFAULT_CITY_NAME)
