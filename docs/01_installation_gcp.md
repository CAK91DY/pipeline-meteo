# Installation : Google Cloud et jeton Kaggle

Ce guide prépare tout ce dont le pipeline a besoin. Compter environ 30 minutes.
Les commandes se lancent dans un terminal où le [SDK Google Cloud](https://cloud.google.com/sdk/docs/install) (`gcloud`, `bq`) est installé.

## 0. Prérequis

- Un compte Google et un compte de facturation (l'essai gratuit de Google Cloud suffit).
- Python 3.11 ou plus récent.
- Un jeton Kaggle, pour télécharger le jeu Olist : créer un compte sur [kaggle.com](https://www.kaggle.com), puis dans *Settings > API*, cliquer sur *Generate New Token* et copier le jeton affiché.
- Les autres sources (taux de change, jours fériés) sont des API publiques sans clé. Les données de l'IBGE sont fournies dans le dépôt (`dbt/seeds/`).

## 1. Variables utilisées dans ce guide

Adapter les valeurs, puis coller ces lignes dans le terminal :

```bash
export PROJECT_ID="pipeline-retail-$RANDOM"          # identifiant unique au monde
export REGION="EU"                                   # données hébergées en Europe
export BUCKET="${PROJECT_ID}-raw"
export SA_NAME="sa-pipeline-retail"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export MY_EMAIL="ton.adresse@gmail.com"              # le compte Google utilisé
echo "$PROJECT_ID"                                   # à noter pour le fichier .env
```

## 2. Créer le projet et activer les API

```bash
gcloud auth login
gcloud projects create "$PROJECT_ID" --name="Pipeline retail"
gcloud config set project "$PROJECT_ID"

gcloud billing accounts list                         # repérer l'ACCOUNT_ID
gcloud billing projects link "$PROJECT_ID" --billing-account=ACCOUNT_ID

gcloud services enable storage.googleapis.com bigquery.googleapis.com \
  secretmanager.googleapis.com iamcredentials.googleapis.com
```

**Conseillé :** créer une alerte budgétaire (par exemple 5 €) dans la console, menu *Facturation > Budgets et alertes*. Le volume de ce projet reste très faible, mais l'alerte protège d'une erreur de configuration.

## 3. Créer le bucket Cloud Storage (données brutes)

```bash
gcloud storage buckets create "gs://${BUCKET}" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --public-access-prevention
```

L'accès uniforme et le blocage de l'accès public garantissent que le bucket ne peut pas être rendu public par erreur.

## 4. Créer le dataset BigQuery de la couche brute

```bash
bq --location="$REGION" mk --dataset "${PROJECT_ID}:retail_raw"
```

Les datasets de transformation seront créés par dbt à l'étape 3.

## 5. Créer le compte de service du pipeline (droits minimaux)

Le pipeline n'utilise pas ton compte personnel, mais un compte de service qui n'a que les droits nécessaires.

```bash
gcloud iam service-accounts create "$SA_NAME" --display-name="Pipeline retail"

# Lire et écrire des fichiers, uniquement dans ce bucket
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/storage.objectAdmin"

# Lancer des requêtes et écrire dans les tables BigQuery du projet
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/bigquery.jobUser"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/bigquery.dataEditor"
```

`bigquery.dataEditor` est attribué au niveau du projet parce que dbt doit pouvoir créer ses propres datasets. C'est acceptable ici, car le projet est dédié au pipeline. En entreprise, on le restreindrait à chaque dataset.

## 6. Stocker le jeton Kaggle dans Secret Manager

La saisie avec `read -s` évite que le jeton apparaisse à l'écran ou dans l'historique du terminal :

```bash
read -s -p "Jeton Kaggle : " KAGGLE_TOKEN; echo
printf '%s' "$KAGGLE_TOKEN" | gcloud secrets create kaggle-api-token \
  --replication-policy="automatic" --data-file=-
unset KAGGLE_TOKEN

# Seul le compte de service peut lire ce secret
gcloud secrets add-iam-policy-binding kaggle-api-token \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor"
```

## 7. S'authentifier en local sans fichier de clé JSON

On ne télécharge pas de clé JSON pour le compte de service. Ces fichiers sont la première cause de fuite d'identifiants, et les nouveaux projets bloquent souvent leur création. On utilise plutôt l'**emprunt d'identité** : ton compte Google obtient des jetons temporaires au nom du compte de service.

```bash
# Autoriser ton compte à emprunter l'identité du compte de service
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="user:${MY_EMAIL}" --role="roles/iam.serviceAccountTokenCreator"

# Identifiants locaux utilisés par les bibliothèques Python
gcloud auth application-default login --impersonate-service-account="$SA_EMAIL"
```

La propagation des droits IAM peut prendre une ou deux minutes.

## 8. Vérifier

```bash
gcloud secrets versions access latest --secret=kaggle-api-token \
  --impersonate-service-account="$SA_EMAIL" > /dev/null && echo "Secret lisible : OK"
gcloud storage ls "gs://${BUCKET}" && echo "Bucket accessible : OK"
bq ls "${PROJECT_ID}:retail_raw" && echo "Dataset accessible : OK"
```

## 9. Configurer le projet et lancer l'extraction

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Dans `.env`, laisser `KAGGLE_API_TOKEN` vide et renseigner :

```
KAGGLE_API_TOKEN_SECRET_ID=projects/<PROJECT_ID>/secrets/kaggle-api-token/versions/latest
GCP_PROJECT_ID=<PROJECT_ID>
GCS_BUCKET=<PROJECT_ID>-raw
```

Puis :

```bash
pytest                                   # tests unitaires, sans appel réseau
python -m pipeline_retail download-olist                      # une seule fois
python -m pipeline_retail extract-reference --date 2026-10-27  # tables de référence
python -m pipeline_retail load --scope reference --date 2026-10-27
python -m pipeline_retail run-daily --date 2017-11-24          # une journée d'Olist
```
