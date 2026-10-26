"""Chargement du fichier brut : disque local → Cloud Storage → BigQuery.

1. Le fichier NDJSON de la date est copié dans
   gs://<bucket>/raw/openweather/date=AAAA-MM-JJ/weather.ndjson
2. Il est chargé dans la table BigQuery <dataset>.weather_raw, partitionnée
   par jour sur la colonne run_date.

Les deux opérations sont idempotentes : le fichier GCS est écrasé, et le
chargement remplace uniquement la partition de la date (WRITE_TRUNCATE sur
`weather_raw$AAAAMMJJ`). Relancer une date ne crée donc jamais de doublon et
ne touche pas aux autres jours.

Usage :
    python -m pipeline_meteo.load --date 2026-10-26 --input-dir data/raw
"""

import argparse
import logging
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery, storage

GCS_PREFIX = "raw/openweather"
TABLE_NAME = "weather_raw"
SCHEMA = [
    bigquery.SchemaField("run_date", "DATE", mode="REQUIRED",
                         description="Date d'exécution du pipeline (partition)"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP", mode="REQUIRED",
                         description="Horodatage UTC de l'appel à l'API"),
    bigquery.SchemaField("city_name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("country", "STRING"),
    bigquery.SchemaField("payload", "JSON", mode="REQUIRED",
                         description="Réponse brute de l'API OpenWeatherMap"),
]

logger = logging.getLogger(__name__)


class LoadError(RuntimeError):
    """Échec du chargement ou contrôle de cohérence non respecté."""


@dataclass(frozen=True)
class GcpSettings:
    project_id: str
    bucket: str
    dataset: str

    @classmethod
    def from_env(cls) -> "GcpSettings":
        env_vars = {"project_id": "GCP_PROJECT_ID", "bucket": "GCS_BUCKET",
                    "dataset": "BQ_DATASET_RAW"}
        values = {field: os.getenv(var, "").strip() for field, var in env_vars.items()}
        values["dataset"] = values["dataset"] or "meteo_raw"
        missing = [env_vars[field] for field, value in values.items() if not value]
        if missing:
            raise LoadError(f"Variables manquantes dans .env : {', '.join(missing)}")
        return cls(**values)


def local_file_path(input_dir: Path, run_date: date) -> Path:
    return Path(input_dir) / f"date={run_date.isoformat()}" / "weather.ndjson"


def gcs_blob_name(run_date: date) -> str:
    return f"{GCS_PREFIX}/date={run_date.isoformat()}/weather.ndjson"


def partition_table_id(settings: GcpSettings, run_date: date) -> str:
    return f"{settings.project_id}.{settings.dataset}.{TABLE_NAME}${run_date:%Y%m%d}"


def count_lines(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def upload_to_gcs(storage_client, settings: GcpSettings, local_path: Path,
                  run_date: date) -> str:
    if not local_path.exists():
        raise LoadError(f"Fichier introuvable : {local_path} (lancer l'extraction d'abord)")
    blob_name = gcs_blob_name(run_date)
    blob = storage_client.bucket(settings.bucket).blob(blob_name)
    blob.upload_from_filename(str(local_path), content_type="application/x-ndjson")
    uri = f"gs://{settings.bucket}/{blob_name}"
    logger.info("Fichier envoyé : %s", uri)
    return uri


def ensure_table(bq_client, settings: GcpSettings) -> None:
    """Crée la table partitionnée si elle n'existe pas encore."""
    table = bigquery.Table(f"{settings.project_id}.{settings.dataset}.{TABLE_NAME}",
                           schema=SCHEMA)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="run_date")
    table.description = "Couche brute : une ligne par ville et par exécution"
    bq_client.create_table(table, exists_ok=True)


def load_to_bigquery(bq_client, settings: GcpSettings, gcs_uri: str,
                     run_date: date, expected_rows: int) -> int:
    ensure_table(bq_client, settings)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=SCHEMA,
    )
    destination = partition_table_id(settings, run_date)
    job = bq_client.load_table_from_uri(gcs_uri, destination, job_config=job_config)
    job.result()  # attend la fin du job et lève une exception en cas d'erreur

    if job.output_rows != expected_rows:
        raise LoadError(
            f"Contrôle échoué : {job.output_rows} lignes chargées, {expected_rows} attendues"
        )
    logger.info("%d lignes chargées dans %s", job.output_rows, destination)
    return job.output_rows


def run(run_date: date, input_dir: Path, storage_client=None, bq_client=None) -> int:
    load_dotenv()
    settings = GcpSettings.from_env()
    storage_client = storage_client or storage.Client(project=settings.project_id)
    bq_client = bq_client or bigquery.Client(project=settings.project_id)

    local_path = local_file_path(input_dir, run_date)
    gcs_uri = upload_to_gcs(storage_client, settings, local_path, run_date)
    return load_to_bigquery(bq_client, settings, gcs_uri, run_date, count_lines(local_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Chargement GCS puis BigQuery")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(),
                        help="Date d'exécution AAAA-MM-JJ (défaut : aujourd'hui)")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(args.date, args.input_dir)


if __name__ == "__main__":
    main()
