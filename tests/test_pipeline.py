import json
from datetime import date

import pytest
from google.cloud import bigquery

from pipeline_retail import cli, config
from pipeline_retail import load as ld
from pipeline_retail.storage import raw_file_path, wrap_records, write_ndjson
from tests.conftest import FakeResponse

BLACK_FRIDAY = date(2017, 11, 24)
# Réponse de l'API Frankfurter pour une période (format vérifié sur l'API réelle)
FX_RANGE = FakeResponse(200, {
    "amount": 1.0, "base": "BRL", "start_date": "2017-11-24", "end_date": "2017-11-24",
    "rates": {"2017-11-24": {"EUR": 0.26056, "USD": 0.30947}}})
SETTINGS = ld.GcpSettings(project_id="mon-projet", bucket="mon-bucket", dataset="retail_raw")


def read_ndjson(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# --- Écriture des fichiers bruts --------------------------------------------------

def test_ecriture_idempotente(tmp_path):
    path = raw_file_path(tmp_path, "olist", "orders", BLACK_FRIDAY)
    rows = wrap_records([{"order_id": "o1"}], "olist", BLACK_FRIDAY)
    write_ndjson(rows, path)
    write_ndjson(rows, path)   # relance de la même date

    assert path == tmp_path / "olist" / "orders" / "date=2017-11-24" / "data.ndjson"
    assert len(read_ndjson(path)) == 1
    assert list(path.parent.iterdir()) == [path]   # pas de fichier temporaire oublié


def test_format_commun_des_lignes(tmp_path):
    [row] = wrap_records([{"order_id": "o1"}], "olist", BLACK_FRIDAY)
    assert set(row) == {"run_date", "extracted_at", "source", "record"}
    assert row["run_date"] == "2017-11-24" and row["record"] == {"order_id": "o1"}


# --- Extraction de bout en bout (sans réseau) -------------------------------------

def test_extract_daily_ecrit_toutes_les_tables_du_jour(olist_dir, tmp_path, api_session):
    raw = tmp_path / "raw"
    cli.extract_daily(BLACK_FRIDAY, source_dir=olist_dir, raw_dir=raw, session=api_session)

    for source, table in config.DAILY_TABLES:
        assert raw_file_path(raw, source, table, BLACK_FRIDAY).exists(), (source, table)
    orders = read_ndjson(raw_file_path(raw, "olist", "orders", BLACK_FRIDAY))
    assert [r["record"]["order_id"] for r in orders] == ["o1", "o2"]


def test_extract_reference_ecrit_toutes_les_tables(olist_dir, tmp_path, api_session):
    raw = tmp_path / "raw"
    cli.extract_reference(BLACK_FRIDAY, source_dir=olist_dir, raw_dir=raw, session=api_session)

    for source, table in config.REFERENCE_TABLES:
        assert raw_file_path(raw, source, table, BLACK_FRIDAY).exists(), (source, table)


# --- Chargement (faux clients Google) ---------------------------------------------

class FakeBlob:
    def __init__(self, name, uploads):
        self.name, self.uploads = name, uploads

    def upload_from_filename(self, filename, content_type=None):
        self.uploads.append(self.name)


class FakeStorageClient:
    def __init__(self):
        self.uploads = []

    def bucket(self, name):
        uploads = self.uploads

        class Bucket:
            def blob(self, blob_name):
                return FakeBlob(f"{name}/{blob_name}", uploads)
        return Bucket()


class FakeJob:
    def __init__(self, output_rows):
        self.output_rows = output_rows

    def result(self):
        return self


class FakeBigQueryClient:
    def __init__(self, output_rows):
        self.output_rows, self.created, self.loads = output_rows, [], []

    def create_table(self, table, exists_ok=False):
        self.created.append((table, exists_ok))

    def load_table_from_uri(self, uri, destination, job_config=None):
        self.loads.append((uri, destination, job_config))
        return FakeJob(self.output_rows)


@pytest.fixture
def raw_orders(tmp_path):
    path = raw_file_path(tmp_path, "olist", "orders", BLACK_FRIDAY)
    write_ndjson(wrap_records([{"order_id": "o1"}, {"order_id": "o2"}], "olist", BLACK_FRIDAY), path)
    return tmp_path


def test_chargement_gcs_puis_partition_du_jour(raw_orders):
    storage_client, bq = FakeStorageClient(), FakeBigQueryClient(output_rows=2)
    rows = ld.load_table(storage_client, bq, SETTINGS, raw_orders, "olist", "orders", BLACK_FRIDAY)

    assert rows == 2
    assert storage_client.uploads == ["mon-bucket/raw/olist/orders/date=2017-11-24/data.ndjson"]
    uri, destination, job_config = bq.loads[0]
    assert destination == "mon-projet.retail_raw.olist_orders$20171124"
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    table, exists_ok = bq.created[0]
    assert exists_ok and table.time_partitioning.field == "run_date"


def test_controle_du_nombre_de_lignes(raw_orders):
    with pytest.raises(ld.LoadError, match="1 lignes chargées, 2 attendues"):
        ld.load_table(FakeStorageClient(), FakeBigQueryClient(output_rows=1), SETTINGS,
                      raw_orders, "olist", "orders", BLACK_FRIDAY)


def test_fichier_vide_rien_a_charger(tmp_path):
    write_ndjson([], raw_file_path(tmp_path, "olist", "orders", BLACK_FRIDAY))
    bq = FakeBigQueryClient(output_rows=0)
    assert ld.load_table(FakeStorageClient(), bq, SETTINGS, tmp_path, "olist", "orders", BLACK_FRIDAY) == 0
    assert bq.loads == []


def test_fichier_absent(tmp_path):
    with pytest.raises(ld.LoadError, match="introuvable"):
        ld.load_table(FakeStorageClient(), FakeBigQueryClient(0), SETTINGS,
                      tmp_path, "olist", "orders", BLACK_FRIDAY)


def test_variables_gcp_manquantes(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "")
    monkeypatch.setenv("GCS_BUCKET", "")
    with pytest.raises(ld.LoadError, match="GCP_PROJECT_ID, GCS_BUCKET"):
        ld.GcpSettings.from_env()


# --- Rejeu complet d'une période ----------------------------------------------------

def test_backfill_identique_au_rejeu_jour_par_jour(olist_dir, tmp_path, api_session):
    start, end = date(2017, 11, 24), date(2017, 11, 26)
    api_session.routes = {"https://api.frankfurter.dev/v1/2017-11-24..": FX_RANGE, **api_session.routes}
    cli.backfill(start, end, source_dir=olist_dir, raw_dir=tmp_path / "b", session=api_session)
    cli.extract_daily(BLACK_FRIDAY, source_dir=olist_dir, raw_dir=tmp_path / "d", session=api_session)

    # Pour le 24/11, le contenu est le même que par extract-daily (hors horodatage d'extraction)
    for source, table in config.DAILY_TABLES:
        b = read_ndjson(raw_file_path(tmp_path / "b", source, table, BLACK_FRIDAY))
        d = read_ndjson(raw_file_path(tmp_path / "d", source, table, BLACK_FRIDAY))
        assert [r["record"] for r in b] == [r["record"] for r in d], (source, table)

    # Chaque jour a ses fichiers, même le 26/11 sans commande (fichier vide)
    assert read_ndjson(raw_file_path(tmp_path / "b", "olist", "orders", date(2017, 11, 26))) == []
    orders_25 = read_ndjson(raw_file_path(tmp_path / "b", "olist", "orders", date(2017, 11, 25)))
    assert [r["record"]["order_id"] for r in orders_25] == ["o3"]
    # Le dimanche 26/11 reçoit le taux du vendredi 24/11, comme l'API jour par jour
    [fx_26] = read_ndjson(raw_file_path(tmp_path / "b", "frankfurter", "fx_rates", date(2017, 11, 26)))
    assert fx_26["record"]["requested_date"] == "2017-11-26" and fx_26["record"]["date"] == "2017-11-24"


def test_backfill_refuse_une_periode_inversee(olist_dir, tmp_path, api_session):
    with pytest.raises(ValueError):
        cli.backfill(date(2018, 1, 2), date(2018, 1, 1), source_dir=olist_dir,
                     raw_dir=tmp_path, session=api_session)
