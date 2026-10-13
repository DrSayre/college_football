import pytest

import cfbd


def test_missing_key_is_actionable(monkeypatch):
    monkeypatch.delenv("CFBD_API_KEY", raising=False)
    with pytest.raises(cfbd.DataError, match="Secrets"):
        cfbd.get("/records", year=2026)


def test_only_completed_conference_weeks_fetched(monkeypatch):
    calls = []
    def fake_get(path, **params):
        calls.append((path, params))
        if path == "/records":
            return []
        if path == "/games":
            if params["seasonType"] == "postseason":
                return []
            return [
                {"completed": True, "conferenceGame": True, "week": 3, "seasonType": "regular"},
                {"completed": True, "conferenceGame": True, "week": 3, "seasonType": "regular"},
                {"completed": False, "conferenceGame": True, "week": 4},
                {"completed": True, "conferenceGame": False, "week": 1},
            ]
        return [{"id": 123, "teams": []}]
    monkeypatch.setattr(cfbd, "get", fake_get)
    _, _, stats = cfbd.load_season(2026)
    assert stats == [{"id": 123, "teams": []}]
    assert [(path, params) for path, params in calls if path == "/games/teams"] == [
        ("/games/teams", {"year": 2026, "seasonType": "regular", "week": 3})]
