# Pipeline météo : API → Cloud Storage → BigQuery → dbt, orchestré par Airflow

Pipeline de données quotidien sur Google Cloud. Il extrait la météo de plusieurs villes françaises depuis l'API OpenWeatherMap, conserve la réponse brute dans Cloud Storage, la charge dans BigQuery, puis la transforme avec dbt. Airflow, lancé en local avec Docker Compose, planifie les étapes, gère les erreurs et permet de relancer une date.

## Avancement

| Étape | Contenu | État |
|---|---|---|
| 1. Fondations | Extraction Python, gestion sécurisée de la clé, ressources GCP | Fait |
| 2. Chargement | Envoi dans Cloud Storage, chargement idempotent dans BigQuery | Fait |
| 3. Transformation et orchestration | Modèles et tests dbt, DAG Airflow (Docker Compose) | À faire |
| 4. Documentation portfolio | Architecture, choix techniques, limites | À faire |

## Structure

```
config/cities.json          villes interrogées (nom, latitude, longitude)
pipeline_meteo/extract.py   extraction API → NDJSON partitionné par date
pipeline_meteo/secrets.py   lecture de la clé (.env ou Secret Manager)
pipeline_meteo/load.py      envoi dans Cloud Storage puis chargement BigQuery
tests/                      tests unitaires (sans appel réseau)
docs/                       installation GCP et sécurité
```

## Démarrage rapide

1. Préparer Google Cloud et la clé API : [docs/01_installation_gcp.md](docs/01_installation_gcp.md)
2. Installer et lancer :

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # puis renseigner les valeurs
pytest
python -m pipeline_meteo.extract --date 2026-10-26
python -m pipeline_meteo.load --date 2026-10-26
```

Le fichier produit est `data/raw/date=2026-10-26/weather.ndjson`, avec une ligne par ville. Le chargement le copie dans Cloud Storage, puis dans la table BigQuery `meteo_raw.weather_raw` (détails : [docs/02_chargement.md](docs/02_chargement.md)). Relancer la même date remplace les données de ce jour, sans créer de doublon.

## Sécurité

La clé API n'est jamais dans le code ni dans les logs. Voir [docs/securite_cles_api.md](docs/securite_cles_api.md).
