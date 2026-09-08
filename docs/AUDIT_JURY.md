# Audit critère par critère du référentiel RNCP

> **À quoi sert ce document.** `docs/LIVRABLES.md` regarde la couverture au
> niveau de la *compétence*. Ici on descend d'un cran : les **135 critères
> d'évaluation** que le jury coche un par un, extraits de
> `reference/referentiel-rncp-ai-engineer.xlsx`, confrontés à l'**état constaté
> du dépôt** au commit `d29b444` (08/09/2026).
>
> Même règle que la grille de contrôle : **on ne dénature pas le projet pour
> cocher une case.** Un critère hors périmètre est écrit comme tel, avec la
> raison — c'est plus défendable devant un jury qu'une case cochée de travers.
>
> **Ce document périme.** La première version datait du commit `a019878` ;
> vingt commits ont atterri derrière sans qu'elle bouge, et une dizaine de
> lignes affirmaient encore l'absence de choses déjà écrites — chaîne
> d'intégration, authentification, journalisation, incidents. Un audit faux
> est pire qu'un audit manquant : il rassure. La ligne de commit ci-dessus dit
> jusqu'où il a été vérifié ; si `git log` en montre d'autres derrière,
> **relire avant de s'y fier**.

**Convention.** ✅ couvert, preuve dans le dépôt · 🟡 partiel, il manque quelque
chose de nommé · ❌ absent · ➖ écarté, avec motif assumé.

## Le compte

| Livrable | Critères | ✅ | 🟡 | ❌ | ➖ |
|---|---|---|---|---|---|
| E1 — Données (C1-C5) | 28 | 7 | 6 | 14 | 1 |
| E2 — Veille et IA préexistante (C6-C8) | 20 | 15 | 4 | 1 | 0 |
| E3 — Modèle IA (C9-C13) | 39 | 23 | 6 | 10 | 0 |
| E4 — Application (C14-C19) | 36 | 19 | 8 | 9 | 0 |
| E5 — Exploitation (C20-C21) | 12 | 7 | 5 | 0 | 0 |
| **Total** | **135** | **71** | **29** | **34** | **1** |

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

**2. Des trois exigences transverses, deux sont traitées, une ne l'est pas.**
L'accessibilité est citée dans **huit** compétences, et pas seulement sur
l'interface : sur les *documents livrés* (C6-39, C8-57, C9-66, C11-85, C12-93,
C13-101, C18-137, C20-151). Elle est désormais une **règle écrite**
(`docs/ACCESSIBILITE_DOCUMENTS.md`, neuf règles) dont trois sont **vérifiées
mécaniquement** à chaque exécution de la chaîne — un critère transverse tenu
par une machine ne se perd pas en route. Seul C13-101 reste ❌, parce que la
chaîne MLOps qu'il vise n'existe pas encore. OWASP top 10, exigé sur les deux
API (C9-61, C17-127), est couvert par six mesures nommées dans
`app/authentification.py` plus les garde-fous d'entrée.

**L'éco-responsabilité** (C7-49, C15-110, C17-126) est passée de l'intention à
l'argument : `docs/BENCHMARK_STT.md` chiffre l'écart entre transcription locale
et API distante et refuse l'argument facile — le local est sobre parce que la
machine tourne déjà pour le LLM, pas par nature. Elle reste **non mesurée** :
aucun wattmètre n'a encore tourné, et c'est ce qui maintient C15-110 et C17-126
à mi-chemin.

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
| 19 | Modélisations respectant Merise | ✅ | `docs/MODELE_DONNEES.md` — modèle conceptuel Merise (neuf entités, cardinalités justifiées), dictionnaire des données champ par champ avec le module qui le définit, modèle logique en tables. Le niveau conceptuel et le dictionnaire **décrivent le code**, pas une intention ; le niveau logique est marqué comme cible. |
| 20 | Modèle physique fonctionnel | 🟡 | Le modèle physique n'est pas écrit, et le document dit pourquoi : il n'a pas lieu d'être avant que la migration en base soit décidée. Les quatre déclencheurs de cette décision sont nommés. |
| 21 | Base choisie au regard de la modélisation et des contraintes | ❌ | La persistance actuelle est du JSON à plat (`app/persistance.py`), choix assumé pour le prototype mais non argumenté comme choix de base. |
| 22 | Procédures d'installation reproductibles (base + API) | 🟡 | L'API s'installe et se lance (`README.md`, `CLAUDE.md`). Rien pour une base. |
| 23 | Script d'import fonctionnel | ❌ | Absent. |
| 24 | Documentation du script d'import versionnée à la racine du dépôt | ❌ | Absente. |
| 25 | Documentations couvrant dépendances et commandes d'exécution | 🟡 | Couvert pour l'application, pas pour des scripts de données inexistants. |
| 26 | Registre des traitements de données personnelles | ✅ | `docs/RGPD.md` — quatre traitements (devis, dictée, signal qualité, journalisation), chacun avec finalité, base légale, personnes concernées, destinataires, conservation et mesures de sécurité. Écrit **depuis le code**, chaque donnée citée avec son module. |
| 27 | Procédures de tri RGPD rédigées | ✅ | `docs/RGPD.md` — tri à la collecte (ce qui n'entre pas), tri avant réutilisation (ce qui ne part pas à l'entraînement), tri à la sortie. Chaque règle porte son état : tenue par le code, ou à faire. |
| 28 | Procédures détaillant traitements et fréquence | ✅ | `docs/RGPD.md` — tableau des opérations, chacune avec son déclencheur, sa fréquence et sa trace. Les deux purges absentes y figurent comme absentes, pas comme prévues. |

