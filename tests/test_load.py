from datetime import date

import pytest
from google.cloud import bigquery

from pipeline_meteo import load as ld

RUN_DATE = date(2026, 10, 26)
SETTINGS = ld.GcpSettings(project_id="mon-projet", bucket="mon-bucket", dataset="meteo_raw")


class FakeBlob:
    def __init__(self, name, uploads):
        self.name, self.uploads = name, uploads

    def upload_from_filename(self, filename, content_type=None):
        self.uploads.append((self.name, filename, content_type))


class FakeBucket:
    def __init__(self, uploads):
        self.uploads = uploads

    def blob(self, name):
        return FakeBlob(name, self.uploads)


class FakeStorageClient:
    def __init__(self):
        self.uploads, self.buckets = [], []

    def bucket(self, name):
        self.buckets.append(name)
        return FakeBucket(self.uploads)


class FakeJob:
    def __init__(self, output_rows):
        self.output_rows = output_rows

    def result(self):
        return self


class FakeBigQueryClient:
    def __init__(self, output_rows):
        self.output_rows = output_rows
        self.created, self.loads = [], []

    def create_table(self, table, exists_ok=False):
        self.created.append((table, exists_ok))

    def load_table_from_uri(self, uri, destination, job_config=None):
        self.loads.append((uri, destination, job_config))
        return FakeJob(self.output_rows)


@pytest.fixture
def ndjson_file(tmp_path):
    path = ld.local_file_path(tmp_path, RUN_DATE)
    path.parent.mkdir(parents=True)
    path.write_text('{"city_name": "Paris"}\n{"city_name": "Lyon"}\n', encoding="utf-8")
    return path


def test_envoi_gcs_dans_le_bon_chemin(ndjson_file):
    client = FakeStorageClient()
    uri = ld.upload_to_gcs(client, SETTINGS, ndjson_file, RUN_DATE)

    assert uri == "gs://mon-bucket/raw/openweather/date=2026-10-26/weather.ndjson"
    assert client.buckets == ["mon-bucket"]
    assert client.uploads[0][0] == "raw/openweather/date=2026-10-26/weather.ndjson"


def test_envoi_gcs_sans_fichier_local(tmp_path):
    with pytest.raises(ld.LoadError, match="introuvable"):
        ld.upload_to_gcs(FakeStorageClient(), SETTINGS, tmp_path / "absent.ndjson", RUN_DATE)


def test_chargement_remplace_seulement_la_partition_du_jour():
    client = FakeBigQueryClient(output_rows=2)
    rows = ld.load_to_bigquery(client, SETTINGS, "gs://b/f.ndjson", RUN_DATE, expected_rows=2)

    assert rows == 2
    uri, destination, config = client.loads[0]
    assert destination == "mon-projet.meteo_raw.weather_raw$20261026"
    assert config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert config.source_format == bigquery.SourceFormat.NEWLINE_DELIMITED_JSON


def test_table_creee_partitionnee_par_run_date():
    client = FakeBigQueryClient(output_rows=2)
    ld.load_to_bigquery(client, SETTINGS, "gs://b/f.ndjson", RUN_DATE, expected_rows=2)

    table, exists_ok = client.created[0]
    assert exists_ok is True
    assert table.time_partitioning.field == "run_date"
    assert {f.name: f.field_type for f in table.schema}["payload"] == "JSON"


def test_controle_du_nombre_de_lignes():
    client = FakeBigQueryClient(output_rows=1)
    with pytest.raises(ld.LoadError, match="Contrôle échoué"):
        ld.load_to_bigquery(client, SETTINGS, "gs://b/f.ndjson", RUN_DATE, expected_rows=2)


def test_run_enchaine_gcs_puis_bigquery(ndjson_file, tmp_path, monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "mon-projet")
    monkeypatch.setenv("GCS_BUCKET", "mon-bucket")
    monkeypatch.setenv("BQ_DATASET_RAW", "meteo_raw")
    storage_client, bq_client = FakeStorageClient(), FakeBigQueryClient(output_rows=2)

    rows = ld.run(RUN_DATE, tmp_path, storage_client=storage_client, bq_client=bq_client)

    assert rows == 2
    assert bq_client.loads[0][0] == "gs://mon-bucket/raw/openweather/date=2026-10-26/weather.ndjson"


def test_variables_manquantes(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "")
    monkeypatch.setenv("GCS_BUCKET", "")
    with pytest.raises(ld.LoadError, match="GCP_PROJECT_ID"):
        ld.GcpSettings.from_env()
