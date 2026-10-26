# Sécurité des clés et des accès

## Principes appliqués

| Risque | Mesure dans le projet |
|---|---|
| Clé API publiée sur GitHub | La clé n'est jamais dans le code. `.env` et les fichiers d'identifiants sont dans `.gitignore`, et seul `.env.example` (vide) est versionné. |
| Clé visible dans les logs ou les erreurs | Les erreurs HTTP sont réécrites sans l'URL (qui contient la clé), et la chaîne d'exceptions est coupée (`from None`). Un test unitaire le vérifie. |
| Clé stockée en clair sur le poste | Option recommandée : la clé vit dans Secret Manager et n'est lue qu'au moment de l'exécution. |
| Fuite d'un fichier de compte de service | Aucune clé JSON n'est créée : authentification par emprunt d'identité, avec des jetons temporaires. |
| Droits trop larges | Compte de service dédié, droits Storage limités au bucket, secret lisible par ce seul compte. |
| Bucket exposé publiquement | Accès uniforme et blocage de l'accès public activés à la création. |
| Dérive des coûts | Alerte budgétaire sur le compte de facturation. |

## Si une clé a fuité

1. Régénérer la clé sur openweathermap.org et supprimer l'ancienne.
2. Ajouter une nouvelle version du secret :
   `read -s OWM_KEY; printf '%s' "$OWM_KEY" | gcloud secrets versions add openweather-api-key --data-file=-; unset OWM_KEY`
3. Si la clé a été poussée sur GitHub, la supprimer du dépôt ne suffit pas : l'historique la conserve. La régénération (point 1) est la seule protection fiable.

## Vérification avant chaque commit

```bash
git status            # .env ne doit jamais apparaître
git diff --cached     # relire ce qui part
```