> **Traité le 08/09/2026 — et l'exercice a trouvé un vrai défaut.** Le produit
> collecte bien des données personnelles (nom, adresse de chantier du client
> final ; voix de l'artisan). En remontant la trace de la voix, le registre a
> mis au jour que la dictée du prototype **sortait de la machine** : la *Web
> Speech API* du navigateur envoie l'audio à un service distant, contre
> l'engagement « 100 % local » du cadrage. Corrigé le jour même
> (`app/static/index.html`, `tests/test_front.py`). C'est l'argument à tenir
> devant le jury : le registre n'a pas été rédigé pour cocher trois cases, il a
> servi à quelque chose.
>
> `docs/RGPD.md` nomme aussi ce qui reste en défaut — aucune durée de
> conservation implémentée, aucun tri avant entraînement, client final non
> informé — plutôt que de décrire des mesures inexistantes.

### C5 — API de mise à disposition du jeu de données

| # | Critère | Statut | Constat |
|---|---|---|---|
| 30 | Documentation technique couvrant tous les points de terminaison | 🟡 | FastAPI génère `/openapi.json` et `/docs` pour les **seize** points de terminaison existants, chacun avec `summary`, `tags` et modèle de sortie déclaré (`app/api_schema.py`). Aucun n'expose un *jeu de données* au sens de C5. |
| 31 | Documentation des règles d'authentification/autorisation | ✅ | Les règles sont écrites au plus près du code qui les applique : docstring de `app/authentification.py` (un seul compte, empreinte scrypt en variable d'environnement, jeton HMAC de 12 h, 5 tentatives par fenêtre de 5 minutes, cookie `httponly`/`samesite=strict`), et tableau des variables d'environnement dans `README.md`. |
| 32 | Documentation respectant un standard (OpenAPI) | ✅ | OpenAPI 3.1 servi automatiquement par FastAPI. Seul ✅ franc de E1. |
| 33 | API restreignant l'accès aux données par autorisation | ✅ | Depuis `0442fbe` : un appel sans jeton reçoit 401 **avant toute recherche de ressource**, `/openapi.json` compris. `tests/test_auth.py` (19 tests) et les deux premières étapes du parcours de bout en bout le vérifient. |
| 34 | API fonctionnelle pour la mise à disposition du jeu de données | ➖ | **Écarté et assumé** : le projet n'a pas de jeu de données à exposer. La chose honnête est de dire que C5 sera porté par l'API du modèle (C9), pas d'inventer un endpoint de données factice. |

---

## E2 — Veille et services d'IA préexistants (C6-C8)

### C6 — Veille technique et réglementaire

