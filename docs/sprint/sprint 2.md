# Sprint 2 — Socle et chaîne CI/CD

## Ressources

- [grille-atelier-2-socle-chaine.pdf](grille-atelier-2-socle-chaine.pdf)

## Contexte du projet

Déployer un **squelette de bout en bout qui marche** : API + interface minimale + un appel LLM qui répond, livré par une chaîne CI/CD bloquante jusqu'à la production.

Rien de fonctionnellement riche, mais tout est branché, et tout ce qui suivra sera livré par cette chaîne. C'est l'inverse du prototype qui ne tourne que « sur ma machine » : à partir de ce sprint, « ça marche ailleurs » n'est plus un jalon, c'est l'état permanent du projet.

## Travail attendu

1. **Monter le repo propre** : structure, environnements reproductibles (Docker), secrets hors du dépôt.
2. **Développer le squelette** : une route API, une interface minimale, un appel au LLM qui répond.
3. **Construire la chaîne** : lint → tests → build → déploiement automatique sur merge / PR, à travers les environnements.
4. **Rendre les tests bloquants et le prouver** : un commit volontairement cassé doit être arrêté par la chaîne.
5. **Mettre en place et répéter le rollback** : revenir à la version précédente en une opération.

## Modalités d'évaluation

Évaluation par un pair.

- [ ] Le squelette tourne ailleurs que sur la machine du présenté : l'évaluateur le constate sur l'URL de production.
- [ ] Une fusion déclenche la livraison sans action manuelle : démontré en live ou journal de chaîne à l'appui.
- [ ] Un commit cassé est bloqué : démontré en live.
- [ ] Le rollback est montré.
- [ ] Les secrets ne sont pas dans le dépôt ; l'environnement se reconstruit depuis le repo.
- [ ] Journal des retours : les retours sur l'atelier n°1 ont été traités, reportés ou écartés.

## Livrables

- Le squelette en production, livré par la chaîne.
- La preuve du blocage sur échec et du rollback (captures ou journal de chaîne versionnés).
