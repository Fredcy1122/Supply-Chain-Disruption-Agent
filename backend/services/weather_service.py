"""
Historical weather from Open-Meteo for shipment investigations.

The shipment data is from 2017 to 2018, so the service retrieves the
weather that was observed at the time, never current conditions.
Every failure is raised as WeatherServiceError so the agent can treat
weather as optional evidence.
"""

from datetime import date
from functools import lru_cache
from typing import Any

import requests

from backend.config import settings
from backend.exceptions import WeatherServiceError


# ============================================================
# DESTINATION COUNTRIES
# ============================================================


# ISO 3166-1 alpha-2 codes for the Spanish country names used in
# shipment_tool_data.csv. The geocoder filters by code, which prevents
# matches on same-named towns in other countries. Unknown names are
# rejected rather than guessed.
COUNTRY_CODES = {
    "Afganistán": "AF",
    "Alemania": "DE",
    "Australia": "AU",
    "Austria": "AT",
    "Bangladés": "BD",
    "Bélgica": "BE",
    "Brasil": "BR",
    "Bután": "BT",
    "Camboya": "KH",
    "China": "CN",
    "Chipre": "CY",
    "Corea del Sur": "KR",
    "Dinamarca": "DK",
    "España": "ES",
    "Filipinas": "PH",
    "Finlandia": "FI",
    "Francia": "FR",
    "Grecia": "GR",
    "Hong Kong": "HK",
    "India": "IN",
    "Indonesia": "ID",
    "Irlanda": "IE",
    "Italia": "IT",
    "Japón": "JP",
    "Laos": "LA",
    "Luxemburgo": "LU",
    "Malasia": "MY",
    "Mongolia": "MN",
    "Myanmar (Birmania)": "MM",
    "Nepal": "NP",
    "Noruega": "NO",
    "Países Bajos": "NL",
    "Pakistán": "PK",
    "Papúa Nueva Guinea": "PG",
    "Portugal": "PT",
    "Reino Unido": "GB",
    "Singapur": "SG",
    "Sri Lanka": "LK",
    "Suecia": "SE",
    "Suiza": "CH",
    "Tailandia": "TH",
    "Taiwán": "TW",
    "Vietnam": "VN",
}


# ============================================================
# WMO WEATHER CODES
# ============================================================


# WMO weather interpretation codes, as documented by Open-Meteo.
WEATHER_CODE_DESCRIPTIONS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snowfall",
    73: "moderate snowfall",
    75: "heavy snowfall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}

# Severity follows the intensity in the WMO code itself: heavy, violent
# and thunderstorm conditions are high; moderate, dense, freezing and
# fog conditions are moderate; everything else is low.
HIGH_SEVERITY_CODES = {65, 67, 75, 82, 86, 95, 96, 99}
MODERATE_SEVERITY_CODES = {45, 48, 53, 55, 56, 57, 63, 66, 73, 81, 85}


def describe_weather_code(code: int) -> str:
    return WEATHER_CODE_DESCRIPTIONS.get(code, f"WMO weather code {code}")


def classify_weather_severity(code: int) -> str:
    if code in HIGH_SEVERITY_CODES:
        return "high"
    if code in MODERATE_SEVERITY_CODES:
        return "moderate"
    return "low"


# ============================================================
# OPEN-METEO REQUESTS
# ============================================================


def get_country_code(country_name: str) -> str:
    """
    Return the ISO country code for a destination country name from
    the shipment dataset.
    """
    country_code = COUNTRY_CODES.get(country_name.strip())

    if country_code is None:
        raise WeatherServiceError(
            "No ISO country code is configured for destination "
            f"country '{country_name}'."
        )

    return country_code


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(
            url,
            params=params,
            timeout=settings.weather_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

    except requests.Timeout as exc:
        raise WeatherServiceError(
            "Open-Meteo did not respond within "
            f"{settings.weather_timeout_seconds:g} seconds."
        ) from exc

    except (requests.RequestException, ValueError) as exc:
        raise WeatherServiceError(
            f"Open-Meteo request failed: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise WeatherServiceError(
            "Open-Meteo returned an unexpected response: expected a "
            f"JSON object, got {type(data).__name__}."
        )

    return data


# Results are cached because the same destination and window recur
# across investigations; failures are not cached and will be retried.
@lru_cache(maxsize=256)
def geocode_city(city: str, country_code: str) -> dict[str, Any]:
    """
    Find a city's coordinates within one country.

    The geocoder's top-ranked match is used. Callers must not modify
    the returned dictionary because it is cached.
    """
    data = _get_json(
        settings.weather_geocoding_url,
        {
            "name": city,
            "countryCode": country_code,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )

    results = data.get("results") or []

    if not results:
        raise WeatherServiceError(
            f"No geocoding match was found for '{city}' "
            f"in country {country_code}."
        )

    match = results[0]

    try:
        return {
            "name": str(match["name"]),
            "country": str(match.get("country") or country_code),
            "latitude": float(match["latitude"]),
            "longitude": float(match["longitude"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherServiceError(
            f"Open-Meteo returned an invalid geocoding result for '{city}'."
        ) from exc


@lru_cache(maxsize=256)
def get_daily_weather(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> tuple[dict[str, Any], ...]:
    """
    Retrieve observed daily precipitation, maximum wind speed and WMO
    weather code for each day from start_date to end_date inclusive.

    Days are aggregated in the location's local time zone.
    """
    data = _get_json(
        settings.weather_api_base_url,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "precipitation_sum,wind_speed_10m_max,weather_code",
            "precipitation_unit": "mm",
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        },
    )

    try:
        daily = data["daily"]
        days = list(
            zip(
                daily["time"],
                daily["precipitation_sum"],
                daily["wind_speed_10m_max"],
                daily["weather_code"],
                strict=True,
            )
        )
        if not days:
            raise ValueError("no days returned")

        return tuple(
            {
                "date": str(day),
                "precipitation_mm": float(precipitation),
                "max_wind_speed_kmh": float(wind_speed),
                "weather_code": int(code),
            }
            for day, precipitation, wind_speed, code in days
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherServiceError(
            "Open-Meteo returned incomplete daily weather for "
            f"{start_date} to {end_date}: {exc}"
        ) from exc
