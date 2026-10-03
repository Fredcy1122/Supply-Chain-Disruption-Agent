from datetime import date

import pandas as pd
import pytest
import requests

from backend.config import settings
from backend.exceptions import BackendServiceError, WeatherServiceError
from backend.services import weather_service
from backend.services.weather_service import (
    classify_weather_severity,
    describe_weather_code,
    geocode_city,
    get_country_code,
    get_daily_weather,
)
from backend.services.shipment_service import DATA_PATH


GEOCODING_RESPONSE = {
    "results": [
        {
            "name": "Vassouras",
            "country": "Brazil",
            "country_code": "BR",
            "latitude": -22.4036,
            "longitude": -43.6625,
        }
    ]
}

ARCHIVE_RESPONSE = {
    "daily": {
        "time": ["2017-06-14", "2017-06-15"],
        "precipitation_sum": [8.9, 0.3],
        "wind_speed_10m_max": [17.9, 12.8],
        "weather_code": [61, 51],
    }
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error")

    def json(self):
        return self.payload


class CallLog(list):
    """Recorded requests, plus the canned response for each URL."""

    responses: dict


@pytest.fixture
def http_calls(monkeypatch):
    """
    Answer Open-Meteo requests from canned payloads and record them.
    """
    calls = CallLog()
    calls.responses = {
        settings.weather_geocoding_url: FakeResponse(GEOCODING_RESPONSE),
        settings.weather_api_base_url: FakeResponse(ARCHIVE_RESPONSE),
    }

    def fake_get(url, params, timeout):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return calls.responses[url]

    monkeypatch.setattr(weather_service.requests, "get", fake_get)
    return calls


def raise_on_get(exception):
    def fake_get(url, params, timeout):
        raise exception

    return fake_get


# ============================================================
# COUNTRY MAPPING
# ============================================================


@pytest.mark.parametrize(
    ("country_name", "country_code"),
    [
        ("Brasil", "BR"),
        ("Países Bajos", "NL"),
        ("Reino Unido", "GB"),
        ("Myanmar (Birmania)", "MM"),
        (" Francia ", "FR"),
    ],
)
def test_get_country_code_maps_dataset_names(country_name, country_code):
    assert get_country_code(country_name) == country_code


def test_get_country_code_rejects_unknown_country():
    with pytest.raises(WeatherServiceError, match="Atlantis"):
        get_country_code("Atlantis")


def test_every_destination_country_in_dataset_is_mapped():
    countries = pd.read_csv(
        DATA_PATH,
        usecols=["destination_country"],
    )["destination_country"].unique()

    assert set(countries) <= set(weather_service.COUNTRY_CODES)


def test_weather_service_error_uses_backend_hierarchy():
    assert issubclass(WeatherServiceError, BackendServiceError)


# ============================================================
# GEOCODING
# ============================================================


def test_geocode_city_filters_by_country_and_parses_match(http_calls):
    location = geocode_city("Vassouras", "BR")

    assert location == {
        "name": "Vassouras",
        "country": "Brazil",
        "latitude": -22.4036,
        "longitude": -43.6625,
    }
    request = http_calls[0]
    assert request["url"] == settings.weather_geocoding_url
    assert request["params"]["name"] == "Vassouras"
    assert request["params"]["countryCode"] == "BR"
    assert request["timeout"] == settings.weather_timeout_seconds


def test_geocode_city_caches_repeated_lookups(http_calls):
    geocode_city("Vassouras", "BR")
    geocode_city("Vassouras", "BR")

    assert len(http_calls) == 1


def test_geocode_city_without_match_raises(http_calls):
    http_calls.responses[settings.weather_geocoding_url] = FakeResponse({})

    with pytest.raises(WeatherServiceError, match="No geocoding match"):
        geocode_city("Nowhere", "BR")


# ============================================================
# HISTORICAL WEATHER
# ============================================================


def test_get_daily_weather_parses_archive_response(http_calls):
    days = get_daily_weather(
        -22.4036, -43.6625, date(2017, 6, 14), date(2017, 6, 15)
    )

    assert days == (
        {
            "date": "2017-06-14",
            "precipitation_mm": 8.9,
            "max_wind_speed_kmh": 17.9,
            "weather_code": 61,
        },
        {
            "date": "2017-06-15",
            "precipitation_mm": 0.3,
            "max_wind_speed_kmh": 12.8,
            "weather_code": 51,
        },
    )
    params = http_calls[0]["params"]
    assert http_calls[0]["url"] == settings.weather_api_base_url
    assert params["start_date"] == "2017-06-14"
    assert params["end_date"] == "2017-06-15"
    assert params["daily"] == (
        "precipitation_sum,wind_speed_10m_max,weather_code"
    )


@pytest.mark.parametrize(
    "daily",
    [
        None,
        {"time": ["2017-06-14"], "precipitation_sum": [1.0]},
        {
            "time": ["2017-06-14"],
            "precipitation_sum": [None],
            "wind_speed_10m_max": [10.0],
            "weather_code": [3],
        },
        {
            "time": [],
            "precipitation_sum": [],
            "wind_speed_10m_max": [],
            "weather_code": [],
        },
    ],
)
def test_get_daily_weather_rejects_incomplete_response(http_calls, daily):
    http_calls.responses[settings.weather_api_base_url] = FakeResponse(
        {"daily": daily}
    )

    with pytest.raises(WeatherServiceError, match="incomplete daily weather"):
        get_daily_weather(0.0, 0.0, date(2017, 6, 14), date(2017, 6, 14))


# ============================================================
# HTTP FAILURES
# ============================================================


def test_http_error_raises_weather_service_error(http_calls):
    http_calls.responses[settings.weather_geocoding_url] = FakeResponse(
        {}, status_code=503
    )

    with pytest.raises(WeatherServiceError, match="503"):
        geocode_city("Vassouras", "BR")


def test_timeout_raises_weather_service_error(monkeypatch):
    monkeypatch.setattr(
        weather_service.requests,
        "get",
        raise_on_get(requests.Timeout("read timed out")),
    )

    with pytest.raises(WeatherServiceError, match="did not respond within 10"):
        geocode_city("Vassouras", "BR")


def test_connection_error_raises_weather_service_error(monkeypatch):
    monkeypatch.setattr(
        weather_service.requests,
        "get",
        raise_on_get(requests.ConnectionError("connection refused")),
    )

    with pytest.raises(WeatherServiceError, match="connection refused"):
        get_daily_weather(0.0, 0.0, date(2017, 6, 14), date(2017, 6, 14))


def test_non_object_json_response_raises_weather_service_error(http_calls):
    http_calls.responses[settings.weather_geocoding_url] = FakeResponse([])

    with pytest.raises(WeatherServiceError, match="expected a JSON object"):
        geocode_city("Vassouras", "BR")


def test_failed_lookup_is_not_cached(http_calls):
    http_calls.responses[settings.weather_geocoding_url] = FakeResponse(
        {}, status_code=503
    )
    with pytest.raises(WeatherServiceError):
        geocode_city("Vassouras", "BR")

    http_calls.responses[settings.weather_geocoding_url] = FakeResponse(
        GEOCODING_RESPONSE
    )

    assert geocode_city("Vassouras", "BR")["name"] == "Vassouras"


# ============================================================
# WEATHER CODES
# ============================================================


@pytest.mark.parametrize(
    ("code", "description", "severity"),
    [
        (0, "clear sky", "low"),
        (61, "slight rain", "low"),
        (63, "moderate rain", "moderate"),
        (45, "fog", "moderate"),
        (65, "heavy rain", "high"),
        (95, "thunderstorm", "high"),
        (42, "WMO weather code 42", "low"),
    ],
)
def test_weather_code_description_and_severity(code, description, severity):
    assert describe_weather_code(code) == description
    assert classify_weather_severity(code) == severity
