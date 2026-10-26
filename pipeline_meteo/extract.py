"""Extraction de la météo actuelle depuis l'API OpenWeatherMap.

Produit un fichier NDJSON (une ligne JSON par ville) :
    <output_dir>/date=AAAA-MM-JJ/weather.ndjson

Le chemin ne dépend que de la date d'exécution : relancer une même date
écrase le fichier au lieu de créer un doublon (traitement idempotent).

Usage :
    python -m pipeline_meteo.extract --date 2026-10-26 --output-dir data/raw
"""

import argparse
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline_meteo.secrets import get_api_key

API_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_CITIES_FILE = Path(__file__).resolve().parent.parent / "config" / "cities.json"
REQUEST_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)


class ExtractionError(RuntimeError):
    """Échec d'extraction. Le message ne contient jamais la clé API."""


def build_session(total_retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    """Session HTTP qui réessaie sur les erreurs temporaires (429 et 5xx)."""
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def load_cities(path: Path = DEFAULT_CITIES_FILE) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        cities = json.load(f)
    for city in cities:
        missing = {"name", "lat", "lon"} - city.keys()
        if missing:
            raise ValueError(f"Ville mal définie dans {path} : champs manquants {missing}")
    return cities


def fetch_city_weather(session: requests.Session, city: dict, api_key: str) -> dict:
    params = {"lat": city["lat"], "lon": city["lon"], "appid": api_key, "units": "metric"}
    try:
        response = session.get(API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        # Les exceptions de requests contiennent l'URL complète, donc la clé :
        # on ne garde que le type d'erreur et on coupe la chaîne d'exceptions.
        raise ExtractionError(
            f"{city['name']} : erreur réseau ({type(exc).__name__})"
        ) from None

    if response.status_code == 401:
        raise ExtractionError(
            "Clé API refusée (401). Vérifier la clé ; une clé neuve peut "
            "mettre jusqu'à quelques heures à être activée."
        )
    if response.status_code != 200:
        raise ExtractionError(f"{city['name']} : réponse HTTP {response.status_code}")
    return response.json()


def extract(cities: list[dict], api_key: str, run_date: date,
            session: requests.Session | None = None) -> list[dict]:
    """Interroge l'API pour chaque ville et ajoute des métadonnées de chargement.

    La réponse de l'API est conservée intacte dans `payload` : la couche brute
    reste fidèle à la source, le nettoyage se fera dans dbt.
    Si une ville échoue, toute l'extraction échoue : Airflow relancera la date
    complète, ce qui est sans risque puisque l'écriture est idempotente.
    """
    session = session or build_session()
    extracted_at = datetime.now(timezone.utc).isoformat()
    records, errors = [], []

    for city in cities:
        try:
            payload = fetch_city_weather(session, city, api_key)
        except ExtractionError as exc:
            logger.error("%s", exc)
            errors.append(str(exc))
            continue
        records.append({
            "run_date": run_date.isoformat(),
            "extracted_at": extracted_at,
            "city_name": city["name"],
            "country": city.get("country"),
            "payload": payload,
        })
        logger.info("%s : OK", city["name"])

    if errors:
        raise ExtractionError(f"{len(errors)} ville(s) en échec sur {len(cities)}")
    return records


def write_ndjson(records: list[dict], output_dir: Path, run_date: date) -> Path:
    partition = Path(output_dir) / f"date={run_date.isoformat()}"
    partition.mkdir(parents=True, exist_ok=True)
    path = partition / "weather.ndjson"
    tmp_path = path.with_suffix(".ndjson.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp_path.replace(path)  # écriture atomique : pas de fichier à moitié écrit
    return path


def run(run_date: date, output_dir: Path, cities_file: Path = DEFAULT_CITIES_FILE) -> Path:
    load_dotenv()
    cities = load_cities(cities_file)
    records = extract(cities, get_api_key(), run_date)
    path = write_ndjson(records, output_dir, run_date)
    logger.info("%d enregistrements écrits dans %s", len(records), path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraction OpenWeatherMap vers NDJSON")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(),
                        help="Date d'exécution AAAA-MM-JJ (défaut : aujourd'hui)")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--cities-file", type=Path, default=DEFAULT_CITIES_FILE)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(args.date, args.output_dir, args.cities_file)


if __name__ == "__main__":
    main()
