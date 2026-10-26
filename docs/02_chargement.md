# Étape 2 : chargement dans Cloud Storage puis BigQuery

## Ce que fait `pipeline_meteo.load`

```
data/raw/date=2026-10-26/weather.ndjson                     (fichier local, étape 1)
        │  envoi (écrase le fichier de la même date)
        ▼
gs://<bucket>/raw/openweather/date=2026-10-26/weather.ndjson  (archive brute)
        │  job de chargement BigQuery (remplace la partition du jour)
        ▼
<projet>.meteo_raw.weather_raw   partition 2026-10-26
```

| Colonne | Type | Contenu |
|---|---|---|
| `run_date` | DATE | Date d'exécution, colonne de partition |
| `extracted_at` | TIMESTAMP | Heure UTC de l'appel à l'API |
| `city_name` | STRING | Ville demandée |
| `country` | STRING | Code pays |
| `payload` | JSON | Réponse brute de l'API, non modifiée |

## Pourquoi ces choix

- **Garder le brut intact.** La colonne `payload` conserve toute la réponse de l'API. Si l'API ajoute un champ, ou si un nettoyage se révèle faux, on peut tout recalculer avec dbt sans réinterroger l'API.
- **Une partition par jour.** Les requêtes filtrées sur `run_date` ne lisent que les jours utiles, ce qui réduit le coût dans BigQuery.
- **Relance sans doublon.** Le chargement vise `weather_raw$AAAAMMJJ` en mode `WRITE_TRUNCATE` : il remplace uniquement le jour concerné. On peut relancer une date autant de fois qu'on veut.
- **Contrôle de cohérence.** Le nombre de lignes chargées doit être égal au nombre de lignes du fichier, sinon le traitement échoue. Airflow saura alors qu'il faut relancer.

## Lancer

Prérequis : avoir suivi [01_installation_gcp.md](01_installation_gcp.md) et renseigné `GCP_PROJECT_ID`, `GCS_BUCKET` et `BQ_DATASET_RAW` dans `.env`.

```bash
python -m pipeline_meteo.extract --date 2026-10-26
python -m pipeline_meteo.load --date 2026-10-26
```

## Vérifier dans BigQuery

Dans la console BigQuery, ou avec `bq query --use_legacy_sql=false '...'` :

```sql
-- Une ligne par ville pour la date chargée
SELECT run_date, city_name,
       FLOAT64(payload.main.temp) AS temperature_c,
       STRING(payload.weather[0].description) AS description
FROM `<projet>.meteo_raw.weather_raw`
WHERE run_date = '2026-10-26'
ORDER BY city_name;

-- Après une relance de la même date, le total ne doit pas changer
SELECT run_date, COUNT(*) AS nb_lignes
FROM `<projet>.meteo_raw.weather_raw`
GROUP BY run_date
ORDER BY run_date DESC;
```
