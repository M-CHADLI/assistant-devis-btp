# Sprint 3 — Données et ancrage

## Ressources

- [grille-atelier-3-donnees-ancrage-.pdf](grille-atelier-3-donnees-ancrage-.pdf)

## Contexte du projet

Brancher le projet sur ses données : ingestion, stockage, et le mécanisme d'ancrage qui convient au sujet (RAG, SQL, les deux, ou autre).

À la fin du sprint, l'application répond **à partir de ses données, en citant ses sources**, et **refuse proprement** ce qui sort de son corpus ou de son périmètre, livrée par la chaîne du sprint 2.

## Travail attendu

1. **Construire le pipeline d'ingestion** adapté au projet : collecte, nettoyage, chunking et métadonnées de traçabilité (ou schéma et chargement pour une base structurée). Il doit être rejouable sur demande.
2. **Choisir et poser le stockage** : base vectorielle, base relationnelle, ou les deux.
3. **Implémenter l'ancrage** : retrieval (avec les avancées de Phase 3 si le projet les justifie), SQL sécurisé, ou injection de contexte frais.
4. **Garantir la traçabilité** : chaque réponse cite sa source (document, table, identifiant, date).
5. **Implémenter le refus** hors corpus / hors périmètre sous un seuil de pertinence.
6. **Appliquer la minimisation RGPD** avant indexation si les données le demandent, et documenter ce choix.

## Modalités d'évaluation

Évaluation par un pair.

- [ ] Les sources de données sont identifiées et licites (RGPD : minimisation appliquée ou non-applicabilité argumentée).
- [ ] Les réponses sont traçables : l'évaluateur pose une question et remonte à la source citée.
- [ ] Le refus hors corpus est démontré : l'évaluateur pose lui-même une question hors sujet.
- [ ] Le pipeline d'ingestion est rejouable (une commande, pas une suite de manipulations).
- [ ] Tout est visible en production, pas dans un notebook.
- [ ] Journal des retours tenu.

## Livrables

- L'application en production répond à partir des données du projet, sources citées.
- Le pipeline d'ingestion est rejouable.
- Un jeu de 5 à 10 questions de démonstration (couvertes + hors corpus) est versionné.
