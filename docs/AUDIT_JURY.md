# Audit critère par critère du référentiel RNCP

> **À quoi sert ce document.** `docs/LIVRABLES.md` regarde la couverture au
> niveau de la *compétence*. Ici on descend d'un cran : les **135 critères
> d'évaluation** que le jury coche un par un, extraits de
> `reference/referentiel-rncp-ai-engineer.xlsx`, confrontés à l'**état constaté
> du dépôt** au 08/09/2026 (commit `a019878`).
>
> Même règle que la grille de contrôle : **on ne dénature pas le projet pour
> cocher une case.** Un critère hors périmètre est écrit comme tel, avec la
> raison — c'est plus défendable devant un jury qu'une case cochée de travers.

**Convention.** ✅ couvert, preuve dans le dépôt · 🟡 partiel, il manque quelque
chose de nommé · ❌ absent · ➖ écarté, avec motif assumé.

## Le compte

| Livrable | Critères | ✅ | 🟡 | ❌ | ➖ |
|---|---|---|---|---|---|
| E1 — Données (C1-C5) | 28 | 1 | 5 | 21 | 1 |
| E2 — Veille et IA préexistante (C6-C8) | 20 | 5 | 7 | 8 | 0 |
| E3 — Modèle IA (C9-C13) | 39 | 11 | 9 | 19 | 0 |
| E4 — Application (C14-C19) | 36 | 8 | 9 | 19 | 0 |
| E5 — Exploitation (C20-C21) | 12 | 0 | 3 | 9 | 0 |
| **Total** | **135** | **25** | **33** | **76** | **1** |

Le compte est **volontairement sévère** : un critère n'est ✅ que si la preuve
est dans le dépôt aujourd'hui, pas si elle est prévue. Trois mois de calendrier
restent (`PLANNING.md`), et l'essentiel des ❌ sont des livrables de rédaction
ou d'outillage, pas des impasses de conception.

---

## Deux constats qui coûtent cher, et qui se règlent vite

**1. Il n'y a pas de dépôt Git distant.** `git remote -v` ne renvoie rien. Or
**neuf critères** exigent explicitement « versionné et accessible depuis un
dépôt Git **distant** » : C1-8, C3-16, C4-24, C9-62, C11-83, C12-91, C17-129,
C18-136, C19-143. C'est aujourd'hui le plus gros gisement de points perdus du
référentiel, et le moins cher à combler — un `git remote add` puis un `push`.
Rien d'autre dans le dépôt ne bloque ces neuf critères.

**2. Trois exigences transverses reviennent partout.** L'accessibilité est citée
dans **huit** compétences, et pas seulement sur l'interface : sur les
*documents livrés* (C6-39, C8-57, C9-66, C11-85, C12-93, C13-101, C18-137,
C20-151). Un Markdown bien structuré — titres hiérarchisés sans saut de niveau,
tableaux avec en-têtes, liens explicites, pas d'information portée par la seule
couleur — satisfait ces critères ; encore faut-il l'écrire quelque part et s'y
tenir. OWASP top 10 est exigé sur les deux API (C9-61, C17-127).
L'éco-responsabilité est un critère de choix des services (C7-49, C15-110) et
des développements (C17-126).

---

## E1 — Extraction et stockage des données (C1-C5)

### C1 — Automatiser l'extraction de données

