"""Écriture des fichiers bruts au format NDJSON (une ligne JSON par enregistrement).

Toutes les sources produisent le même format de ligne :
    {"run_date": "...", "extracted_at": "...", "source": "...", "record": {...}}

- run_date     : la date logique traitée (pour Olist, la date des commandes rejouées)
- extracted_at : l'heure réelle de l'extraction, pour la traçabilité
- source       : d'où vient la donnée (olist, frankfurter, nager, ibge)
- record       : la donnée brute, sans modification

Ce format unique permet d'utiliser un seul code de chargement pour toutes les
tables. Le typage et le nettoyage des colonnes se feront ensuite dans dbt.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path


def raw_file_path(base_dir: Path, source: str, table: str, run_date: date) -> Path:
    # Exemple : data/raw/olist/orders/date=2017-11-24/data.ndjson
    # Le dossier "date=..." est une convention de partitionnement reconnue
    # par de nombreux outils (BigQuery, DuckDB, Spark).
    return Path(base_dir) / source / table / f"date={run_date.isoformat()}" / "data.ndjson"


def wrap_records(records: list[dict], source: str, run_date: date) -> list[dict]:
    """Ajoute les métadonnées communes autour de chaque enregistrement brut."""
    # Même horodatage pour toutes les lignes d'un même lot.
    extracted_at = datetime.now(timezone.utc).isoformat()
    return [
        {"run_date": run_date.isoformat(), "extracted_at": extracted_at,
         "source": source, "record": record}
        for record in records
    ]


def write_ndjson(rows: list[dict], path: Path) -> Path:
    """Écrit les lignes dans un fichier, de façon atomique et idempotente."""
    path.parent.mkdir(parents=True, exist_ok=True)   # crée les dossiers si besoin
    tmp_path = path.with_suffix(".ndjson.tmp")
    # On écrit d'abord dans un fichier temporaire...
    with open(tmp_path, "w", encoding="utf-8") as f:
        for row in rows:
            # ensure_ascii=False garde les accents lisibles (São Paulo, não...).
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    # ...puis on le renomme d'un coup : jamais de fichier à moitié écrit.
    # S'il existait déjà un fichier pour cette date, il est remplacé (pas de doublon).
    tmp_path.replace(path)
    return path
