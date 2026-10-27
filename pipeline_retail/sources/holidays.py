"""Enrichissement : jours fériés brésiliens (API Nager.Date, gratuite et sans clé).

Sert à mesurer l'effet des fêtes sur les ventes (Noël, Carnaval...).
Le Black Friday n'est pas un jour férié : il sera calculé dans dbt
(4e vendredi de novembre).
"""

from pipeline_retail import config
from pipeline_retail.http import get_json


def fetch_holidays(session, years=config.OLIST_YEARS) -> list[dict]:
    """Renvoie la liste des jours fériés brésiliens pour les années demandées."""
    records = []
    for year in years:
        # Exemple : https://date.nager.at/api/v3/PublicHolidays/2017/BR
        # Réponse : une liste de fêtes, par exemple
        #   {"date": "2017-12-25", "localName": "Natal", "name": "Christmas Day",
        #    "global": true, "counties": null, "types": ["Public"], ...}
        # "global": false signifie que la fête ne concerne que certains États
        # (listés dans "counties", par exemple ["BR-SP"]).
        records.extend(get_json(session, f"{config.HOLIDAYS_API_URL}/{year}/{config.HOLIDAYS_COUNTRY}"))
    return records
