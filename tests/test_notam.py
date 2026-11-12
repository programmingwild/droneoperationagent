import httpx
import pytest

from backend.app.tools import notam


@pytest.fixture(autouse=True)
def _clear_cache():
    notam.clear_cache()
    yield
    notam.clear_cache()


def test_online_metar_parsed(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert "/metar" in url
        class Resp:
            text = '[{"icaoId":"KJFK","wspd":18,"wgst":24,"fltcat":"MVFR"}]'
            def raise_for_status(self):
                pass
            def json(self):
                return [{"icaoId": "KJFK", "wspd": 18, "wgst": 24, "fltcat": "MVFR"}]
        return Resp()

    monkeypatch.setattr(notam.httpx, "get", fake_get)
    report = notam.check_airspace(40.64, -73.78)
    assert report.status == "ok"
    assert report.wind_max_kt == 24.0
    assert report.flight_category == "MVFR"
    assert report.notam_source == "simulated"  # honestly labelled
    assert all(n["source"] == "simulated" for n in report.simulated_notams)


def test_online_no_stations_reports_ok_not_offline(monkeypatch):
    """aviationweather.gov returns 204 No Content when no METAR station is in the bbox."""
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen.update(params or {})
        class Resp:
            status_code = 204
            text = ""

            def raise_for_status(self):
                pass

        return Resp()

    monkeypatch.setattr(notam.httpx, "get", fake_get)
    report = notam.check_airspace(10.0, 20.0)
    assert report.status == "ok"          # feed reachable, not "offline"
    assert report.station_metar == []     # honestly empty, not an error
    assert "No METAR stations reporting" in report.advisory
    assert seen["bbox"] == "9.6000,19.6000,10.4000,20.4000"  # lat0,lon0,lat1,lon1


def test_offline_no_cache_returns_safe_guidance(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(notam.httpx, "get", boom)
    report = notam.check_airspace(40.64, -73.78)
    assert report.status == "offline_no_cache"
    assert "DO NOT LAUNCH" in report.advisory
    assert report.notam_source == "simulated"


def test_offline_falls_back_to_cache(monkeypatch):
    calls = {"n": 0}

    def flaky_get(url, params=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            class Resp:
                text = '[{"icaoId":"KJFK","wspd":5,"fltcat":"VFR"}]'
                def raise_for_status(self):
                    pass
                def json(self):
                    return [{"icaoId": "KJFK", "wspd": 5, "fltcat": "VFR"}]
            return Resp()
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(notam.httpx, "get", flaky_get)
    first = notam.check_airspace(40.64, -73.78)
    assert first.status == "ok"
    cached = notam.check_airspace(40.64, -73.78)
    assert cached.status == "offline_cache"
    assert cached.wind_max_kt == 5.0
