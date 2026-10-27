# Pipeline retail : Olist enrichi, de l'API à BigQuery, orchestré par Airflow

Pipeline de données quotidien sur Google Cloud, conçu pour alimenter des **tableaux de bord retail** : chiffre d'affaires, saisonnalité, baisse des ventes, produits, régions, livraisons.

- **Source principale :** les commandes e-commerce [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Brésil, 2016-2018), rejouées jour par jour comme un flux quotidien.
- **Enrichissements par API :** taux de change BRL/EUR (BCE), jours fériés brésiliens, population et régions par État (IBGE).
- **Chaîne :** extraction Python → Cloud Storage (brut) → BigQuery → dbt → tableaux de bord Looker Studio, le tout orchestré par Airflow.

## Avancement

| Étape | Contenu | État |
|---|---|---|
| 1. Fondations | Code d'extraction, gestion sécurisée des secrets, ressources GCP | Fait |
| 2. Chargement | Envoi dans Cloud Storage, chargement idempotent dans BigQuery | Fait |
| 3. Exploration | Notebook : qualité des données, saisonnalité, pièges du jeu | À faire |
| 4. Transformation et orchestration | Modèles et tests dbt, DAG Airflow (Docker Compose) | À faire |
| 5. Tableaux de bord et documentation | Looker Studio, architecture, choix techniques, limites | À faire |

## Structure

```
pipeline_retail/
  config.py            paramètres centraux (URL, fichiers, liste des tables)
  secrets.py           lecture des secrets (.env ou Secret Manager)
  http.py              appels d'API avec nouvelles tentatives et erreurs sans secret
  storage.py           écriture des fichiers bruts NDJSON
  load.py              envoi Cloud Storage puis chargement BigQuery
  cli.py               les commandes du pipeline
  sources/
    olist.py           téléchargement Kaggle et rejeu jour par jour
    fx_rates.py        taux de change (Frankfurter)
    holidays.py        jours fériés (Nager.Date)
    ibge.py            États et population (IBGE)
tests/                 tests unitaires (sans réseau ni Google Cloud)
docs/                  installation, sources et chargement, sécurité
```

## Démarrage rapide

1. Préparer Google Cloud et le jeton Kaggle : [docs/01_installation_gcp.md](docs/01_installation_gcp.md)
2. Installer et lancer :

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env                       # puis renseigner les valeurs dans .env
pytest
python -m pipeline_retail download-olist   # télécharge les CSV Olist (une fois)
python -m pipeline_retail extract-daily --date 2017-11-24
```

La dernière commande écrit les commandes du Black Friday 2017 et le taux de change du jour dans `data/raw/`, sans avoir besoin de Google Cloud. Le chargement dans BigQuery est décrit dans [docs/02_sources_et_chargement.md](docs/02_sources_et_chargement.md).

## Sécurité

Le jeton Kaggle n'est jamais dans le code ni dans les logs. Voir [docs/securite_cles_api.md](docs/securite_cles_api.md).
