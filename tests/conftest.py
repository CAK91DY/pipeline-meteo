"""Données de test partagées : de faux fichiers Olist et une fausse session HTTP."""

import csv

import pytest

from pipeline_retail import config


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def olist_dir(tmp_path):
    """Mini jeu Olist : 2 commandes le 24/11/2017, 1 le 25/11/2017."""
    d = tmp_path / "olist_source"
    d.mkdir()
    write_csv(d / config.OLIST_FILES["orders"], [
        {"order_id": "o1", "customer_id": "c1", "order_status": "delivered",
         "order_purchase_timestamp": "2017-11-24 10:15:32"},
        {"order_id": "o2", "customer_id": "c2", "order_status": "delivered",
         "order_purchase_timestamp": "2017-11-24 22:01:00"},
        {"order_id": "o3", "customer_id": "c1", "order_status": "shipped",
         "order_purchase_timestamp": "2017-11-25 08:00:00"},
    ])
    write_csv(d / config.OLIST_FILES["order_items"], [
        {"order_id": "o1", "order_item_id": "1", "product_id": "p1", "price": "49.90"},
        {"order_id": "o1", "order_item_id": "2", "product_id": "p2", "price": "10.00"},
        {"order_id": "o3", "order_item_id": "1", "product_id": "p1", "price": "49.90"},
    ])
    write_csv(d / config.OLIST_FILES["order_payments"], [
        {"order_id": "o1", "payment_type": "credit_card", "payment_value": "59.90"},
        {"order_id": "o2", "payment_type": "boleto", "payment_value": "20.00"},
    ])
    # Un avis avec un retour à la ligne, comme dans le vrai jeu.
    write_csv(d / config.OLIST_FILES["order_reviews"], [
        {"review_id": "r1", "order_id": "o2", "review_score": "5",
         "review_comment_message": "Muito bom,\nchegou rápido"},
    ])
    write_csv(d / config.OLIST_FILES["customers"], [
        {"customer_id": "c1", "customer_state": "SP"}, {"customer_id": "c2", "customer_state": "RJ"}])
    write_csv(d / config.OLIST_FILES["products"], [{"product_id": "p1", "product_category_name": "beleza_saude"}])
    write_csv(d / config.OLIST_FILES["sellers"], [{"seller_id": "s1", "seller_state": "SP"}])
    # Le vrai fichier de traduction commence par un BOM : on le reproduit.
    path = d / config.OLIST_FILES["category_translation"]
    path.write_text("﻿product_category_name,product_category_name_english\n"
                    "beleza_saude,health_beauty\n", encoding="utf-8")
    return d


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    """Remplace requests.Session : renvoie une réponse selon le début de l'URL."""

    def __init__(self, routes):
        self.routes = routes   # {préfixe d'URL: réponse ou exception}
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers))
        for prefix, response in self.routes.items():
            if url.startswith(prefix):
                if isinstance(response, Exception):
                    raise response
                return response
        return FakeResponse(404)


SIDRA_HEADER = {"D1C": "Unidade da Federação (Código)", "D3C": "Ano (Código)", "V": "Valor"}


@pytest.fixture
def api_session():
    return FakeSession({
        "https://api.frankfurter.dev/v1/": FakeResponse(200, {
            "amount": 1.0, "base": "BRL", "date": "2017-11-24",
            "rates": {"EUR": 0.26056, "USD": 0.30947}}),
        "https://date.nager.at/": FakeResponse(200, [
            {"date": "2017-12-25", "localName": "Natal", "global": True}]),
        "https://servicodados.ibge.gov.br/": FakeResponse(200, [
            {"id": 35, "sigla": "SP", "nome": "São Paulo",
             "regiao": {"id": 3, "sigla": "SE", "nome": "Sudeste"}}]),
        "https://apisidra.ibge.gov.br/": FakeResponse(200, [
            SIDRA_HEADER, {"D1C": "35", "D3C": "2017", "V": "45094866"}]),
    })
