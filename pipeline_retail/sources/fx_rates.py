"""Enrichissement : taux de change BRL -> EUR et USD (Banque centrale européenne).

Sert à exprimer le chiffre d'affaires d'Olist en euros ou en dollars.
API utilisée : Frankfurter, gratuite et sans clé.
"""

from datetime import date

from pipeline_retail import config
from pipeline_retail.http import get_json


def fetch_rates(session, run_date: date) -> list[dict]:
    """Renvoie le taux de change du jour sous forme d'un enregistrement brut."""
    # Exemple d'URL : https://api.frankfurter.dev/v1/2017-11-24?from=BRL&to=EUR,USD
    payload = get_json(
        session,
        f"{config.FX_API_URL}/{run_date.isoformat()}",
        params={"from": config.FX_BASE_CURRENCY, "to": ",".join(config.FX_TARGET_CURRENCIES)},
    )
    # Réponse type : {"amount": 1.0, "base": "BRL", "date": "2017-11-24",
    #                 "rates": {"EUR": 0.26056, "USD": 0.30947}}
    # Attention : la BCE ne publie pas de taux le week-end ni les jours fériés.
    # Pour un samedi, l'API renvoie le taux du vendredi : "date" vaut alors la date
    # du vendredi. On garde donc aussi la date demandée pour pouvoir faire la jointure.
    return [{"requested_date": run_date.isoformat(), **payload}]
