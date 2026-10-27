# Sources de données et chargement

## Les sources

| Source | Type | Contenu | Clé de jointure avec Olist | Usage dans les tableaux de bord |
|---|---|---|---|---|
| **Olist** (Kaggle) | Fichiers CSV, rejoués jour par jour | Commandes, articles, paiements, avis, clients, produits, vendeurs (Brésil, 2016-2018) | — | Chiffre d'affaires, panier moyen, produits, clients, livraisons |
| **Frankfurter** (BCE) | API, sans clé | Taux de change BRL → EUR et USD | date | Montants en euros |
| **Nager.Date** | API, sans clé | Jours fériés brésiliens | date (+ État pour les fêtes locales) | Effet des fêtes sur les ventes |
| **IBGE** | API sans clé, accessible seulement depuis le Brésil : données versionnées dans `dbt/seeds/` | États (sigle, région) et population estimée | sigle de l'État (`SP`, `RJ`...) | Ventes par habitant, analyse régionale |

## Pourquoi « rejouer » Olist

Aucune enseigne ne publie ses ventes réelles par API gratuite. On prend donc un vrai jeu de commandes et on le rejoue : traiter la date D revient à extraire les commandes passées le jour D, ainsi que leurs articles, paiements et avis. Le pipeline se comporte alors comme s'il recevait chaque jour les ventes de la veille, et Airflow peut rejouer toute la période date par date.

**Limite :** les colonnes de livraison et les avis contiennent l'état final de chaque commande, et non l'état connu le jour D.

## Le flux

```
Kaggle (CSV Olist, une fois) ─┐
API Frankfurter ──────────────┤   extraction Python
API Nager.Date ───────────────┤ ─────────────────────► data/raw/<source>/<table>/date=AAAA-MM-JJ/data.ndjson
API IBGE ─────────────────────┘                                │ envoi
                                                                ▼
                                gs://<bucket>/raw/<source>/<table>/date=AAAA-MM-JJ/data.ndjson
                                                                │ chargement (partition du jour remplacée)
                                                                ▼
                                BigQuery : retail_raw.<source>_<table>
```

Deux familles de tables :

- **Quotidiennes**, rechargées pour chaque date : `olist_orders`, `olist_order_items`, `olist_order_payments`, `olist_order_reviews`, `frankfurter_fx_rates`.
- **De référence**, chargées une fois : `olist_customers`, `olist_products`, `olist_sellers`, `olist_category_translation`, `nager_holidays`. Les données IBGE ne passent pas par ce circuit : ce sont des fichiers CSV du dépôt (`dbt/seeds/`), chargés par dbt.

## Un format brut unique

Toutes les tables brutes ont les mêmes 4 colonnes :

| Colonne | Type | Contenu |
|---|---|---|
| `run_date` | DATE | Date traitée, colonne de partition |
| `extracted_at` | TIMESTAMP | Heure réelle de l'extraction |
| `source` | STRING | `olist`, `frankfurter` ou `nager` |
| `record` | JSON | L'enregistrement brut, sans aucune modification |

Pourquoi ce choix :

- **Un seul code de chargement** pour toutes les sources, plutôt qu'un code par table.
- **La couche brute reste fidèle à la source**, valeurs en texte comprises. Le typage (dates, montants), le nettoyage et les jointures se feront dans dbt, où ils sont testés et documentés.
- **Relance sans doublon.** Chaque chargement remplace uniquement la partition de sa date (`WRITE_TRUNCATE` sur `table$AAAAMMJJ`).
- **Contrôle de cohérence.** Le nombre de lignes chargées doit être égal au nombre de lignes du fichier, sinon le traitement échoue.

## Commandes

```bash
python -m pipeline_retail download-olist                        # 1. une seule fois (jeton Kaggle)
python -m pipeline_retail extract-reference --date 2026-10-27   # 2. références
python -m pipeline_retail load --scope reference --date 2026-10-27
python -m pipeline_retail run-daily --date 2017-11-24           # 3. une journée (extraction + chargement)
```

`extract-daily` permet de n'extraire qu'en local, sans Google Cloud : pratique pour explorer les données.

## Vérifier dans BigQuery

```sql
-- Les commandes du Black Friday 2017
SELECT
  JSON_VALUE(record.order_id)                 AS order_id,
  JSON_VALUE(record.order_status)             AS statut,
  JSON_VALUE(record.order_purchase_timestamp) AS achat
FROM `<projet>.retail_raw.olist_orders`
WHERE run_date = '2017-11-24'
LIMIT 10;

-- Nombre de lignes par jour chargé : une relance ne doit pas le modifier
SELECT run_date, COUNT(*) AS nb_commandes
FROM `<projet>.retail_raw.olist_orders`
GROUP BY run_date
ORDER BY run_date DESC;
```
