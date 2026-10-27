"""Source principale : les commandes e-commerce Olist (Brésil, 2016-2018).

Olist est un jeu de données historique distribué sous forme de fichiers CSV sur
Kaggle. Pour simuler un flux quotidien comme celui d'une vraie API, on le
« rejoue » : traiter la date D revient à extraire les commandes passées le jour D,
ainsi que leurs articles, paiements et avis. Airflow pourra rejouer toute la
période date par date.

Limite connue du rejeu : les colonnes de livraison et les avis contiennent l'état
final de la commande, pas l'état connu le jour D. À garder en tête dans l'analyse.
"""

import csv
import logging
import os
from datetime import date
from pathlib import Path

from pipeline_retail import config
from pipeline_retail.secrets import get_secret

logger = logging.getLogger(__name__)


class OlistSourceError(RuntimeError):
    """Fichier Olist manquant ou illisible."""


def download_dataset(dest_dir: Path = config.OLIST_SOURCE_DIR) -> Path:
    """Télécharge les CSV Olist depuis Kaggle (à faire une seule fois)."""
    # Le jeton Kaggle est lu dans .env ou Secret Manager, jamais écrit dans le code.
    # La bibliothèque kaggle le cherche dans la variable KAGGLE_API_TOKEN :
    # on la renseigne uniquement pour ce processus, pas dans un fichier.
    os.environ["KAGGLE_API_TOKEN"] = get_secret("KAGGLE_API_TOKEN")

    # Import tardif : la bibliothèque kaggle tente de s'authentifier dès l'import.
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    dest_dir.mkdir(parents=True, exist_ok=True)
    # unzip=True : Kaggle envoie une archive .zip, on récupère directement les CSV.
    api.dataset_download_files(config.OLIST_KAGGLE_DATASET, path=str(dest_dir),
                               unzip=True, quiet=False)
    check_files(dest_dir)
    logger.info("Jeu Olist téléchargé dans %s", dest_dir)
    return dest_dir


def check_files(source_dir: Path) -> None:
    """Vérifie que tous les CSV attendus sont présents."""
    missing = [name for name in config.OLIST_FILES.values()
               if not (Path(source_dir) / name).exists()]
    if missing:
        raise OlistSourceError(
            f"Fichiers Olist manquants dans {source_dir} : {missing}. "
            "Lancer d'abord : python -m pipeline_retail download-olist"
        )


def read_table(source_dir: Path, table: str) -> list[dict]:
    """Lit un CSV Olist et renvoie une liste de dictionnaires (une ligne = un dict)."""
    path = Path(source_dir) / config.OLIST_FILES[table]
    if not path.exists():
        raise OlistSourceError(f"Fichier introuvable : {path}")
    # utf-8-sig retire le caractère invisible (BOM) présent au début de certains CSV.
    # newline="" laisse le module csv gérer les retours à la ligne dans les avis clients.
    with open(path, encoding="utf-8-sig", newline="") as f:
        # Les valeurs restent du texte : on garde la donnée brute telle quelle.
        return list(csv.DictReader(f))


def extract_daily(source_dir: Path, run_date: date) -> dict[str, list[dict]]:
    """Rejoue une journée : les commandes du jour et tout ce qui leur est rattaché."""
    return extract_range(source_dir, run_date, run_date)[run_date]


def extract_range(source_dir: Path, start: date, end: date) -> dict[date, dict[str, list[dict]]]:
    """Rejoue toutes les journées de start à end (incluses) en lisant les CSV une seule fois.

    Renvoie {jour: {"orders": [...], "order_items": [...], ...}}. Chaque jour de la
    période est présent, même sans commande : un fichier vide dit « rien ce jour-là »,
    alors qu'un fichier absent laisserait croire que le jour n'a pas été traité.
    """
    # 1. Une entrée vide par jour de la période (toordinal numérote les jours, pour boucler simplement).
    days = [date.fromordinal(n) for n in range(start.toordinal(), end.toordinal() + 1)]
    result = {day: {"orders": [], "order_items": [], "order_payments": [], "order_reviews": []}
              for day in days}

    # 2. Les commandes, rangées selon leur date d'achat.
    #    order_purchase_timestamp ressemble à "2017-11-24 10:15:32" :
    #    les 10 premiers caractères donnent la date.
    day_of_order = {}   # order_id -> jour d'achat, pour ranger ensuite les autres tables
    for row in read_table(source_dir, "orders"):
        day = date.fromisoformat(row["order_purchase_timestamp"][:10])
        if day in result:   # on ignore les commandes hors période
            result[day]["orders"].append(row)
            day_of_order[row["order_id"]] = day

    # 3. Les articles, paiements et avis suivent le jour de leur commande.
    for table in ("order_items", "order_payments", "order_reviews"):
        for row in read_table(source_dir, table):
            day = day_of_order.get(row["order_id"])   # None si la commande est hors période
            if day is not None:
                result[day][table].append(row)

    n_orders = sum(len(tables["orders"]) for tables in result.values())
    n_items = sum(len(tables["order_items"]) for tables in result.values())
    period = str(start) if start == end else f"du {start} au {end}"
    logger.info("Olist %s : %d commandes, %d articles", period, n_orders, n_items)
    return result


def extract_reference(source_dir: Path) -> dict[str, list[dict]]:
    """Tables de référence : clients, produits, vendeurs, traduction des catégories."""
    return {table: read_table(source_dir, table)
            for table in ("customers", "products", "sellers", "category_translation")}
