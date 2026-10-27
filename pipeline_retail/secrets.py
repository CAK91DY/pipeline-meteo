"""Lecture des secrets (jetons, clés) sans jamais les écrire dans le code.

Ordre de recherche pour un secret nommé NOM :
1. la variable d'environnement NOM (développement local, via le fichier .env) ;
2. Secret Manager, si la variable NOM_SECRET_ID contient l'identifiant du secret.
"""

import os


class MissingSecretError(RuntimeError):
    """Le secret demandé n'a été trouvé nulle part."""


def get_secret(name: str) -> str:
    # 1. Variable d'environnement : os.getenv renvoie "" si elle n'existe pas,
    #    et .strip() retire les espaces ou retours à la ligne copiés par erreur.
    value = os.getenv(name, "").strip()
    if value:
        return value

    # 2. Secret Manager : on cherche l'identifiant complet du secret,
    #    par exemple projects/mon-projet/secrets/kaggle-api-token/versions/latest
    secret_id = os.getenv(f"{name}_SECRET_ID", "").strip()
    if secret_id:
        return _read_from_secret_manager(secret_id)

    # Rien trouvé : on arrête tout avec un message qui dit quoi faire.
    raise MissingSecretError(
        f"Secret introuvable : renseigner {name} ou {name}_SECRET_ID "
        "dans le fichier .env (voir .env.example)."
    )


def _read_from_secret_manager(secret_id: str) -> str:
    # Import placé ici : la bibliothèque n'est chargée que si on utilise cette option.
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_id)
    # Le secret est stocké en octets : on le convertit en texte.
    return response.payload.data.decode("utf-8").strip()
