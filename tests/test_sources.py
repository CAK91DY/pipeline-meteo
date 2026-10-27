from datetime import date

import pytest
import requests

from pipeline_retail import http
from pipeline_retail.secrets import MissingSecretError, get_secret
from pipeline_retail.sources import fx_rates, holidays, ibge, olist

from .conftest import FakeResponse, FakeSession

BLACK_FRIDAY = date(2017, 11, 24)


# --- Olist ----------------------------------------------------------------------

def test_rejeu_olist_ne_garde_que_les_commandes_du_jour(olist_dir):
    tables = olist.extract_daily(olist_dir, BLACK_FRIDAY)

    assert [o["order_id"] for o in tables["orders"]] == ["o1", "o2"]
    # Les articles de o3 (commandée le 25) ne doivent pas apparaître.
    assert [(i["order_id"], i["order_item_id"]) for i in tables["order_items"]] == [("o1", "1"), ("o1", "2")]
    assert {p["order_id"] for p in tables["order_payments"]} == {"o1", "o2"}


def test_rejeu_olist_garde_les_retours_a_la_ligne_des_avis(olist_dir):
    review = olist.extract_daily(olist_dir, BLACK_FRIDAY)["order_reviews"][0]
    assert review["review_comment_message"] == "Muito bom,\nchegou rápido"


def test_jour_sans_commande(olist_dir):
    tables = olist.extract_daily(olist_dir, date(2017, 1, 1))
    assert all(rows == [] for rows in tables.values())


def test_references_olist_et_bom_retire(olist_dir):
    ref = olist.extract_reference(olist_dir)
    assert set(ref) == {"customers", "products", "sellers", "category_translation"}
    # Sans utf-8-sig, la clé serait "﻿product_category_name".
    assert ref["category_translation"][0]["product_category_name"] == "beleza_saude"


def test_fichiers_olist_manquants(tmp_path):
    with pytest.raises(olist.OlistSourceError, match="download-olist"):
        olist.check_files(tmp_path)


# --- API d'enrichissement -------------------------------------------------------

def test_taux_de_change_garde_la_date_demandee(api_session):
    saturday = date(2017, 11, 25)
    [record] = fx_rates.fetch_rates(api_session, saturday)

    assert record["requested_date"] == "2017-11-25"   # la date demandée (samedi)
    assert record["date"] == "2017-11-24"             # la date du taux publié (vendredi)
    assert record["rates"]["EUR"] == 0.26056
    url, params, _ = api_session.calls[0]
    assert url.endswith("/2017-11-25") and params == {"from": "BRL", "to": "EUR,USD"}


def test_jours_feries_une_requete_par_annee(api_session):
    records = holidays.fetch_holidays(api_session, years=(2017, 2018))
    assert len(records) == 2
    assert [c[0].split("/")[-2] for c in api_session.calls] == ["2017", "2018"]


def test_population_ignore_la_ligne_d_en_tete(api_session):
    records = ibge.fetch_population(api_session, years=(2017,))
    assert records == [{"D1C": "35", "D3C": "2017", "V": "45094866"}]


def test_etats(api_session):
    assert ibge.fetch_states(api_session)[0]["sigla"] == "SP"


def test_les_api_recoivent_l_en_tete_json(api_session):
    ibge.fetch_states(api_session)
    assert api_session.calls[0][2] == {"Accept": "application/json"}


def test_erreur_http_claire():
    session = FakeSession({"https://x.org": FakeResponse(503)})
    with pytest.raises(http.ApiError, match="503"):
        http.get_json(session, "https://x.org/data")


def test_erreur_reseau_sans_l_url_complete():
    error = requests.ConnectionError("https://x.org/data?token=secret")
    session = FakeSession({"https://x.org": error})
    with pytest.raises(http.ApiError) as excinfo:
        http.get_json(session, "https://x.org/data?token=secret")
    assert "secret" not in str(excinfo.value)
    assert excinfo.value.__cause__ is None and excinfo.value.__suppress_context__


# --- Secrets --------------------------------------------------------------------

def test_secret_depuis_l_environnement(monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", " abc123 \n")
    assert get_secret("KAGGLE_API_TOKEN") == "abc123"


def test_secret_absent(monkeypatch):
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    monkeypatch.delenv("KAGGLE_API_TOKEN_SECRET_ID", raising=False)
    with pytest.raises(MissingSecretError, match="KAGGLE_API_TOKEN"):
        get_secret("KAGGLE_API_TOKEN")
