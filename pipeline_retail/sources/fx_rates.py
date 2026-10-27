"""Enrichissement : taux de change BRL -> EUR et USD (Banque centrale européenne).

Sert à exprimer le chiffre d'affaires d'Olist en euros ou en dollars.
API utilisée : Frankfurter, gratuite et sans clé.
"""

from datetime import date, timedelta

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


def fetch_rates_range(session, start: date, end: date) -> dict[date, list[dict]]:
    """Taux de change de chaque jour de start à end, en un seul appel à l'API.

    Chaque jour reçoit un enregistrement au même format que fetch_rates, pour que
    le rejeu complet et le traitement quotidien produisent des fichiers identiques.
    """
    # Exemple d'URL : https://api.frankfurter.dev/v1/2017-01-01..2018-08-31?from=BRL&to=EUR,USD
    payload = get_json(
        session,
        f"{config.FX_API_URL}/{start.isoformat()}..{end.isoformat()}",
        params={"from": config.FX_BASE_CURRENCY, "to": ",".join(config.FX_TARGET_CURRENCIES)},
    )
    # Réponse type : {"amount": 1.0, "base": "BRL", "start_date": "2016-12-30", "end_date": ...,
    #                 "rates": {"2016-12-30": {"EUR": 0.2915, "USD": 0.30727}, "2017-01-02": {...}}}
    # Seuls les jours ouvrés de la BCE sont présents. Si la période commence un week-end,
    # l'API ajoute le dernier jour ouvré précédent : on peut donc toujours remonter en arrière.
    rates_by_date = {date.fromisoformat(d): r for d, r in payload["rates"].items()}

    result = {}
    last_rate_date = None
    day = min(rates_by_date) if rates_by_date else start
    while day <= end:
        if day in rates_by_date:
            last_rate_date = day   # nouveau taux publié ce jour-là
        if day >= start and last_rate_date is not None:
            # Même logique que l'API jour par jour : un samedi reçoit le taux du vendredi.
            result[day] = [{"requested_date": day.isoformat(), "amount": payload["amount"],
                            "base": payload["base"], "date": last_rate_date.isoformat(),
                            "rates": rates_by_date[last_rate_date]}]
        day += timedelta(days=1)
    return result
