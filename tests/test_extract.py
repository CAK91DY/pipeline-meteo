import json
from datetime import date

import pytest
import requests

from pipeline_meteo import extract as ex
from pipeline_meteo.secrets import MissingApiKeyError, get_api_key

API_KEY = "cle-secrete-de-test"
CITIES = [
    {"name": "Paris", "country": "FR", "lat": 48.85, "lon": 2.35},
    {"name": "Lyon", "country": "FR", "lat": 45.76, "lon": 4.83},
]
RUN_DATE = date(2026, 10, 26)


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    """Remplace requests.Session : renvoie une réponse par appel, dans l'ordre."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_extract_ajoute_les_metadonnees_et_garde_la_reponse_brute():
    payload = {"name": "Paris", "main": {"temp": 12.3}}
    session = FakeSession([FakeResponse(200, payload), FakeResponse(200, payload)])

    records = ex.extract(CITIES, API_KEY, RUN_DATE, session=session)

    assert len(records) == 2
    assert records[0]["run_date"] == "2026-10-26"
    assert records[0]["city_name"] == "Paris"
    assert records[0]["payload"] == payload
    assert session.calls[0]["units"] == "metric"


def test_cle_refusee_donne_un_message_clair():
    session = FakeSession([FakeResponse(401), FakeResponse(401)])
    with pytest.raises(ex.ExtractionError):
        ex.extract(CITIES, API_KEY, RUN_DATE, session=session)


def test_une_ville_en_echec_fait_echouer_l_extraction():
    session = FakeSession([FakeResponse(200, {"ok": 1}), FakeResponse(503)])
    with pytest.raises(ex.ExtractionError, match="1 ville"):
        ex.extract(CITIES, API_KEY, RUN_DATE, session=session)


def test_la_cle_n_apparait_pas_dans_les_erreurs_reseau():
    error = requests.ConnectionError(f"https://api.example?appid={API_KEY}")
    session = FakeSession([error])
    with pytest.raises(ex.ExtractionError) as excinfo:
        ex.fetch_city_weather(session, CITIES[0], API_KEY)
    assert API_KEY not in str(excinfo.value)
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


def test_ecriture_ndjson_idempotente(tmp_path):
    records = [{"city_name": "Paris"}, {"city_name": "Lyon"}]
    path = ex.write_ndjson(records, tmp_path, RUN_DATE)
    ex.write_ndjson(records, tmp_path, RUN_DATE)  # relance de la même date

    assert path == tmp_path / "date=2026-10-26" / "weather.ndjson"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["city_name"] for line in lines] == ["Paris", "Lyon"]
    assert list(path.parent.iterdir()) == [path]


def test_load_cities_refuse_une_ville_incomplete(tmp_path):
    bad = tmp_path / "cities.json"
    bad.write_text(json.dumps([{"name": "Paris"}]), encoding="utf-8")
    with pytest.raises(ValueError):
        ex.load_cities(bad)


def test_fichier_de_villes_du_projet_valide():
    assert len(ex.load_cities()) >= 1


def test_get_api_key_depuis_l_environnement(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", API_KEY)
    assert get_api_key() == API_KEY


def test_get_api_key_absente(monkeypatch):
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("OPENWEATHER_SECRET_ID", raising=False)
    with pytest.raises(MissingApiKeyError):
        get_api_key()
