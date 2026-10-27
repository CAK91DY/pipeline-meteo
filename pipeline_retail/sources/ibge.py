"""Enrichissement : États brésiliens et population (IBGE, institut de statistique).

Sert à calculer des ventes par habitant : sans cela, São Paulo domine tous les
classements simplement parce que c'est l'État le plus peuplé.

Particularité : les API de l'IBGE ne répondent qu'aux connexions venant du Brésil
(depuis la France, la connexion expire). Comme ces données changent très rarement,
on les stocke une fois pour toutes dans dbt/seeds/ (fichiers CSV versionnés).
La commande "python -m pipeline_retail refresh-ibge" les met à jour, depuis un réseau
qui peut joindre l'IBGE (VPN brésilien, serveur au Brésil...).
"""

import csv
from pathlib import Path

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


def write_seeds(session, seeds_dir: Path = config.DBT_SEEDS_DIR, years=config.OLIST_YEARS) -> None:
    """Interroge l'IBGE et réécrit les deux fichiers de référence de dbt/seeds/."""
    states = fetch_states(session)
    population = fetch_population(session, years)   # appels faits AVANT d'écrire : tout ou rien
    seeds_dir = Path(seeds_dir)
    seeds_dir.mkdir(parents=True, exist_ok=True)

    with open(seeds_dir / "ibge_states.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state_code", "state_abbr", "state_name", "region_abbr", "region_name"])
        for s in sorted(states, key=lambda s: s["id"]):
            writer.writerow([s["id"], s["sigla"], s["nome"], s["regiao"]["sigla"], s["regiao"]["nome"]])

    with open(seeds_dir / "ibge_population.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state_code", "population_year", "population"])
        for row in sorted(population, key=lambda r: (int(r["D1C"]), int(r["D3C"]))):
            # "..." ou "-" signifient "valeur inexistante" chez l'IBGE : on laisse la case vide
            value = row["V"] if row["V"].isdigit() else ""
            writer.writerow([row["D1C"], row["D3C"], value])
