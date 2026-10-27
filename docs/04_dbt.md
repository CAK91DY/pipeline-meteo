# Transformations dbt (en local avec DuckDB)

dbt transforme les fichiers bruts en tables propres, testées et prêtes pour les tableaux de bord. En local, la base est un simple fichier DuckDB (`data/retail.duckdb`) : rien à installer côté serveur. Le même SQL tournera ensuite sur BigQuery.

## Lancer

Depuis la racine du projet, avec le `.venv` activé :

```bash
python -m pip install -r requirements-dev.txt
python -m pipeline_retail backfill --start 2016-09-01 --end 2018-10-31
python -m pipeline_retail extract-reference --date 2026-10-27
cd dbt
dbt build --profiles-dir .
```

- `backfill` rejoue toutes les journées d'Olist d'un coup. Il lit les CSV une seule fois et récupère les taux de change en un seul appel. Le résultat est identique à `extract-daily` lancé jour par jour.
- `extract-reference` récupère les tables de référence : clients, produits, jours fériés, États et population.
- `dbt build` construit toutes les tables et exécute les tests. Chaque ligne doit finir en `PASS` ou `OK`.

Pour explorer le résultat :

```bash
dbt show --profiles-dir . --inline "select * from {{ ref('fct_daily_sales') }}" --limit 10
```

## Organisation

```
dbt/
  dbt_project.yml        paramètres, dont la fenêtre d'analyse (analysis_start, analysis_end)
  profiles.yml           connexion DuckDB (et BigQuery, commentée pour plus tard)
  macros/                fonctions SQL qui diffèrent entre DuckDB et BigQuery
  models/staging/        une table propre par table brute (types, doublons)
  models/marts/          faits et dimensions pour les tableaux de bord
  tests/                 tests de cohérence écrits à la main
```

| Table | Une ligne = | Usage |
|---|---|---|
| `marts.fct_orders` | une commande | CA en BRL et EUR, statut, délai, retard, note |
| `marts.fct_order_items` | un article vendu | catégories, produits, vendeurs |
| `marts.fct_daily_sales` | un jour de la fenêtre d'analyse | courbes, saisonnalité, baisses |
| `marts.dim_date` | un jour | jour de la semaine, fériés, Black Friday, fenêtre |
| `marts.dim_products` | un produit | catégorie en anglais (ou `unknown`) |
| `marts.dim_states` | un État | région, population pour le CA par habitant |

## Les règles appliquées

Elles viennent de l'exploration (voir [03_resultats_exploration.md](03_resultats_exploration.md)) :

- **Chiffre d'affaires.** C'est la somme des prix des articles. Les frais de port sont suivis à part.
- **Statuts exclus.** Les commandes `canceled` et `unavailable` sont exclues du chiffre d'affaires (colonne `is_valid`).
- **Avis.** On garde un avis par commande, le plus récent.
- **Fenêtre d'analyse.** Elle va du 01/02/2017 au 21/08/2018. `fct_daily_sales` ne contient que cette période, et `dim_date.is_in_analysis_window` permet de filtrer les autres tables.
- **Conversion en euros.** Elle utilise le taux du jour d'achat. Le week-end, c'est le taux du vendredi.

## Les tests

`dbt build` vérifie notamment :

- **Unicité et présence des clés.** Les identifiants de commande, d'article, de produit et de jour sont uniques et jamais vides.
- **Liens entre tables.** Chaque article pointe vers une commande et un produit existants, et chaque État client existe dans l'IBGE.
- **Valeurs attendues.** Les statuts, les notes de 1 à 5 et les jours de 1 à 7 restent dans leurs listes.
- **Cohérence.** Le chiffre d'affaires quotidien est égal, au centime près, à la somme des commandes (`tests/assert_daily_sales_match_orders.sql`).

## Passer à BigQuery (plus tard)

Les différences de SQL entre les deux bases sont isolées dans `macros/` (lecture du JSON, calendrier, conversions). Pour basculer, il faudra :

1. Créer le projet Google Cloud ([01_installation_gcp.md](01_installation_gcp.md)).
2. Charger les données brutes avec `python -m pipeline_retail load`.
3. Installer `dbt-bigquery`, puis décommenter la cible `bigquery` dans `profiles.yml`.
4. Lancer `dbt build --profiles-dir . --target bigquery`.

Ce passage n'a pas encore été testé sur un vrai projet BigQuery.