| # | Critère | Statut | Constat |
|---|---|---|---|
| 3 | Présentation du projet et du contexte : acteurs, objectifs, environnements, contraintes, budget, organisation, planification | 🟡 | `docs/CADRAGE_MODELE.md` et `PLANNING.md` couvrent acteurs, objectifs, contraintes techniques et planification. **Le budget n'est chiffré nulle part.** |
| 4 | Spécifications techniques : technologies, outils, services externes, langages, accessibilité | 🟡 | Technologies et contraintes matérielles sont précises (`CADRAGE_MODELE.md` §Contraintes). Les services externes (Gladia, Pappers, OCR) sont cités sans spécification. |
| 5 | Périmètre complet des spécifications d'extraction et d'agrégation | ❌ | `docs/SOURCES_DONNEES.md` porte la structure du dump catalogue, pas une spécification d'extraction. |
| 6 | Script d'extraction fonctionnel | ❌ | Aucun script d'extraction dans le dépôt. |
| 7 | Le script comprend point de lancement, dépendances, connexions, règles, gestion d'erreurs, sauvegarde | ❌ | Sans objet tant que le script n'existe pas. |
| 8 | Script versionné et accessible depuis un dépôt Git | ❌ | Voir le constat nº 1 : **pas de remote**. |
| 9 | Mix d'au moins : API REST, fichier, scraping, base de données, big data | ❌ | Le pivot a retiré au référentiel d'entraînement son rôle de collecte. Le scraping des fiches fabricants est maintenu comme exercice à part entière (`LIVRABLES.md` E1) mais **n'est pas écrit**. |

### C2 — Requêtes SQL

| # | Critère | Statut | Constat |
|---|---|---|---|
| 11 | Requêtes SQL fonctionnelles | ❌ | Il n'y a pas de base de données. Le catalogue est un dictionnaire Python (`app/catalogue.py`, 67 lignes). |
| 12 | Documentation des choix : sélections, filtrages, jointures | ❌ | Sans objet. |
| 13 | Documentation des optimisations | ❌ | Sans objet. |

> **Le vrai enjeu de C2.** Le catalogue en dur est légitime pour un prototype,
> mais il ne produit aucune preuve pour C2 *ni* pour C4. Le porter en SQLite ou
> PostgreSQL est le seul geste qui débloque les deux compétences à la fois — et
> il est petit : le module `app/catalogue.py` a déjà la forme d'une table.

### C3 — Agrégation des données

| # | Critère | Statut | Constat |
|---|---|---|---|
| 15 | Script d'agrégation fonctionnel (nettoyage, normalisation) | ❌ | Absent. |
| 16 | Script versionné sur dépôt Git | ❌ | Voir constat nº 1. |
| 17 | Documentation : dépendances, commandes, algorithme, choix de nettoyage | ❌ | Absente. |

### C4 — Base de données et RGPD

| # | Critère | Statut | Constat |
|---|---|---|---|
| 19 | Modélisations respectant Merise | ❌ | Aucun MCD/MPD. `archive/renoassistant/DIAGRAMMES.md` contient des diagrammes Mermaid de flux, pas un modèle Merise, et relève d'une conception **périmée**. |
| 20 | Modèle physique fonctionnel | ❌ | Absent. |
| 21 | Base choisie au regard de la modélisation et des contraintes | ❌ | La persistance actuelle est du JSON à plat (`app/persistance.py`), choix assumé pour le prototype mais non argumenté comme choix de base. |
| 22 | Procédures d'installation reproductibles (base + API) | 🟡 | L'API s'installe et se lance (`README.md`, `CLAUDE.md`). Rien pour une base. |
| 23 | Script d'import fonctionnel | ❌ | Absent. |
| 24 | Documentation du script d'import versionnée à la racine du dépôt | ❌ | Absente. |
| 25 | Documentations couvrant dépendances et commandes d'exécution | 🟡 | Couvert pour l'application, pas pour des scripts de données inexistants. |
| 26 | Registre des traitements de données personnelles | ❌ | **Non écrit alors que le projet en traite** : coordonnées du client final saisies pour les mentions obligatoires BTP, transcriptions vocales, journal des corrections artisan. |
| 27 | Procédures de tri RGPD rédigées | ❌ | Absentes. |
| 28 | Procédures détaillant traitements et fréquence | ❌ | Absentes. |

