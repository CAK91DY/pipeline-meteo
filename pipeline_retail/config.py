"""Paramètres centraux du pipeline.

Tout ce qui pourrait changer (URL d'API, noms de fichiers, liste des tables)
est regroupé ici. Le reste du code importe ces constantes : pour modifier un
paramètre, on ne touche qu'à ce fichier.
"""

from pathlib import Path

# Dossier racine du projet (le dossier qui contient pipeline_retail/).
# __file__ est le chemin de ce fichier ; .parent remonte d'un dossier.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dossier local où l'on télécharge les CSV Olist depuis Kaggle (exclu de Git).
OLIST_SOURCE_DIR = PROJECT_ROOT / "data" / "olist_source"

# Dossier local où l'on écrit les fichiers bruts avant de les envoyer dans le cloud.
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# --- Olist (Kaggle) -----------------------------------------------------------

# Identifiant du jeu de données sur Kaggle : "propriétaire/nom".
OLIST_KAGGLE_DATASET = "olistbr/brazilian-ecommerce"

# Nom court de chaque table -> nom du fichier CSV fourni par Olist.
OLIST_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# --- API d'enrichissement (gratuites, sans clé) -------------------------------

# Taux de change de la Banque centrale européenne, servis par Frankfurter.
FX_API_URL = "https://api.frankfurter.dev/v1"
FX_BASE_CURRENCY = "BRL"            # la monnaie d'Olist : le réal brésilien
FX_TARGET_CURRENCIES = ("EUR", "USD")

# Jours fériés par pays et par année.
HOLIDAYS_API_URL = "https://date.nager.at/api/v3/PublicHolidays"
HOLIDAYS_COUNTRY = "BR"

# Institut brésilien de statistique (IBGE).
IBGE_STATES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
# Table SIDRA 6579 = population résidente estimée, n3 = niveau "État".
IBGE_POPULATION_URL = "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/all/p/{year}"

# Années couvertes par Olist : on charge les références (fériés, population) pour chacune.
OLIST_YEARS = (2016, 2017, 2018)

# --- Tables du pipeline -------------------------------------------------------

# Chaque table brute est identifiée par (source, table).
# "daily" : rechargées pour chaque date traitée (les faits du jour).
DAILY_TABLES = (
    ("olist", "orders"),
    ("olist", "order_items"),
    ("olist", "order_payments"),
    ("olist", "order_reviews"),
    ("frankfurter", "fx_rates"),
)

# "reference" : tables de référence, chargées une fois puis rarement mises à jour.
REFERENCE_TABLES = (
    ("olist", "customers"),
    ("olist", "products"),
    ("olist", "sellers"),
    ("olist", "category_translation"),
    ("nager", "holidays"),
    ("ibge", "states"),
    ("ibge", "population"),
)
