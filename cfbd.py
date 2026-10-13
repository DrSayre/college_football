"""Small HTTPS client; credentials stay in memory and errors never expose them."""
import os
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class DataError(RuntimeError):
    pass


def get(path, **params):
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        raise DataError("Set CFBD_API_KEY securely in your environment’s Secrets settings, then restart the app.")
    with requests.Session() as session:
        retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
        session.mount("https://", HTTPAdapter(max_retries=retry))
        try:
            response = session.get("https://api.collegefootballdata.com" + path,
                                   params=params, timeout=45,
                                   headers={"accept": "application/json", "Authorization": "Bearer " + key})
            if response.status_code == 401:
                raise DataError("The API rejected authentication. Check your saved CFBD_API_KEY.")
            if response.status_code == 403:
                raise DataError("API access was denied. Check your account’s endpoint permissions and network settings.")
            if response.status_code == 429:
                raise DataError("API request limit reached. Wait before refreshing or check your account’s quota.")
            if not response.ok:
                raise DataError(f"College Football Data returned HTTP {response.status_code} for {path}.")
            payload = response.json()
            if not isinstance(payload, list):
                raise DataError(f"Unexpected API response for {path}; expected a list.")
            return payload
        except (requests.RequestException, ValueError) as from_error:
            raise DataError(f"Could not retrieve {path}. Check connectivity and try again.") from from_error


def load_season(year):
    records = get("/records", year=year)
    games = []
    for season_type in ("regular", "postseason"):
        games.extend(get("/games", year=year, seasonType=season_type))
    # Only weeks with finished conference games need yardage requests.
    periods = sorted({(g.get("seasonType", "regular"), g["week"])
                      for g in games if g.get("completed") and g.get("conferenceGame")})
    def fetch(period):
        season_type, week = period
        return get("/games/teams", year=year, seasonType=season_type, week=week)
    with ThreadPoolExecutor(max_workers=3) as pool:
        statistics = [g for result in pool.map(fetch, periods) for g in result]
    return records, games, statistics
