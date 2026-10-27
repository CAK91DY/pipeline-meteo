"""Appels HTTP robustes, partagés par toutes les sources de type API."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Au-delà de ce délai (en secondes), on considère que l'API ne répond pas.
REQUEST_TIMEOUT_SECONDS = 30


class ApiError(RuntimeError):
    """Échec d'un appel d'API (réseau ou réponse inattendue)."""


def build_session(total_retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    """Crée une session HTTP qui réessaie automatiquement les erreurs temporaires."""
    retry = Retry(
        total=total_retries,                          # 3 nouvelles tentatives au maximum
        backoff_factor=backoff_factor,                # attente croissante : 1 s, 2 s, 4 s
        status_forcelist=(429, 500, 502, 503, 504),   # trop de requêtes ou erreur serveur
        allowed_methods=("GET",),                     # on ne réessaie que des lectures
        raise_on_status=False,                        # on laisse get_json traiter le code final
    )
    session = requests.Session()
    # Toutes les URL en https:// passeront par cette politique de nouvelles tentatives.
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def get_json(session: requests.Session, url: str, params: dict | None = None):
    """Appelle une URL et renvoie la réponse JSON décodée, ou lève ApiError."""
    try:
        response = session.get(
            url,
            params=params,
            # Certaines API (comme SIDRA) renvoient du XML sauf si l'on demande du JSON.
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        # On ne recopie pas le message d'origine : il contient l'URL complète, qui
        # pourrait un jour contenir un jeton. "from None" coupe la chaîne d'erreurs.
        raise ApiError(f"Erreur réseau sur {url.split('?')[0]} ({type(exc).__name__})") from None

    if response.status_code != 200:
        raise ApiError(f"Réponse HTTP {response.status_code} sur {url.split('?')[0]}")
    return response.json()
