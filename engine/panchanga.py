# -*- coding: utf-8 -*-
"""Panchanga elements derived from the sidereal Sun and Moon: tithi, yoga, karana, vara, gana."""

from __future__ import annotations

from datetime import datetime
from typing import Any

TITHI_NAMES_SI: tuple[str, ...] = (
    "පෑලවිය",
    "දියවක",
    "තියවක",
    "සිව්වක",
    "පස්වක",
    "සැටවක",
    "සත්වක",
    "අටවක",
    "නවවක",
    "දසවක",
    "එකොළොස්වක",
    "දොළොස්වක",
    "තෙළෙස්වක",
    "තුදුස්වක",
    "පසළොස්වක",
)

VARA_SI: tuple[str, ...] = (
    "ඉරිදා",
    "සඳුදා",
    "අඟහරුවාදා",
    "බදාදා",
    "බ්‍රහස්පතින්දා",
    "සිකුරාදා",
    "සෙනසුරාදා",
)

YOGA_NAMES: tuple[str, ...] = (
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarman",
    "Dhriti",
    "Shula",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyan",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
)

MOVABLE_KARANAS: tuple[str, ...] = (
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Gara",
    "Vanija",
    "Vishti",
)

FIXED_KARANAS: tuple[str, ...] = ("Shakuni", "Chatushpada", "Naga")

# Nakshatra index (0-based) -> gana.
_DEVA = frozenset({0, 4, 6, 7, 12, 14, 16, 21, 26})
_MANUSHYA = frozenset({1, 3, 5, 10, 11, 19, 20, 24, 25})

GANA_SI = {"deva": "දේව", "manushya": "මනුෂ්‍ය", "rakshasa": "රාක්ෂස"}


def gana_of(nakshatra_index: int) -> str:
    """nakshatra_index is 0-based."""
    if nakshatra_index in _DEVA:
        return "deva"
    if nakshatra_index in _MANUSHYA:
        return "manushya"
    return "rakshasa"


def tithi_of(sun_lon: float, moon_lon: float) -> dict[str, Any]:
    """30 tithis across the lunar month, from the Moon's elongation from the Sun."""
    diff = (moon_lon - sun_lon) % 360.0
    index = int(diff // 12.0)  # 0..29
    within = index % 15  # 0..14
    name = TITHI_NAMES_SI[within]
    if index < 15:
        label = f"පුර {name}"
        paksha = "පුර"
    else:
        label = "අමාවක" if within == 14 else f"අව {name}"
        paksha = "අව"
    return {"index": index + 1, "paksha": paksha, "name_si": label}


def yoga_of(sun_lon: float, moon_lon: float) -> dict[str, Any]:
    total = (sun_lon + moon_lon) % 360.0
    index = int(total // (360.0 / 27.0)) % 27
    return {"index": index + 1, "name": YOGA_NAMES[index]}


def karana_of(sun_lon: float, moon_lon: float) -> dict[str, Any]:
    """60 half-tithis: one opening karana, seven movable repeated eight times, three closing."""
    diff = (moon_lon - sun_lon) % 360.0
    half = int(diff // 6.0)  # 0..59
    if half == 0:
        name = "Kimstughna"
    elif half >= 57:
        name = FIXED_KARANAS[half - 57]
    else:
        name = MOVABLE_KARANAS[(half - 1) % 7]
    return {"index": half + 1, "name": name}


def vara_of(birth_dt: datetime) -> dict[str, Any]:
    """Civil weekday of the birth date (not sunrise-adjusted)."""
    index = (birth_dt.weekday() + 1) % 7  # Monday=0 -> Sunday=0
    return {"index": index + 1, "name_si": VARA_SI[index]}


def build(
    sun_lon: float,
    moon_lon: float,
    moon_nakshatra_index: int,
    birth_dt: datetime,
) -> dict[str, Any]:
    gana = gana_of(moon_nakshatra_index - 1)
    return {
        "vara": vara_of(birth_dt),
        "tithi": tithi_of(sun_lon, moon_lon),
        "yoga": yoga_of(sun_lon, moon_lon),
        "karana": karana_of(sun_lon, moon_lon),
        "gana": {"name": gana, "name_si": GANA_SI[gana]},
    }