| # | Critère | Statut | Constat |
|---|---|---|---|
| 36 | Thématique portant sur un outil et/ou une réglementation de la mise en situation | ✅ | « Unsloth et fine-tuning MoE » — c'est l'outil du projet (`veille/DISPOSITIF.md`). Le recadrage était nécessaire : l'ancienne thématique « IA et marché de l'emploi » ne satisfaisait pas ce critère. |
| 37 | Temps de veille planifiés, au moins une heure hebdomadaire | ✅ | Rituel du vendredi, une heure, décrit dans `veille/DISPOSITIF.md`. |
| 38 | Outils d'agrégation cohérents avec les sources et le budget | ✅ | **Six** flux dans `veille/sources.opml`, agrégation RSS, coût nul. Le sixième (PyPI) a été ajouté par la séance du 08/09, qui a constaté que le flux GitHub ne portait plus le changelog de la bibliothèque. |
| 39 | Synthèses communiquées dans un format accessible | ✅ | `veille/seances/2026-09-08.md`, au gabarit, en Markdown, contrôlé par `tools/verifier_accessibilite_docs.py` au même titre que les documents de conception. |
| 40 | Informations partagées répondant à la thématique | 🟡 | Une séance tenue (08/09/2026) : 52 items balayés, 5 retenus, tous sur Unsloth et le fine-tuning. Elle a produit des effets réels — OPML corrigé, deux notes dans `docs/NOTES.md`, un ajout à `PLANNING.md`. **Une seule séance ne fait pas un rituel** : le critère se ferme par la récurrence hebdomadaire. |
| 41 | Sources répondant aux critères de fiabilité (auteur identifié, notoriété, absence d'intérêt personnel) | 🟡 | Les six flux sont choisis, leur fiabilité n'est **pas argumentée par écrit** source par source, ce que le critère demande. |
| 42 | Analyse du contenu valable (date récente, sources citées, document structuré) | ✅ | Séance du 08/09 : items datés d'août-septembre 2026, sources citées une à une, structure imposée par le gabarit, un verdict unique par item et une suite donnée à chacun. |
| 43 | Sources respectant les normes d'accessibilité privilégiées, information confirmée ailleurs | ❌ | Non traité dans le choix des sources. |

> **Une séance tenue, pas quatre — délibérément.** Antidater trois séances de
> plus fabriquerait la preuve au lieu de la produire, et la séance du 08/09 le
> dit elle-même en tête : c'est un rattrapage assisté, sur cinq semaines de
> balayage. 42 est fermé, 39 consolidé, 40 attend la **récurrence**, qui ne
> s'écrit pas — elle se tient. 43 (accessibilité des sources) reste entier.

### C7 — Benchmark de services d'IA préexistants

| # | Critère | Statut | Constat |
|---|---|---|---|
| 45 | Expression de besoin reformulée, objectifs et contraintes | ✅ | `docs/BENCHMARK_STT.md` §1 : le besoin est reformulé pour l'usage réel (dictée sur chantier bruyant, noms propres de clients, relecture HITL-0), assorti d'un tableau besoin → contrainte imposée au service, et d'une liste explicite de **ce qui n'est pas un besoin** (diarisation, traduction, temps réel sub-seconde) — c'est elle qui écarte des services excellents mais hors sujet. |
| 46 | Benchmark listant services étudiés **et non étudiés** | ✅ | `docs/BENCHMARK_STT.md` §2 : six solutions étudiées (Web Speech API, faster-whisper large-v3-turbo, Parakeet TDT 0.6b v3, Gladia, Deepgram, Azure AI Speech) **et** un second tableau des solutions écartées sans étude avec leur motif (AssemblyAI, Speechmatics, Google, AWS, API OpenAI, Vosk, dictée système, outils de réunion). |
| 47 | Raisons d'écarter un service explicitées | ✅ | `docs/BENCHMARK_STT.md` §7 : chaque écart tient sur un fait nommé — Deepgram sur l'usage par défaut de l'audio client pour l'entraînement, Azure sur le poids d'exploitation et la contrainte de régions européennes, Web Speech API sur la sortie de l'audio hors machine (INC-10). |
| 48 | Niveau d'adéquation par ensemble fonctionnel | 🟡 | `docs/BENCHMARK_STT.md` §5 : grille de neuf ensembles fonctionnels × six solutions, en mots et non en couleur. Mais cinq lignes sur neuf sont « partiel » partout — jargon métier, noms propres, bruit — et le document le dit : la documentation des fournisseurs ne permet pas de les départager. Le protocole de mesure (§8) est écrit, **pas encore tenu**. |
| 49 | Niveau de démarche éco-responsable de chaque service | ✅ | `docs/BENCHMARK_STT.md` §6 : ce que chaque fournisseur publie et ce qu'il tait, puis un ordre de grandeur calculé aux valeurs constructeur de la DGX Spark (≈ 2,3 Wh par heure d'audio transcrite en local, contre ≈ 528 Wh pour 24 h de veille). La conclusion refuse l'argument facile : le local est sobre **parce que la machine tourne déjà pour le LLM**, pas parce qu'il est local — si elle ne tournait que pour transcrire, l'API mutualisée gagnerait. |
| 50 | Contraintes techniques et pré-requis par solution | ✅ | `docs/BENCHMARK_STT.md` §4 : une fiche par solution — prérequis, empreinte mémoire, limites connues (la version *turbo* dégrade la traduction et boucle sur les silences sans VAD ; Parakeet gagne en glouton plutôt qu'en faisceau ; Azure impose des régions), coût public et pérennité du fournisseur. |
| 51 | Conclusions délimitant services retenus et écartés | ✅ | `docs/BENCHMARK_STT.md` §7 : trois écartés sur faits, deux finalistes locaux, Gladia en repli documenté. L'arbitrage restant est **nommé et rendu à son propriétaire** — « le 100 % local couvre-t-il tout le traitement ou seulement le LLM ? » — avec, pour chaque branche, ce qu'elle change dans le code et dans quels documents. |

> **Le benchmark a été fait là où le projet hésite vraiment.** Pas sur le choix
> du LLM, tranché depuis le cadrage, mais sur le STT : c'est le seul endroit où
> l'éco-responsabilité et la contrainte « 100 % local » s'opposent franchement,
> et où la conclusion changera le code. Le document s'arrête volontairement
> avant l'arbitrage de principe, qui n'appartient pas à un benchmark.

### C8 — Paramétrage d'un service d'IA

| # | Critère | Statut | Constat |
|---|---|---|---|
| 53 | Service installé et accessible, avec authentification éventuelle | ✅ | Ollama répond sur `localhost:11434` et sert `gpt-oss:20b`. Vérifié. |
| 54 | Service configuré correctement, répondant aux besoins et contraintes | ✅ | `app/llm.py` : température 0,2, `stream: false`, timeout 60 s, prompt système imposant l'enveloppe JSON unique. |
| 55 | Monitorage disponible du service opérationnel | ✅ | `app/observabilite.py` écrit un événement JSON par appel au modèle (validité, motif d'échec, tentative, latence) et `/metriques` restitue le tout, **consultable modèle arrêté**. C'est du monitorage du service opérationnel, produit par le projet plutôt qu'acheté. |
| 56 | Documentation : accès, installation, test, dépendances, données impliquées | 🟡 | `CLAUDE.md` et `README.md` donnent les commandes ; la procédure d'installation d'Ollama et le choix du modèle ne sont pas documentés. |
| 57 | Documentation communiquée dans un format accessible | ✅ | `docs/ACCESSIBILITE_DOCUMENTS.md` pose neuf règles, dont trois sont vérifiées mécaniquement par `tools/verifier_accessibilite_docs.py` sur les 19 documents du dépôt, étape de la chaîne d'intégration continue. |

---

## E3 — Modèle d'intelligence artificielle (C9-C13)

### C9 — API exposant le modèle

| # | Critère | Statut | Constat |
|---|---|---|---|
| 59 | L'API restreint l'accès au modèle par authentification | ✅ | `app/authentification.py` — phrase de passe unique dérivée par scrypt, jeton HMAC-SHA256 à durée bornée inscrite dans le jeton. **Aucun chemin non authentifié n'existe dans le code** : sans empreinte dans l'environnement, le module en tire une au hasard et l'affiche sur la console plutôt que d'ouvrir l'application. |
| 60 | L'API donne accès aux fonctions du modèle selon les spécifications | ✅ | Sept endpoints, dont `/api/message` qui porte le cycle complet. |
| 61 | Recommandations OWASP top 10 intégrées quand nécessaire | ✅ | Six mesures nommées et tenues : A01 (401 avant toute recherche de ressource), A02 (scrypt, HMAC, comparaisons en temps constant), A05 (cookie `httponly`/`samesite=strict`/`secure` en HTTPS, clé tirée au hasard au démarrage), A07 (jeton de 12 h, 5 tentatives par fenêtre), A09 (chaque échec journalisé sans jamais recopier la phrase essayée), CSRF (`samesite=strict` et API JSON seulement). S'y ajoutent la validation Pydantic stricte, la liste blanche du chemin de projet et la **neutralisation des injections de prompt** (`app/garde_fous.py`, US-20). |
| 62 | Sources versionnées sur dépôt Git **distant** | ❌ | Voir constat nº 1. |
| 63 | Tests couvrant tous les points de terminaison | ✅ | `tests/test_api.py` couvre les sept endpoints. |
| 64 | Tests s'exécutant sans bug, résultats interprétés | ✅ | `62 passed`. Vérifié au commit `d783b9a`. |
| 65 | Documentation : architecture, endpoints, règles d'authentification | ✅ | Architecture dans `CONTEXTE_COMPLET_PROJET.md`, points de terminaison décrits par OpenAPI avec modèles de sortie et erreurs déclarées (`app/api_schema.py`, `tests/test_contrat_api.py`), règles d'authentification documentées — voir C5-31. |
| 66 | Documentation et API respectant un standard, format accessible | ✅ | OpenAPI pour l'API ; pour les documents, la règle d'accessibilité est écrite et **tenue par la chaîne d'intégration**. |

### C10 — Intégration de l'API dans une application

| # | Critère | Statut | Constat |
|---|---|---|---|
| 68 | Application de départ installée et fonctionnelle en développement | ✅ | `uvicorn app.main:app --reload` sert l'interface et l'API. Vérifié. |
| 69 | Communication avec l'API fonctionnelle | ✅ | Le front mono-fichier `app/static/index.html` appelle les sept endpoints. |
| 70 | Authentification et renouvellement des jetons intégrés | 🟡 | Le front ouvre la session, la ferme, et **tout 401 le ramène au formulaire quel que soit l'appel** (`tests/test_front.py`). Il n'y a en revanche **aucun renouvellement silencieux** : à l'expiration des 12 h, l'artisan ressaisit sa phrase. Acceptable pour une journée de chantier, à nommer devant le jury plutôt qu'à cacher. |
| 71 | Tous les endpoints du projet intégrés selon les spécifications | ✅ | Les sept sont appelés depuis le front. |
| 72 | Adaptations d'interface intégrées | ✅ | Interface conforme RGAA 4.1, désormais **adossée à des maquettes annotées**. L'exercice a produit une adaptation réelle : sous 45 rem, les deux panneaux s'empilent au lieu de se serrer (WCAG 2.1, critère 1.4.10), ce qui manquait pour un produit dont l'entrée est la dictée sur chantier. |
| 73 | Tests d'intégration couvrant tous les endpoints exploités | ✅ | `tests/test_api.py` via `TestClient`. |
| 74 | Tests s'exécutant en totalité, résultats interprétés | ✅ | `62 passed`. |
| 75 | Sources versionnées sur le dépôt Git de l'application | 🟡 | Versionnées localement depuis `e669883`. **Pas de remote.** |

### C11 — Monitorage du modèle

| # | Critère | Statut | Constat |
|---|---|---|---|
| 77 | Métriques expliquées sans erreur d'interprétation | ✅ | Huit métriques définies avec seuils dans `docs/DISPOSITIF_AGENT.md` §4, dont deux au rang sécurité (justesse de la mention ≥ 95 %, prix ou référence inventés = 0). Le raisonnement derrière chaque seuil est écrit. |
| 78 | Outils de monitorage adaptés au contexte | ✅ | Outil fait maison, et l'argument est écrit dans `app/observabilite.py` : JSONL d'un seul fichier, relisible à l'œil, sans dépendance ni service tiers — cohérent avec un produit dont le principe premier est que rien ne sort de la machine. Toute écriture est protégée : un disque plein dégrade l'observabilité, pas le produit. |
| 79 | Au moins un vecteur de restitution temps réel | ✅ | La page `/metriques` agrège le journal à chaque chargement et reste **consultable modèle arrêté** — c'est précisément quand on en a besoin. |
| 80 | Enjeux d'accessibilité pris en compte dans le choix de l'outil | ✅ | Le tableau de bord est un **tableau**, pas un graphique ; l'état d'une métrique est **écrit**, pas seulement coloré. Quatre tests le tiennent (`tests/test_front.py`). |
| 81 | Chaîne testée en bac à sable | ✅ | `tests/test_observabilite.py` (11 tests) exerce l'écriture et l'agrégation sur un journal jetable, `BTP_DONNEES` isolant la racine de données — c'est le bac à sable, et la chaîne d'intégration l'utilise. |
| 82 | Chaîne en état de marche | ✅ | Vérifié en conditions réelles : l'étape « les métriques sont servies » du parcours de bout en bout passe contre le serveur réel. |
| 83 | Sources versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |
| 84 | Documentation d'installation, configuration, utilisation | 🟡 | Les huit métriques, leurs seuils et le sens de comparaison sont écrits (`docs/DISPOSITIF_AGENT.md` §4.3) et recopiés sans réinterprétation dans `SEUILS`. Il manque une **procédure d'installation et d'exploitation** du dispositif rédigée pour quelqu'un d'autre que son auteur. |
| 85 | Documentation au format accessible | ✅ | Voir C8-57 : règle écrite, contrôle mécanique dans la chaîne. |

> **C11 est la compétence la plus déséquilibrée du dossier** : la partie
> difficile — décider *quoi* mesurer et *à quel seuil* — est faite et bien
> faite ; la partie mécanique — collecter, restituer, alerter — est entièrement
> à faire. Huit critères sur neuf tiennent à l'outillage.

### C12 — Tests automatisés du modèle

| # | Critère | Statut | Constat |
|---|---|---|---|
| 87 | Cas à tester listés : partie visée, périmètre, stratégie | 🟡 | La stratégie d'évaluation du modèle est posée (`DISPOSITIF_AGENT.md` §4 : jeu de test de 150-200 exemples écrits à la main, protocole 20b brut contre 20b fine-tuné). Les cas ne sont pas listés un par un. |
| 88 | Outils de test cohérents avec l'environnement | ✅ | pytest, cohérent avec la stack Python/uv. |
| 89 | Tests intégrés respectant la couverture établie | 🟡 | **271 tests** couvrent le code déterministe : référentiel, moteur de devis, pipeline, garde-fous, persistance, API, contrat OpenAPI, transcription, export, authentification, observabilité, boucle qualité, front. S'y ajoute `tools/parcours_bout_en_bout.py`, qui ne neutralise rien (24/24 étapes contre le serveur et `gpt-oss:20b` réels). Aucun test ne porte encore sur le **modèle** lui-même — or c'est l'objet de C12, et cela reste le manque de fond. |
| 90 | Tests s'exécutant sans problème technique | ✅ | `62 passed` en ~4 s. |
| 91 | Sources versionnées sur dépôt Git distant (DVC, GitLab…) | ❌ | Voir constat nº 1. Aucun versionnement de données non plus. |
| 92 | Documentation : installation, dépendances, exécution, couverture | 🟡 | Installation et exécution documentées dans `CLAUDE.md` et `docs/INTEGRATION_CONTINUE.md`. **Aucune mesure de couverture** n'est produite. |
| 93 | Documentation au format accessible | ✅ | Voir C8-57. |

### C13 — Chaîne de livraison continue du modèle (MLOps)

| # | Critère | Statut | Constat |
|---|---|---|---|
| 95 | Documentation couvrant étapes, tâches, déclencheurs | ❌ | Absente. |
| 96 | Déclencheurs intégrés comme définis | ❌ | Absent. |
| 97 | Fichiers de configuration reconnus et exécutés | ❌ | Absent. |
| 98 | Étape de test des données intégrée et sans erreur | ❌ | Absente. |
| 99 | Étapes de test, entraînement et validation du modèle intégrées | ❌ | Absentes. |
| 100 | Sources de la chaîne versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |
| 101 | Documentation d'installation, configuration, test, au format accessible | ❌ | Absente. La chaîne MLOps n'existe pas ; la règle d'accessibilité, elle, est prête à s'y appliquer. |

> C13 est **intégralement à faire**. C'est cohérent avec le calendrier : le
> fine-tuning n'a pas encore eu lieu. Mais c'est sept critères, et la chaîne
> doit exister avant l'entraînement pour pouvoir en porter la trace.

---

## E4 — Application (C14-C19)

### C14 — Analyse du besoin et spécifications fonctionnelles

| # | Critère | Statut | Constat |
|---|---|---|---|
| 103 | Modélisation des données respectant un formalisme (Merise, entités-relations) | ✅ | Même document qu'en C4-19. Il couvre en plus les **structures propres à l'application** — projet, ligne de devis, correction, escalade — et les quatre contraintes d'intégrité qu'un schéma relationnel ne peut pas porter, avec ce qui les vérifie. |
| 104 | Modélisation des parcours utilisateurs (schéma fonctionnel, wireframes) | ✅ | `docs/MAQUETTES.md` — le parcours complet en schéma fonctionnel (les trois points d'arrêt HITL y sont visibles), puis six maquettes filaires. Le document **dit qu'elles ont été dessinées après l'interface** plutôt que de faire croire l'inverse ; à partir de là, les écrans restants (US-01, US-03, US-17) seront dessinés avant d'être codés. |
| 105 | Chaque spécification couvre contexte, scénarios, critères de validation | ✅ | `docs/STORIES.md` : 26 stories, chacune avec son contexte, ses critères d'acceptation et **un cas dégradé**. |
| 106 | Objectifs d'accessibilité intégrés aux critères d'acceptation des user stories | ✅ | 21 stories portent une rubrique « Accessibilité » **au même rang** que le fonctionnel — c'est exactement ce que le critère demande, et c'est rare. |
| 107 | Objectifs d'accessibilité appuyés sur un standard (WCAG, RGAA) | ✅ | RGAA 4.1 nommé 23 fois dans `docs/STORIES.md`, avec les numéros de critère. |

### C15 — Cadre technique

| # | Critère | Statut | Constat |
|---|---|---|---|
| 109 | Spécifications techniques : architecture, dépendances, environnement d'exécution | ✅ | `CADRAGE_MODELE.md` (frontière modèle/code, schéma de sortie), `pyproject.toml` (dépendances épinglées, Python ≥ 3.14), contraintes matérielles argumentées. |
| 110 | Services et prestataires éco-responsables favorisés | 🟡 | Le critère éco-responsable est désormais **instruit** : `docs/BENCHMARK_STT.md` §6 compare ce que chaque fournisseur publie, calcule l'ordre de grandeur local et conclut que le local est la seule option dont l'empreinte soit mesurable par le projet. Reste 🟡 tant qu'aucune consommation n'est **relevée** et qu'aucun prestataire n'est effectivement retenu. |
| 111 | Flux de données représentés par un diagramme de flux | 🟡 | `CONTEXTE_COMPLET_PROJET.md` porte un schéma ASCII du flux. Ce n'est pas un **diagramme de flux de données** au sens formel (DFD niveau 0/1). |
| 112 | Preuve de concept accessible et fonctionnelle en pré-production | 🟡 | La preuve de concept **fonctionne en local et c'est vérifié**, pas supposé : `tools/parcours_bout_en_bout.py` déroule 24 étapes contre le serveur réel et `gpt-oss:20b`, du 401 sans jeton jusqu'à la fermeture, en écrivant un vrai `.docx`. Il n'y a toujours pas d'environnement de pré-production. |
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
| 121 | Interfaces intégrées respectant les maquettes | ✅ | L'interface respecte les maquettes par construction, puisqu'elles en sont tirées. Ce qui rend le critère défendable est ailleurs : **chaque maquette porte ses annotations d'accessibilité et le test qui les tient**. Quatre propriétés annotées n'étaient couvertes par aucun test — lien d'évitement, région vivante du fil, piège de focus de la modale — elles le sont depuis. |
| 122 | Comportements des composants et navigation conformes aux spécifications | ✅ | Validation, modale accessible, arbitrage des quantités, correction de ligne — conformes aux stories. |
| 123 | Composants métier développés et fonctionnels | ✅ | Moteur de devis déterministe : référentiel, taux de chute, rendements, TVA, ventilation, acompte. 12 tests dédiés. |
| 124 | Gestion des droits d'accès développée | 🟡 | L'accès est fermé, testé et journalisé (voir C5-33), mais **il n'y a qu'un seul rôle** : un artisan sur sa machine. Il n'existe donc pas de gestion de droits différenciés, et il n'en faut pas encore — US-01 (comptes) la rendra nécessaire. |
| 125 | Flux de données intégrés conformément aux spécifications | ✅ | La frontière est tenue : le modèle décrit, le code calcule. Le schéma de sortie ne comporte **ni prix ni référence produit** — le modèle ne peut pas halluciner ce qu'il n'a pas la possibilité d'exprimer. |
| 126 | Bonnes pratiques d'éco-conception (éco-index, Green IT) | 🟡 | Le front est **un seul fichier de 36 Ko, sans cadriciel, sans dépendance externe, sans image**, l'audio n'est jamais conservé et HITL-0 filtre avant l'appel modèle plutôt qu'après. C'est de l'éco-conception effective, désormais **revendiquée et argumentée** (`docs/BENCHMARK_STT.md` §6), toujours pas **mesurée** — aucun éco-index n'a été passé. |
| 127 | Préconisations OWASP top 10 implémentées quand nécessaire | ✅ | Mêmes six mesures qu'en C9-61, plus les garde-fous d'entrée. Le front n'ajoute pas de surface : un seul fichier, aucune dépendance externe, aucun script tiers. |
| 128 | Tests unitaires ou d'intégration couvrant composants métier et gestion des accès | ✅ | Composants métier largement couverts ; **la gestion des accès l'est aussi** depuis `0442fbe` — `tests/test_auth.py` couvre le refus sans jeton, le jeton forgé, l'expiration, la limitation de tentatives et la fermeture de session. |
| 129 | Sources versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |
| 130 | Documentation : installation, architecture, dépendances, tests, normes d'accessibilité | ✅ | Installation, architecture, dépendances et tests documentés ; les normes d'accessibilité documentaire sont désormais **écrites et tenues mécaniquement** (`docs/ACCESSIBILITE_DOCUMENTS.md`, étape de la chaîne). |

### C18 — Intégration continue

| # | Critère | Statut | Constat |
|---|---|---|---|
| 132 | Documentation couvrant outils, étapes, tâches, déclencheurs | ✅ | `docs/INTEGRATION_CONTINUE.md` — outil retenu et pourquoi, déclencheurs, étapes une à une avec le motif de chacune, procédure pour reproduire la chaîne en local, et une section « ce que la chaîne ne fait pas encore ». |
| 133 | Outil d'intégration continue sélectionné de façon cohérente | ✅ | GitHub Actions, choisi parce que le dépôt ira sur GitHub et qu'aucun autre service n'est à installer ni à payer. L'argument est écrit. |
| 134 | Chaîne intégrant les étapes préalables aux tests (build, configuration) | ✅ | `actions/checkout`, `astral-sh/setup-uv` avec cache sur `uv.lock`, puis `uv sync --frozen --all-groups` : le lock fait foi, et la chaîne **échoue** s'il a dérivé au lieu de résoudre en silence (c'est INC-07). |
| 135 | Chaîne exécutant les tests au déclenchement | ✅ | `uv run --frozen pytest -q` à chaque déclenchement, suivi du contrôle d'accessibilité documentaire et d'un `node --check` sur le JavaScript du front. |
| 136 | Configurations versionnées sur dépôt Git distant | ❌ | Voir constat nº 1. |
| 137 | Documentation au format accessible | ✅ | Voir C8-57 — et `docs/INTEGRATION_CONTINUE.md` est lui-même dans le corpus contrôlé. |

> **C'était le meilleur rapport effort/points du dossier, et il a été pris.**
> Cinq critères sur six sont fermés par un fichier de trente lignes qui
> réutilise les tests déjà écrits. Le sixième, C18-136, ne demande pas de
> travail : il demande un dépôt distant, et la décision n'est pas la mienne.
> La chaîne est d'ailleurs déjà *utile* — c'est elle qui ferait tomber une
> dérive de `uv.lock` (INC-07), un JavaScript qui ne compile plus, ou un
> document qui casse la hiérarchie de ses titres.

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
| 146 | Arguments en faveur des choix techniques d'outillage | ✅ | Écrits dans `app/observabilite.py` : trois partis pris assumés (le journal ne casse jamais un tour ; un seul fichier JSONL relisible à l'œil, sans dépendance ; on ne mesure que ce qu'on observe vraiment). Les métriques 2 à 5 sont déclarées « non mesurée » plutôt qu'approchées par un chiffre flatteur. |
| 147 | Outils installés et opérationnels au moins en local | ✅ | Journal applicatif et tableau de bord installés et opérationnels en local, vérifiés par le parcours de bout en bout. |
| 148 | Règles de journalisation intégrées aux sources | ✅ | Dix points de journalisation branchés dans les sources : appel au modèle (validité, motif, tentative, latence), tour, escalade, injection neutralisée, hors périmètre, correction de l'artisan selon quatre origines, et échec d'authentification. **Le journal ne porte aucun texte libre** — la dictée reste hors du journal, par construction (`docs/RGPD.md`, T4). |
| 149 | Alertes configurées et en état de marche | 🟡 | Le tableau de bord **écrit** l'état de chaque métrique par rapport à son seuil, et ne s'en remet pas à la couleur. Mais rien n'est émis vers personne : pas de notification, pas de destinataire, pas de valeur de réveil. |
| 150 | Documentation d'installation et de configuration | 🟡 | `README.md` et `docs/INTEGRATION_CONTINUE.md` couvrent l'installation de l'application, donc du journal. La configuration propre au dispositif (rotation, destination, seuils) n'est pas documentée à part. |
| 151 | Documentation au format accessible | ✅ | Voir C8-57. |

### C21 — Résolution d'incidents

| # | Critère | Statut | Constat |
|---|---|---|---|
| 153 | Causes des problèmes identifiées correctement | ✅ | `docs/INCIDENTS.md` — **dix fiches**, chacune avec son symptôme, sa reproduction, sa cause remontée au-delà du symptôme, son correctif et son test de non-régression. Trois portent en plus un « comment il a été trouvé » : le défaut de remise par le parcours réel, la sévérité par emoji, la fuite de la dictée par la rédaction du registre RGPD. |
| 154 | Problème reproduit en environnement de développement | ✅ | Chaque fiche porte sa reproduction, et la commande commune est donnée en tête du journal. Sept des dix incidents ont un test de non-régression dédié dans la suite. |
| 155 | Procédure de débogage documentée depuis l'outil de suivi | 🟡 | La procédure de débogage est écrite une fois pour toutes en tête de `docs/INCIDENTS.md` — reproduire d'abord, écrire le test qui échoue avant le correctif, remonter à la cause, un correctif un commit, relancer la suite entière. Elle n'est pas *tenue depuis un outil de suivi* : le fichier en tient lieu jusqu'à ce que le tableau Notion soit monté. |
| 156 | Solution documentée expliquant chaque étape | ✅ | Chaque fiche explique la solution et ce qu'elle change, pas seulement le fichier touché. |
| 157 | Solution versionnée dans le dépôt (merge request par exemple) | 🟡 | Versionnée par commits atomiques et messages explicatifs. **Sans remote, pas de merge request.** |

> **C21 est presque gratuit et pourtant à zéro.** Le travail d'investigation a
> été fait ; il manque le *format*. Une fiche d'incident par anomalie —
> symptôme, cause, reproduction, correctif, test de non-régression, commit —
> ferme cinq critères avec des faits déjà établis. Six anomalies sont
> disponibles immédiatement.

---

## Ce qu'il faut faire, dans l'ordre du rendement

1. **Créer le dépôt distant et pousser.** Neuf critères, une commande. *(Décision de l'utilisateur : je n'ai pas le droit de pousser.)*
2. ~~**Chaîne d'intégration continue** (`.github/workflows/`).~~ **Fait** : `tests.yml` et `docs/INTEGRATION_CONTINUE.md`. Cinq des six critères de C18 sont fermés ; le sixième attend le dépôt distant.
3. ~~**Fiches d'incident** pour les anomalies déjà corrigées.~~ **Fait** : `docs/INCIDENTS.md`, dix fiches. → C21 pour l'essentiel.
4. ~~**Quatre séances de veille** au gabarit.~~ **Fait pour une** (08/09/2026), et pas pour quatre : voir la note de C6. La suite est un rituel à tenir, pas un document à écrire. → C6.
5. ~~**Registre des traitements de données personnelles** + procédures de tri.~~ **Fait** le 08/09/2026 : `docs/RGPD.md`. Trois critères fermés, et un défaut de confidentialité trouvé et corrigé au passage. → C4.
6. ~~**Journalisation applicative** branchée sur les escalades et corrections existantes.~~ **Fait** : `app/observabilite.py`, dix points de journalisation, tableau de bord `/metriques`. → C20 et C11 largement fermés.
7. ~~**Modèle Merise** du référentiel métier et du catalogue.~~ **Fait** : `docs/MODELE_DONNEES.md`. C4-19 et C14-103 fermés, C4-20 passe à partiel, et le schéma cible du catalogue est prêt pour C2.
8. ~~**Authentification de l'API.**~~ **Fait** : `app/authentification.py`, 19 tests. C5-31, C5-33, C9-59, C9-61, C9-65 fermés ; C10-70 et C17-124 restent 🟡 (pas de renouvellement de jeton, un seul rôle).
9. ~~**Wireframes** de l'interface existante.~~ **Fait** : `docs/MAQUETTES.md`, six maquettes annotées. C14-104, C17-121 et C10-72 fermés, quatre tests d'accessibilité ajoutés au passage.
10. ~~**Benchmark STT** avec colonne éco-responsable.~~ **Fait** : `docs/BENCHMARK_STT.md`. Six des sept critères de C7 fermés, C7-48 reste 🟡 faute de mesure ; C15-110 et C17-126 passent à partiel. Le protocole de mesure est écrit et attend un corpus de trente dictées.

**Ce qui reste, en une phrase.** Pousser le dépôt (neuf critères), **tenir** le
protocole de mesure du banc d'essai plutôt que l'écrire (trois critères à
mi-chemin), et la chaîne MLOps de C13 (sept) — le reste est du rituel à tenir,
pas du travail à inventer. Les quatre gisements documentaires de la liste
ci-dessus sont fermés.

---

*Audit établi le 08/09/2026, révisé le même jour sur le dépôt à l'état du
commit `4ee3870`. Les statuts décrivent ce qui est dans le dépôt à ce
commit-là, pas ce qui est prévu — et pas ce qui a été écrit depuis.*
