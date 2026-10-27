# Sécurité des clés et des accès

## Principes appliqués

| Risque | Mesure dans le projet |
|---|---|
| Jeton publié sur GitHub | Le jeton Kaggle n'est jamais dans le code. `.env` et les fichiers d'identifiants sont dans `.gitignore`, et seul `.env.example` (vide) est versionné. |
| Secret visible dans les logs ou les erreurs | Les erreurs HTTP sont réécrites sans l'URL complète (qui pourrait contenir un secret), et la chaîne d'exceptions est coupée (`from None`). Un test unitaire le vérifie. |
| Jeton stocké en clair sur le poste | Option recommandée : le jeton vit dans Secret Manager et n'est lue qu'au moment de l'exécution. |
| Fuite d'un fichier de compte de service | Aucune clé JSON n'est créée : authentification par emprunt d'identité, avec des jetons temporaires. |
| Droits trop larges | Compte de service dédié, droits Storage limités au bucket, secret lisible par ce seul compte. |
| Bucket exposé publiquement | Accès uniforme et blocage de l'accès public activés à la création. |
| Dérive des coûts | Alerte budgétaire sur le compte de facturation. |

## Si le jeton a fuité

1. Sur kaggle.com, dans *Settings > API*, révoquer l'ancien jeton et en générer un nouveau.
2. Ajouter une nouvelle version du secret :
   `read -s KAGGLE_TOKEN; printf '%s' "$KAGGLE_TOKEN" | gcloud secrets versions add kaggle-api-token --data-file=-; unset KAGGLE_TOKEN`
3. Si le jeton a été poussé sur GitHub, la supprimer du dépôt ne suffit pas : l'historique la conserve. La régénération (point 1) est la seule protection fiable.

## Bonnes pratiques à retenir

- Le vrai secret va dans `.env`, jamais dans `.env.example` : ce dernier est publié sur GitHub.
- Avant d'envoyer une capture d'écran, masquer les jetons et les clés qui y apparaissent.

## Vérification avant chaque commit

```bash
git status            # .env ne doit jamais apparaître
git diff --cached     # relire ce qui part
```