> **Point sensible.** Le produit **collecte bien des données personnelles**
> (nom, adresse de chantier du client final ; voix de l'artisan). Le registre
> des traitements n'est pas un exercice académique ici, il est dû. C'est aussi
> le document le moins cher à produire de tout le référentiel : trois
> traitements, une page.

### C5 — API de mise à disposition du jeu de données

| # | Critère | Statut | Constat |
|---|---|---|---|
| 30 | Documentation technique couvrant tous les points de terminaison | 🟡 | FastAPI génère `/openapi.json` et `/docs` pour les **sept** endpoints existants. Aucun n'expose un *jeu de données* au sens de C5. |
| 31 | Documentation des règles d'authentification/autorisation | ❌ | **Il n'y a aucune authentification** (`grep -n 'Depends\|auth' app/*.py` : rien). |
| 32 | Documentation respectant un standard (OpenAPI) | ✅ | OpenAPI 3.1 servi automatiquement par FastAPI. Seul ✅ franc de E1. |
| 33 | API restreignant l'accès aux données par autorisation | ❌ | Aucune restriction. Le cookie `projet_id` isole les sessions, ce **n'est pas** de l'authentification. |
| 34 | API fonctionnelle pour la mise à disposition du jeu de données | ➖ | **Écarté et assumé** : le projet n'a pas de jeu de données à exposer. La chose honnête est de dire que C5 sera porté par l'API du modèle (C9), pas d'inventer un endpoint de données factice. |

---

## E2 — Veille et services d'IA préexistants (C6-C8)

### C6 — Veille technique et réglementaire

| # | Critère | Statut | Constat |
|---|---|---|---|
| 36 | Thématique portant sur un outil et/ou une réglementation de la mise en situation | ✅ | « Unsloth et fine-tuning MoE » — c'est l'outil du projet (`veille/DISPOSITIF.md`). Le recadrage était nécessaire : l'ancienne thématique « IA et marché de l'emploi » ne satisfaisait pas ce critère. |
| 37 | Temps de veille planifiés, au moins une heure hebdomadaire | ✅ | Rituel du vendredi, une heure, décrit dans `veille/DISPOSITIF.md`. |
| 38 | Outils d'agrégation cohérents avec les sources et le budget | ✅ | Cinq flux dans `veille/sources.opml`, agrégation RSS, coût nul. |
| 39 | Synthèses communiquées dans un format accessible | 🟡 | `veille/GABARIT-SEANCE.md` structure les comptes rendus. Aucune synthèse n'a encore été communiquée. |
| 40 | Informations partagées répondant à la thématique | ❌ | **`veille/seances/` est vide** (un seul `.gitkeep`). C'est le manque le plus visible de E2 : le dispositif est décrit, il n'a jamais tourné. |
| 41 | Sources répondant aux critères de fiabilité (auteur identifié, notoriété, absence d'intérêt personnel) | 🟡 | Les cinq flux sont choisis, leur fiabilité n'est **pas argumentée par écrit** source par source, ce que le critère demande. |
| 42 | Analyse du contenu valable (date récente, sources citées, document structuré) | ❌ | Sans séance, pas d'analyse. |
| 43 | Sources respectant les normes d'accessibilité privilégiées, information confirmée ailleurs | ❌ | Non traité dans le choix des sources. |

> **La correction la moins chère du référentiel.** Quatre séances d'une heure
> rédigées au gabarit ferment 40, 42 et 43, et solidifient 39 et 41. Le
> dispositif est prêt ; il ne manque que les traces.

### C7 — Benchmark de services d'IA préexistants

| # | Critère | Statut | Constat |
|---|---|---|---|
| 45 | Expression de besoin reformulée, objectifs et contraintes | 🟡 | `docs/CADRAGE_MODELE.md` porte objectifs et contraintes, mais pas sous la forme d'une expression de besoin d'intégration d'un service tiers. |
| 46 | Benchmark listant services étudiés **et non étudiés** | ❌ | Aucun benchmark. |
| 47 | Raisons d'écarter un service explicitées | 🟡 | Des choix sont argumentés en dispersé (gpt-oss retenu pour Apache 2.0 et MoE ; OCR délégué à une API externe ; Gladia contre Whisper local non tranché) mais **jamais rassemblés en benchmark**. |
| 48 | Niveau d'adéquation par ensemble fonctionnel | ❌ | Absent. |
| 49 | Niveau de démarche éco-responsable de chaque service | ❌ | Absent. Angle porteur ici : le 100 % local évite le trafic d'inférence mais consomme une DGX Spark — c'est un arbitrage réel à documenter, pas un argument facile. |
| 50 | Contraintes techniques et pré-requis par solution | 🟡 | Les contraintes de la cible matérielle sont posées avec précision (128 Go unifiés, 273 Go/s, MoE + FP4) — pour **un** service, pas pour un panel. |
| 51 | Conclusions délimitant services retenus et écartés | ❌ | Absentes. |

> Le benchmark naturel du projet est **STT** — Gladia, Whisper local, Web Speech
> API, Azure Speech, Deepgram — parce que c'est le seul endroit où le projet
> hésite encore vraiment, où l'éco-responsabilité et la contrainte « 100 % local »
> s'opposent franchement, et où la conclusion changera le code.

### C8 — Paramétrage d'un service d'IA

| # | Critère | Statut | Constat |
|---|---|---|---|
| 53 | Service installé et accessible, avec authentification éventuelle | ✅ | Ollama répond sur `localhost:11434` et sert `gpt-oss:20b`. Vérifié. |
| 54 | Service configuré correctement, répondant aux besoins et contraintes | ✅ | `app/llm.py` : température 0,2, `stream: false`, timeout 60 s, prompt système imposant l'enveloppe JSON unique. |
| 55 | Monitorage disponible du service opérationnel | ❌ | Aucun monitorage. Aucun `logging` dans `app/`. |
| 56 | Documentation : accès, installation, test, dépendances, données impliquées | 🟡 | `CLAUDE.md` et `README.md` donnent les commandes ; la procédure d'installation d'Ollama et le choix du modèle ne sont pas documentés. |
| 57 | Documentation communiquée dans un format accessible | 🟡 | Markdown structuré, mais aucune règle d'accessibilité documentaire n'est écrite ni tenue explicitement. |

---

## E3 — Modèle d'intelligence artificielle (C9-C13)

### C9 — API exposant le modèle

| # | Critère | Statut | Constat |
|---|---|---|---|
| 59 | L'API restreint l'accès au modèle par authentification | ❌ | Aucune. **Critère structurant, et le seul qui bloque C9 sur le fond.** |
| 60 | L'API donne accès aux fonctions du modèle selon les spécifications | ✅ | Sept endpoints, dont `/api/message` qui porte le cycle complet. |
| 61 | Recommandations OWASP top 10 intégrées quand nécessaire | 🟡 | Deux protections réelles : validation Pydantic stricte sur toutes les entrées, et validation du chemin de projet contre la traversée de répertoire (`MOTIF_ID`, testé sur `"../../etc/passwd"`). Manquent : authentification (A01, A07), limitation de débit, en-têtes de sécurité, et la **neutralisation des injections de prompt** (US-20). |
| 62 | Sources versionnées sur dépôt Git **distant** | ❌ | Voir constat nº 1. |
| 63 | Tests couvrant tous les points de terminaison | ✅ | `tests/test_api.py` couvre les sept endpoints. |
| 64 | Tests s'exécutant sans bug, résultats interprétés | ✅ | `62 passed`. Vérifié au commit `d783b9a`. |
| 65 | Documentation : architecture, endpoints, règles d'authentification | 🟡 | Architecture décrite dans `CONTEXTE_COMPLET_PROJET.md` ; endpoints décrits par OpenAPI ; **règles d'authentification inexistantes**. |
| 66 | Documentation et API respectant un standard, format accessible | 🟡 | OpenAPI oui ; l'accessibilité du format documentaire n'est pas traitée. |

### C10 — Intégration de l'API dans une application

| # | Critère | Statut | Constat |
|---|---|---|---|
| 68 | Application de départ installée et fonctionnelle en développement | ✅ | `uvicorn app.main:app --reload` sert l'interface et l'API. Vérifié. |
| 69 | Communication avec l'API fonctionnelle | ✅ | Le front mono-fichier `app/static/index.html` appelle les sept endpoints. |
| 70 | Authentification et renouvellement des jetons intégrés | ❌ | Rien à intégrer tant que l'API n'authentifie pas. |
| 71 | Tous les endpoints du projet intégrés selon les spécifications | ✅ | Les sept sont appelés depuis le front. |
| 72 | Adaptations d'interface intégrées | 🟡 | Interface fonctionnelle et conforme RGAA, mais **il n'existe aucune maquette** dont on puisse dire qu'elle est respectée (voir C14-104 et C17-121). |
| 73 | Tests d'intégration couvrant tous les endpoints exploités | ✅ | `tests/test_api.py` via `TestClient`. |
| 74 | Tests s'exécutant en totalité, résultats interprétés | ✅ | `62 passed`. |
| 75 | Sources versionnées sur le dépôt Git de l'application | 🟡 | Versionnées localement depuis `e669883`. **Pas de remote.** |

### C11 — Monitorage du modèle

| # | Critère | Statut | Constat |
|---|---|---|---|
| 77 | Métriques expliquées sans erreur d'interprétation | ✅ | Huit métriques définies avec seuils dans `docs/DISPOSITIF_AGENT.md` §4, dont deux au rang sécurité (justesse de la mention ≥ 95 %, prix ou référence inventés = 0). Le raisonnement derrière chaque seuil est écrit. |
| 78 | Outils de monitorage adaptés au contexte | ❌ | Aucun outil choisi. |
| 79 | Au moins un vecteur de restitution temps réel | ❌ | Absent. |
| 80 | Enjeux d'accessibilité pris en compte dans le choix de l'outil | ❌ | Sans objet tant qu'aucun outil n'est choisi. |
| 81 | Chaîne testée en bac à sable | ❌ | Absent. |
| 82 | Chaîne en état de marche | ❌ | Absent. |
| 83 | Sources versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |
| 84 | Documentation d'installation, configuration, utilisation | ❌ | Absente. |
| 85 | Documentation au format accessible | ❌ | Absente. |

> **C11 est la compétence la plus déséquilibrée du dossier** : la partie
> difficile — décider *quoi* mesurer et *à quel seuil* — est faite et bien
> faite ; la partie mécanique — collecter, restituer, alerter — est entièrement
> à faire. Huit critères sur neuf tiennent à l'outillage.

### C12 — Tests automatisés du modèle

| # | Critère | Statut | Constat |
|---|---|---|---|
| 87 | Cas à tester listés : partie visée, périmètre, stratégie | 🟡 | La stratégie d'évaluation du modèle est posée (`DISPOSITIF_AGENT.md` §4 : jeu de test de 150-200 exemples écrits à la main, protocole 20b brut contre 20b fine-tuné). Les cas ne sont pas listés un par un. |
| 88 | Outils de test cohérents avec l'environnement | ✅ | pytest, cohérent avec la stack Python/uv. |
| 89 | Tests intégrés respectant la couverture établie | 🟡 | 62 tests couvrent le **code déterministe** : référentiel, devis, pipeline, persistance, API. Aucun test ne porte sur le **modèle** lui-même — or c'est l'objet de C12. |
| 90 | Tests s'exécutant sans problème technique | ✅ | `62 passed` en ~4 s. |
| 91 | Sources versionnées sur dépôt Git distant (DVC, GitLab…) | ❌ | Voir constat nº 1. Aucun versionnement de données non plus. |
| 92 | Documentation : installation, dépendances, exécution, couverture | 🟡 | Installation et exécution documentées dans `CLAUDE.md`. **Aucune mesure de couverture** n'est produite. |
| 93 | Documentation au format accessible | 🟡 | Markdown structuré, sans règle écrite. |

### C13 — Chaîne de livraison continue du modèle (MLOps)

| # | Critère | Statut | Constat |
|---|---|---|---|
| 95 | Documentation couvrant étapes, tâches, déclencheurs | ❌ | Absente. |
| 96 | Déclencheurs intégrés comme définis | ❌ | Absent. |
| 97 | Fichiers de configuration reconnus et exécutés | ❌ | Absent. |
| 98 | Étape de test des données intégrée et sans erreur | ❌ | Absente. |
| 99 | Étapes de test, entraînement et validation du modèle intégrées | ❌ | Absentes. |
| 100 | Sources de la chaîne versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |
| 101 | Documentation d'installation, configuration, test, au format accessible | ❌ | Absente. |

> C13 est **intégralement à faire**. C'est cohérent avec le calendrier : le
> fine-tuning n'a pas encore eu lieu. Mais c'est sept critères, et la chaîne
> doit exister avant l'entraînement pour pouvoir en porter la trace.

---

## E4 — Application (C14-C19)

### C14 — Analyse du besoin et spécifications fonctionnelles

| # | Critère | Statut | Constat |
|---|---|---|---|
| 103 | Modélisation des données respectant un formalisme (Merise, entités-relations) | ❌ | Absente. Même manque que C4-19 ; un seul modèle sert les deux critères. |
| 104 | Modélisation des parcours utilisateurs (schéma fonctionnel, wireframes) | ❌ | Aucune maquette, aucun wireframe. L'interface a été écrite directement en HTML. |
| 105 | Chaque spécification couvre contexte, scénarios, critères de validation | ✅ | `docs/STORIES.md` : 26 stories, chacune avec son contexte, ses critères d'acceptation et **un cas dégradé**. |
| 106 | Objectifs d'accessibilité intégrés aux critères d'acceptation des user stories | ✅ | 21 stories portent une rubrique « Accessibilité » **au même rang** que le fonctionnel — c'est exactement ce que le critère demande, et c'est rare. |
| 107 | Objectifs d'accessibilité appuyés sur un standard (WCAG, RGAA) | ✅ | RGAA 4.1 nommé 23 fois dans `docs/STORIES.md`, avec les numéros de critère. |

### C15 — Cadre technique

| # | Critère | Statut | Constat |
|---|---|---|---|
| 109 | Spécifications techniques : architecture, dépendances, environnement d'exécution | ✅ | `CADRAGE_MODELE.md` (frontière modèle/code, schéma de sortie), `pyproject.toml` (dépendances épinglées, Python ≥ 3.14), contraintes matérielles argumentées. |
| 110 | Services et prestataires éco-responsables favorisés | ❌ | Aucun critère éco-responsable dans les choix faits. |
| 111 | Flux de données représentés par un diagramme de flux | 🟡 | `CONTEXTE_COMPLET_PROJET.md` porte un schéma ASCII du flux. Ce n'est pas un **diagramme de flux de données** au sens formel (DFD niveau 0/1). |
| 112 | Preuve de concept accessible et fonctionnelle en pré-production | 🟡 | La preuve de concept **fonctionne en local**. Il n'y a pas d'environnement de pré-production. |
| 113 | Conclusion de la preuve de concept permettant une décision | ❌ | Non rédigée. |

### C16 — Conduite agile

| # | Critère | Statut | Constat |
|---|---|---|---|
| 115 | Cycles, étapes, rôles, rituels et outils de la méthode respectés | 🟡 | Le découpage agile est réel — 26 stories, 7 épiques, deux files de priorité, sprints dans `PLANNING.md`. Les **rituels ne sont pas tenus ni tracés** (pas de revue de sprint, pas de rétrospective écrite). |
| 116 | Outils de pilotage disponibles (kanban, burndown, backlog) | 🟡 | Le backlog existe et fait autorité. Le kit de transposition Notion est prêt (`docs/NOTION_BOARD.md`, CSV, CLI) mais **le tableau n'est pas encore monté**. |
| 117 | Objectifs et modalités des rituels partagés aux parties prenantes | ❌ | Non écrits. |
| 118 | Éléments de pilotage accessibles à toutes les parties tout au long du projet | 🟡 | Accessibles dans le dépôt ; pas de vue partagée hors dépôt tant que Notion n'est pas monté. |

> C16 se joue sur des **traces**, pas sur du code : un tableau Notion vivant,
> des revues de sprint datées, une rétrospective. Le projet est conduit de façon
> agile ; il ne le **prouve** pas encore.

### C17 — Développement des composants et interfaces

| # | Critère | Statut | Constat |
|---|---|---|---|
| 120 | Environnement de développement conforme aux spécifications | ✅ | uv, venv hors dépôt, Python ≥ 3.14, dépendances épinglées. |
| 121 | Interfaces intégrées respectant les maquettes | ❌ | Il n'y a pas de maquette (C14-104). Le critère ne peut pas être satisfait tant qu'elle n'existe pas — même si l'interface, elle, existe. |
| 122 | Comportements des composants et navigation conformes aux spécifications | ✅ | Validation, modale accessible, arbitrage des quantités, correction de ligne — conformes aux stories. |
| 123 | Composants métier développés et fonctionnels | ✅ | Moteur de devis déterministe : référentiel, taux de chute, rendements, TVA, ventilation, acompte. 12 tests dédiés. |
| 124 | Gestion des droits d'accès développée | ❌ | Aucune. Le cookie de projet isole, il n'autorise pas. |
| 125 | Flux de données intégrés conformément aux spécifications | ✅ | La frontière est tenue : le modèle décrit, le code calcule. Le schéma de sortie ne comporte **ni prix ni référence produit** — le modèle ne peut pas halluciner ce qu'il n'a pas la possibilité d'exprimer. |
| 126 | Bonnes pratiques d'éco-conception (éco-index, Green IT) | 🟡 | Le front est **un seul fichier, sans framework, sans dépendance externe, sans image** — c'est de l'éco-conception de fait, mais elle n'est ni revendiquée ni mesurée. |
| 127 | Préconisations OWASP top 10 implémentées quand nécessaire | 🟡 | Mêmes protections et mêmes manques qu'en C9-61. |
| 128 | Tests unitaires ou d'intégration couvrant composants métier et gestion des accès | 🟡 | Composants métier : largement couverts. **Gestion des accès : rien à couvrir.** |
| 129 | Sources versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |
| 130 | Documentation : installation, architecture, dépendances, tests, normes d'accessibilité | 🟡 | Tout y est sauf le respect explicite des normes d'accessibilité documentaire. |

### C18 — Intégration continue

| # | Critère | Statut | Constat |
|---|---|---|---|
| 132 | Documentation couvrant outils, étapes, tâches, déclencheurs | ❌ | Absente. |
| 133 | Outil d'intégration continue sélectionné de façon cohérente | ❌ | Aucun. Pas de `.github/`. |
| 134 | Chaîne intégrant les étapes préalables aux tests (build, configuration) | ❌ | Absente. |
| 135 | Chaîne exécutant les tests au déclenchement | ❌ | Absente. |
| 136 | Configurations versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |
| 137 | Documentation au format accessible | ❌ | Absente. |

> **Le meilleur rapport effort/points du dossier.** 62 tests verts existent
> déjà. Un fichier `.github/workflows/tests.yml` de vingt lignes, plus un
> remote, ferment **six critères** d'un coup — et rendent crédibles C12-89
> et C19.

### C19 — Livraison continue

| # | Critère | Statut | Constat |
|---|---|---|---|
| 139 | Documentation couvrant étapes, tâches, déclencheurs | ❌ | Absente. |
| 140 | Fichiers de configuration reconnus et exécutés | ❌ | Absents. |
| 141 | Étape de packaging intégrée et sans erreur | ❌ | Aucun packaging (pas de Dockerfile, pas de build). |
| 142 | Étape de livraison intégrée après validation du packaging | ❌ | Absente. |
| 143 | Sources versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |

---

## E5 — Exploitation (C20-C21)

### C20 — Surveillance et journalisation

| # | Critère | Statut | Constat |
|---|---|---|---|
| 145 | Documentation listant métriques, seuils et valeurs d'alerte | 🟡 | Les huit métriques et leurs seuils sont écrits (`DISPOSITIF_AGENT.md` §4). Les **valeurs d'alerte** — à partir de quand on réveille quelqu'un — ne le sont pas. |
| 146 | Arguments en faveur des choix techniques d'outillage | ❌ | Aucun outil choisi, donc aucun argument. |
| 147 | Outils installés et opérationnels au moins en local | ❌ | Aucun. |
| 148 | Règles de journalisation intégrées aux sources | 🟡 | **Les objets métier existent déjà** : `Escalade(horodatage, motif, detail)` journalise chaque échec du modèle avec son motif, et les corrections de l'artisan sont conservées comme signal qualité. Mais rien n'est écrit dans un journal applicatif — aucun `logging` dans `app/`. La matière est là, le tuyau manque. |
| 149 | Alertes configurées et en état de marche | ❌ | Absentes. |
| 150 | Documentation d'installation et de configuration | ❌ | Absente. |
| 151 | Documentation au format accessible | ❌ | Absente. |

### C21 — Résolution d'incidents

| # | Critère | Statut | Constat |
|---|---|---|---|
| 153 | Causes des problèmes identifiées correctement | ❌ | Aucun incident tracé formellement, alors que **six anomalies réelles ont été diagnostiquées et corrigées** cette nuit (intent `quantitatif` non routé, reprises qui se composaient jusqu'à 4 appels modèle, `Session` de module partagée entre visiteurs, `index.html` en chemin relatif, Ollama arrêté renvoyant un 500, mentions rendues `undefined` côté front). Elles sont dans les messages de commit, pas dans un suivi d'incidents. |
| 154 | Problème reproduit en environnement de développement | ❌ | Non tracé comme tel — plusieurs de ces anomalies ont pourtant un **test de non-régression** dédié. |
| 155 | Procédure de débogage documentée depuis l'outil de suivi | ❌ | Pas d'outil de suivi. |
| 156 | Solution documentée expliquant chaque étape | ❌ | Non rédigée sous cette forme. |
| 157 | Solution versionnée dans le dépôt (merge request par exemple) | 🟡 | Versionnée par commits atomiques et messages explicatifs. **Sans remote, pas de merge request.** |

> **C21 est presque gratuit et pourtant à zéro.** Le travail d'investigation a
> été fait ; il manque le *format*. Une fiche d'incident par anomalie —
> symptôme, cause, reproduction, correctif, test de non-régression, commit —
> ferme cinq critères avec des faits déjà établis. Six anomalies sont
> disponibles immédiatement.

---

## Ce qu'il faut faire, dans l'ordre du rendement

1. **Créer le dépôt distant et pousser.** Neuf critères, une commande. *(Décision de l'utilisateur : je n'ai pas le droit de pousser.)*
2. **Chaîne d'intégration continue** (`.github/workflows/`). Six critères, les tests existent déjà. → C18 entier, appui pour C12 et C19.
3. **Fiches d'incident** pour les six anomalies déjà corrigées. Cinq critères, matière déjà établie. → C21.
4. **Quatre séances de veille** au gabarit. Trois critères fermés, deux consolidés. → C6.
5. **Registre des traitements de données personnelles** + procédures de tri. Trois critères, une page, et c'est légalement dû. → C4.
6. **Journalisation applicative** branchée sur les escalades et corrections existantes. → C20-148, appui C11.
7. **Modèle Merise** du référentiel métier et du catalogue. Deux critères d'un coup (C4-19 et C14-103), et il débloque le portage du catalogue en base — donc C2.
8. **Authentification de l'API.** Quatre critères (C5-33, C9-59, C17-124, C10-70) et c'est un manque de fond, pas de forme.
9. **Wireframes** de l'interface existante. Deux critères (C14-104, C17-121).
10. **Benchmark STT** avec colonne éco-responsable. Sept critères de C7 et deux ailleurs (C15-110, C17-126).

---

*Audit établi le 08/09/2026 sur le dépôt à l'état du commit `a019878`.
Les statuts sont datés : ils décrivent ce qui est dans le dépôt ce jour-là,
pas ce qui est prévu.*
