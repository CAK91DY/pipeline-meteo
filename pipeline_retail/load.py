"""Chargement d'un fichier brut : disque local -> Cloud Storage -> BigQuery.

Pour chaque table (source, table) et chaque date :
1. le fichier local est copié dans
   gs://<bucket>/raw/<source>/<table>/date=AAAA-MM-JJ/data.ndjson
2. il est chargé dans la table BigQuery <dataset>.<source>_<table>,
   partitionnée par jour sur la colonne run_date.

Les deux opérations sont idempotentes : le fichier GCS est écrasé, et le
chargement ne remplace que la partition de la date (WRITE_TRUNCATE sur
`table$AAAAMMJJ`). Relancer une date ne crée donc jamais de doublon.
"""

import logging
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from google.cloud import bigquery

from pipeline_retail.storage import raw_file_path

# Même schéma pour toutes les tables brutes (voir storage.py).
SCHEMA = [
    bigquery.SchemaField("run_date", "DATE", mode="REQUIRED",
                         description="Date logique traitée (partition)"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP", mode="REQUIRED",
                         description="Horodatage UTC de l'extraction"),
    bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("record", "JSON", mode="REQUIRED",
                         description="Enregistrement brut de la source, non modifié"),
]

logger = logging.getLogger(__name__)


class LoadError(RuntimeError):
    """Échec du chargement ou contrôle de cohérence non respecté."""


@dataclass(frozen=True)
class GcpSettings:
    """Les trois paramètres Google Cloud dont le chargement a besoin."""
    project_id: str
    bucket: str
    dataset: str

    @classmethod
    def from_env(cls) -> "GcpSettings":
        # Nom du champ -> nom de la variable dans .env
        env_vars = {"project_id": "GCP_PROJECT_ID", "bucket": "GCS_BUCKET",
                    "dataset": "BQ_DATASET_RAW"}
        values = {field: os.getenv(var, "").strip() for field, var in env_vars.items()}
        values["dataset"] = values["dataset"] or "retail_raw"   # valeur par défaut
        missing = [env_vars[field] for field, value in values.items() if not value]
        if missing:
            raise LoadError(f"Variables manquantes dans .env : {', '.join(missing)}")
        return cls(**values)


def count_lines(path: Path) -> int:
    """Nombre d'enregistrements dans un fichier NDJSON (lignes non vides)."""
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def upload_to_gcs(storage_client, settings: GcpSettings, local_path: Path,
                  source: str, table: str, run_date: date) -> str:
    # Le chemin dans le bucket reprend la même organisation que sur le disque.
    blob_name = f"raw/{source}/{table}/date={run_date.isoformat()}/data.ndjson"
    blob = storage_client.bucket(settings.bucket).blob(blob_name)
    blob.upload_from_filename(str(local_path), content_type="application/x-ndjson")
    uri = f"gs://{settings.bucket}/{blob_name}"
    logger.info("Fichier envoyé : %s", uri)
    return uri


def ensure_table(bq_client, table_id: str) -> None:
    """Crée la table partitionnée par jour si elle n'existe pas encore."""
    table = bigquery.Table(table_id, schema=SCHEMA)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="run_date")
    # exists_ok=True : si la table existe déjà, on ne fait rien (pas d'erreur).
    bq_client.create_table(table, exists_ok=True)


def load_to_bigquery(bq_client, settings: GcpSettings, gcs_uri: str, source: str,
                     table: str, run_date: date, expected_rows: int) -> int:
    table_id = f"{settings.project_id}.{settings.dataset}.{source}_{table}"
    ensure_table(bq_client, table_id)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        # WRITE_TRUNCATE + décorateur $AAAAMMJJ = remplacer uniquement ce jour-là.
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=SCHEMA,
    )
    destination = f"{table_id}${run_date:%Y%m%d}"
    job = bq_client.load_table_from_uri(gcs_uri, destination, job_config=job_config)
    job.result()   # attend la fin du job ; lève une exception si BigQuery refuse

    # Contrôle de cohérence : autant de lignes en base que dans le fichier.
    if job.output_rows != expected_rows:
        raise LoadError(f"{source}_{table} : {job.output_rows} lignes chargées, "
                        f"{expected_rows} attendues")
    logger.info("%d lignes chargées dans %s", job.output_rows, destination)
    return job.output_rows


def load_table(storage_client, bq_client, settings: GcpSettings, raw_dir: Path,
               source: str, table: str, run_date: date) -> int:
    """Charge une table pour une date : envoi GCS puis chargement BigQuery."""
    local_path = raw_file_path(raw_dir, source, table, run_date)
    if not local_path.exists():
        raise LoadError(f"Fichier introuvable : {local_path} (lancer l'extraction d'abord)")

    rows = count_lines(local_path)
    if rows == 0:
        # Exemple : un jour sans aucune commande. Rien à charger, ce n'est pas une erreur.
        logger.warning("%s_%s %s : fichier vide, rien à charger", source, table, run_date)
        return 0

    gcs_uri = upload_to_gcs(storage_client, settings, local_path, source, table, run_date)
    return load_to_bigquery(bq_client, settings, gcs_uri, source, table, run_date, rows)
