"""Enrichissement : États brésiliens et population (IBGE, institut de statistique).

Sert à calculer des ventes par habitant : sans cela, São Paulo domine tous les
classements simplement parce que c'est l'État le plus peuplé.
"""

from pipeline_retail import config
from pipeline_retail.http import get_json


def fetch_states(session) -> list[dict]:
    """Liste des 27 États : code IBGE, sigle (SP, RJ...), nom et région."""
    # Réponse type : [{"id": 35, "sigla": "SP", "nome": "São Paulo",
    #                  "regiao": {"id": 3, "sigla": "SE", "nome": "Sudeste"}}, ...]
    # Le sigle est la clé commune avec Olist (colonnes customer_state, seller_state).
    return get_json(session, config.IBGE_STATES_URL)


def fetch_population(session, years=config.OLIST_YEARS) -> list[dict]:
    """Population estimée de chaque État, pour chaque année demandée."""
    records = []
    for year in years:
        rows = get_json(session, config.IBGE_POPULATION_URL.format(year=year))
        # L'API SIDRA renvoie d'abord une ligne d'en-tête qui décrit les colonnes
        # ({"D1C": "Unidade da Federação (Código)", "V": "Valor", ...}).
        # Ce n'est pas une donnée : on la saute avec rows[1:].
        # Les lignes suivantes ressemblent à :
        #   {"D1C": "35", "D1N": "São Paulo", "D3C": "2017", "V": "45094866", ...}
        # D1C = code de l'État, D3C = année, V = population.
        records.extend(rows[1:])
    return records
