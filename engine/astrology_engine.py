"""Vedic chart via flatlib + Lahiri ayanamsa (sidereal, whole-sign houses)."""

from __future__ import annotations

from typing import Any

import swisseph as swe
from flatlib import const
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos

from engine import panchanga
from engine.dasha import parse_birth_datetime, vimshottari
from engine.vedic_tables import (
    GRAHA_SI,
    SIGN_LORDS,
    SIGNS_SI,
    dignity_of,
    nakshatra_of,
    navamsa_index,
)

SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

GRAHA_IDS = (
    const.SUN,
    const.MOON,
    const.MERCURY,
    const.VENUS,
    const.MARS,
    const.JUPITER,
    const.SATURN,
    const.NORTH_NODE,
    const.SOUTH_NODE,
)

GRAHA_NAMES = {
    const.SUN: "Sun",
    const.MOON: "Moon",
    const.MERCURY: "Mercury",
    const.VENUS: "Venus",
    const.MARS: "Mars",
    const.JUPITER: "Jupiter",
    const.SATURN: "Saturn",
    const.NORTH_NODE: "Rahu",
    const.SOUTH_NODE: "Ketu",
}


def _norm360(lon: float) -> float:
    return lon % 360.0


def _sign_and_degree(lon: float) -> tuple[str, float, int]:
    lon = _norm360(lon)
    idx = int(lon // 30)
    return SIGNS[idx], lon % 30.0, idx


def _whole_sign_house(planet_sign_idx: int, lagna_sign_idx: int) -> int:
    return (planet_sign_idx - lagna_sign_idx) % 12 + 1


def _latlon_to_geopos(lat: float, lon: float) -> GeoPos:
    ns = "n" if lat >= 0 else "s"
    ew = "e" if lon >= 0 else "w"
    alat, alon = abs(lat), abs(lon)
    lat_s = f"{int(alat)}{ns}{int(round((alat % 1) * 60)):02d}"
    lon_s = f"{int(alon)}{ew}{int(round((alon % 1) * 60)):02d}"
    return GeoPos(lat_s, lon_s)


class AstrologyEngine:
    def build_chart(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "")
        birth_date = str(payload["birth_date"]).strip()
        birth_time = str(payload["birth_time"]).strip()
        tz = str(payload.get("tz") or "+05:30")
        lat = float(payload["lat"])
        lon = float(payload["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Invalid latitude/longitude")
        if len(birth_time) == 5:
            birth_time = birth_time + ":00"

        date = Datetime(birth_date, birth_time, tz)
        pos = _latlon_to_geopos(lat, lon)
        tropical = Chart(date, pos, hsys=const.HOUSES_WHOLE_SIGN)

        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayanamsa = float(swe.get_ayanamsa_ut(date.jd))

        asc_trop = float(tropical.getAngle(const.ASC).lon)
        lagna_lon = _norm360(asc_trop - ayanamsa)
        lagna_sign, lagna_deg, lagna_idx = _sign_and_degree(lagna_lon)

        planets: list[dict[str, Any]] = []
        moon_lon = 0.0
        sun_lon = 0.0
        for oid in GRAHA_IDS:
            obj = tropical.getObject(oid)
            sid_lon = _norm360(float(obj.lon) - ayanamsa)
            sign, deg, sidx = _sign_and_degree(sid_lon)
            speed = float(getattr(obj, "lonspeed", 0.0) or 0.0)
            graha = GRAHA_NAMES[oid]
            is_node = oid in (const.NORTH_NODE, const.SOUTH_NODE)
            if graha == "Moon":
                moon_lon = sid_lon
            elif graha == "Sun":
                sun_lon = sid_lon
            nak = nakshatra_of(sid_lon)
            nav_idx = navamsa_index(sid_lon)
            dignity = "neutral" if is_node else dignity_of(graha, sidx)
            planets.append(
                {
                    "name": graha,
                    "name_si": GRAHA_SI[graha],
                    "sign": sign,
                    "sign_si": SIGNS_SI[sidx],
                    "sign_index": sidx,
                    "sign_lord": SIGN_LORDS[sidx],
                    "navamsa_sign": SIGNS[nav_idx],
                    "navamsa_sign_si": SIGNS_SI[nav_idx],
                    "navamsa_sign_index": nav_idx,
                    "house": _whole_sign_house(sidx, lagna_idx),
                    "degree": round(deg, 6),
                    "longitude": round(sid_lon, 6),
                    "retrograde": speed < 0 and not is_node,
                    "nakshatra": nak["name"],
                    "nakshatra_si": nak["name_si"],
                    "nakshatra_pada": nak["pada"],
                    "nakshatra_lord": nak["lord"],
                    "dignity": dignity,
                }
            )

        houses: dict[str, Any] = {}
        for i in range(12):
            sidx = (lagna_idx + i) % 12
            houses[str(i + 1)] = {
                "sign": SIGNS[sidx],
                "sign_si": SIGNS_SI[sidx],
                "lord": SIGN_LORDS[sidx],
                "cusp": round(float(sidx * 30), 6),
            }

        lagna_nak = nakshatra_of(lagna_lon)
        moon_nak = nakshatra_of(moon_lon)
        lagna_nav_idx = navamsa_index(lagna_lon)
        birth_dt = parse_birth_datetime(birth_date, birth_time)
        dasha = vimshottari(moon_lon, birth_dt)
        panch = panchanga.build(sun_lon, moon_lon, int(moon_nak["index"]), birth_dt)

        return {
            "native": {
                "name": name,
                "datetime_local": f"{birth_date} {birth_time}",
                "tz": tz,
                "lat": lat,
                "lon": lon,
            },
            "settings": {
                "tradition": "vedic",
                "ayanamsa": "lahiri",
                "ayanamsa_degree": round(ayanamsa, 6),
                "house_system": "whole_sign",
            },
            "ascendant": {
                "sign": lagna_sign,
                "sign_si": SIGNS_SI[lagna_idx],
                "sign_index": lagna_idx,
                "navamsa_sign": SIGNS[lagna_nav_idx],
                "navamsa_sign_si": SIGNS_SI[lagna_nav_idx],
                "navamsa_sign_index": lagna_nav_idx,
                "lord": SIGN_LORDS[lagna_idx],
                "degree": round(lagna_deg, 6),
                "longitude": round(lagna_lon, 6),
                "nakshatra": lagna_nak["name"],
                "nakshatra_si": lagna_nak["name_si"],
                "nakshatra_pada": lagna_nak["pada"],
            },
            "moon_nakshatra": {
                "name": moon_nak["name"],
                "name_si": moon_nak["name_si"],
                "pada": moon_nak["pada"],
                "lord": moon_nak["lord"],
            },
            "planets": planets,
            "houses": houses,
            "panchanga": panch,
            "dasha": dasha,
        }
