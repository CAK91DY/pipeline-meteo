"""Commandes du pipeline, utilisables dans un terminal ou depuis Airflow.

    python -m pipeline_retail download-olist                 # une seule fois
    python -m pipeline_retail extract-reference              # tables de référence
    python -m pipeline_retail extract-daily --date 2017-11-24
    python -m pipeline_retail load --scope daily --date 2017-11-24
    python -m pipeline_retail run-daily --date 2017-11-24    # extraction + chargement
    python -m pipeline_retail backfill --start 2016-09-01 --end 2018-10-31  # tout rejouer en local
"""

import argparse
import logging
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from pipeline_retail import config
from pipeline_retail.http import build_session
from pipeline_retail.sources import fx_rates, holidays, ibge, olist
from pipeline_retail.storage import raw_file_path, wrap_records, write_ndjson

logger = logging.getLogger(__name__)


def save_tables(tables: dict[tuple[str, str], list[dict]], run_date: date,
                raw_dir: Path = config.RAW_DIR, log_level: int = logging.INFO) -> None:
    """Écrit chaque table dans son fichier brut : {(source, table): enregistrements}."""
    for (source, table), records in tables.items():
        path = raw_file_path(raw_dir, source, table, run_date)
        write_ndjson(wrap_records(records, source, run_date), path)
        logger.log(log_level, "%s_%s : %d lignes -> %s", source, table, len(records), path)


def extract_daily(run_date: date, source_dir: Path = config.OLIST_SOURCE_DIR,
                  raw_dir: Path = config.RAW_DIR, session=None) -> None:
    """Extrait les données d'une journée : commandes Olist + taux de change."""
    session = session or build_session()
    # {"orders": [...], ...} devient {("olist", "orders"): [...], ...}
    tables = {("olist", name): rows for name, rows in olist.extract_daily(source_dir, run_date).items()}
    tables[("frankfurter", "fx_rates")] = fx_rates.fetch_rates(session, run_date)
    save_tables(tables, run_date, raw_dir)


def backfill(start: date, end: date, source_dir: Path = config.OLIST_SOURCE_DIR,
             raw_dir: Path = config.RAW_DIR, session=None) -> None:
    """Rejoue toute une période d'un coup (utile pour alimenter dbt en local).

    Le résultat est identique à extract-daily lancé jour par jour, mais beaucoup plus
    rapide : les CSV sont lus une seule fois et les taux de change demandés en un appel.
    """
    if start > end:
        raise ValueError(f"Période invalide : {start} est après {end}")
    session = session or build_session()
    olist_days = olist.extract_range(source_dir, start, end)
    fx_days = fx_rates.fetch_rates_range(session, start, end)
    for day, olist_tables in olist_days.items():
        tables = {("olist", name): rows for name, rows in olist_tables.items()}
        tables[("frankfurter", "fx_rates")] = fx_days.get(day, [])
        # DEBUG : on n'affiche pas les centaines de lignes de détail, seulement le bilan
        save_tables(tables, day, raw_dir, log_level=logging.DEBUG)
    logger.info("Rejeu terminé : %d jours écrits dans %s", len(olist_days), raw_dir)


def extract_reference(run_date: date, source_dir: Path = config.OLIST_SOURCE_DIR,
                      raw_dir: Path = config.RAW_DIR, session=None) -> None:
    """Extrait les tables de référence : Olist, jours fériés, États, population."""
    session = session or build_session()
    tables = {("olist", name): rows for name, rows in olist.extract_reference(source_dir).items()}
    tables[("nager", "holidays")] = holidays.fetch_holidays(session)
    tables[("ibge", "states")] = ibge.fetch_states(session)
    tables[("ibge", "population")] = ibge.fetch_population(session)
    save_tables(tables, run_date, raw_dir)


def load(scope: str, run_date: date, raw_dir: Path = config.RAW_DIR) -> None:
    """Charge dans BigQuery toutes les tables d'un périmètre (daily ou reference)."""
    # Imports locaux : l'extraction seule ne nécessite pas les bibliothèques Google.
    from google.cloud import bigquery, storage

    from pipeline_retail.load import GcpSettings, load_table

    settings = GcpSettings.from_env()
    storage_client = storage.Client(project=settings.project_id)
    bq_client = bigquery.Client(project=settings.project_id)
    tables = config.DAILY_TABLES if scope == "daily" else config.REFERENCE_TABLES
    for source, table in tables:
        load_table(storage_client, bq_client, settings, raw_dir, source, table, run_date)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="pipeline_retail", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("download-olist", help="Télécharge les CSV Olist depuis Kaggle")

    # date.fromisoformat transforme le texte "2017-11-24" en objet date (et refuse une date invalide).
    p = commands.add_parser("extract-daily", help="Extrait une journée")
    p.add_argument("--date", type=date.fromisoformat, required=True)

    p = commands.add_parser("extract-reference", help="Extrait les tables de référence")
    p.add_argument("--date", type=date.fromisoformat, default=date.today(),
                   help="Date de chargement (défaut : aujourd'hui)")

    p = commands.add_parser("load", help="Charge dans Cloud Storage puis BigQuery")
    p.add_argument("--scope", choices=("daily", "reference"), required=True)
    p.add_argument("--date", type=date.fromisoformat, required=True)

    p = commands.add_parser("run-daily", help="Extraction puis chargement d'une journée")
    p.add_argument("--date", type=date.fromisoformat, required=True)

    p = commands.add_parser("backfill", help="Rejoue toute une période en local")
    p.add_argument("--start", type=date.fromisoformat, required=True)
    p.add_argument("--end", type=date.fromisoformat, required=True)

    args = parser.parse_args(argv)
    load_dotenv()   # lit le fichier .env (secrets et paramètres GCP)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.command == "download-olist":
        olist.download_dataset()
    elif args.command == "extract-daily":
        extract_daily(args.date)
    elif args.command == "extract-reference":
        extract_reference(args.date)
    elif args.command == "load":
        load(args.scope, args.date)
    elif args.command == "backfill":
        backfill(args.start, args.end)
    elif args.command == "run-daily":
        extract_daily(args.date)
        load("daily", args.date)
