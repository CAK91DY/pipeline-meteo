"""Lecture de la clé API sans jamais l'écrire dans le code ni dans les logs.

Ordre de recherche :
1. la variable d'environnement OPENWEATHER_API_KEY (développement local, via .env) ;
2. Secret Manager, si OPENWEATHER_SECRET_ID est renseignée (recommandé).
"""

import os


class MissingApiKeyError(RuntimeError):
    """Aucune clé API n'a été trouvée."""


def get_api_key() -> str:
    key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if key:
        return key

    secret_id = os.getenv("OPENWEATHER_SECRET_ID", "").strip()
    if secret_id:
        return _read_from_secret_manager(secret_id)

    raise MissingApiKeyError(
        "Clé API introuvable : renseigner OPENWEATHER_API_KEY ou "
        "OPENWEATHER_SECRET_ID dans le fichier .env (voir .env.example)."
    )


def _read_from_secret_manager(secret_id: str) -> str:
    # Import local : la dépendance n'est nécessaire que pour cette option.
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_id)
    return response.payload.data.decode("utf-8").strip()
