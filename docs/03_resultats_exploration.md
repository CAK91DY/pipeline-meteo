# Résultats de l'exploration Olist

Synthèse du notebook [01_exploration_olist.ipynb](../notebooks/01_exploration_olist.ipynb), exécuté le 27/10/2026 sur le jeu Olist complet. Le notebook est versionné sans ses sorties : on le relance pour retrouver ces chiffres.

## Chiffres clés

| Indicateur | Valeur |
|---|---|
| Commandes dans le fichier | 99 441 |
| Fenêtre d'analyse retenue | du 01/02/2017 au 21/08/2018 |
| Commandes valides dans la fenêtre | 96 440 |
| Chiffre d'affaires marchandises dans la fenêtre | 13,25 M BRL |
| Taux d'annulation ou d'indisponibilité | 1,2 % |
| Jour le plus fort | lundi (+20 % par rapport à la tendance) |
| Jour le plus faible | samedi (-24 %) |
| Jours de baisse anormale (score robuste < -3) | 19 |
| Livraisons en retard sur la date annoncée | 6,8 % |
| Catégories de produits | 74, dont les 10 premières font 62 % du CA |

## Ce que l'on a appris

**1. Les bords du jeu de données sont trompeurs.**
- Les mois avant février 2017 sont trop clairsemés pour être comparés aux suivants.
- À partir du 22/08/2018, les commandes baissent chaque jour jusqu'à zéro. C'est l'arrêt de la collecte, pas une chute des ventes.
- Sans coupure, un tableau de bord afficherait une fausse croissance au début et une fausse chute à la fin.

**2. La saisonnalité hebdomadaire est nette.** On achète surtout en début de semaine et nettement moins le week-end. Cet effet se répète sur plus de 80 semaines, il est donc fiable.

**3. Le Black Friday 2017 est l'événement majeur.** La semaine du 24/11/2017 approche 400 000 BRL de chiffre d'affaires, soit plus du double des semaines précédentes (environ 150 000 à 175 000 BRL).

**4. Les baisses détectées et leurs explications.** Ce sont des *hypothèses* : l'analyse montre des coïncidences dans le temps, pas des causes.

| Période | Baisse | Explication probable |
|---|---|---|
| 24, 25 et 31 décembre 2017, 1er janvier 2018 | jusqu'à -74 % sur la journée | Fêtes de fin d'année (effet calendrier) |
| Semaine du 10 au 16 avril 2017 | environ -35 % | Pâques (Vendredi saint le 14 avril) |
| Semaine du 21 au 27 mai 2018 | -47 % | Grève des camionneurs au Brésil (21 au 31 mai 2018) |
| Semaines du 2 au 15 juillet 2018 | -17 à -22 % | Fin de la Coupe du monde (piste fragile) |

**5. Une seule année complète.** Avec 2017 seulement, on ne peut pas affirmer que « novembre est toujours fort » : la saisonnalité annuelle reste une hypothèse.

## Pistes à vérifier

- **Grève de mai 2018.** Les délais de livraison des commandes passées entre le 21 et le 31 mai doivent être nettement plus longs que d'habitude. Si c'est le cas, l'hypothèse est renforcée.
- **Coupe du monde.** Les commandes des jours de match du Brésil, aux heures des matchs, doivent être plus faibles que les mêmes heures des autres jours.

## Conséquences pour la suite

Les règles de nettoyage et de calcul sont listées à la fin du notebook (section 9). Elles deviennent les modèles et les tests dbt de l'étape 4. La règle de fenêtre (mois complets, coupure à la fin de la collecte) sera portée par la dimension date, pour que les tableaux de bord ne montrent jamais les artefacts des bords.
