# Couverture des livrables — grille de contrôle

> **Ce document n'est pas le projet.** Le projet est décrit dans
> `CADRAGE_MODELE.md` et `DISPOSITIF_AGENT.md`, et il vaut par lui-même.
> Ceci est une **grille de contrôle** : elle vérifie que l'Assistant Bricolage,
> tel qu'il est cadré, produit bien les cinq livrables attendus — et signale
> les endroits où il n'en produit aucun.
>
> Sens de lecture : **on ne dénature pas le projet pour cocher une case.** Quand
> une compétence n'est pas couverte, il y a deux réponses possibles — une
> extension naturelle du projet, ou l'assumer comme un manque. Les deux sont
> écrites ci-dessous.
>
> Source : `reference/referentiel-rncp-ai-engineer.xlsx` (21 compétences,
> 5 livrables).

## Vue d'ensemble

| Livrable | Compétences | Format attendu | Couverture |
|---|---|---|---|
| **E1** — Données | C1-C5 | 2-5 p., 15 min | ⚠️ Le maillon faible |
| **E2** — Veille et benchmark | C6-C8 | 15-20 p., 15 min | 🟡 C6 recadré et outillé ; manque les séances et C7 |
| **E3** — Modèle IA | C9-C13 | 15-20 p., 20 min + démo | 🟢 Le cœur du projet |
| **E4** — Application | C14-C19 | 15-20 p., 20 min | 🟡 Conçu, pas construit |
| **E5** — Exploitation | C20-C21 | 2-5 p., 10 min | 🔴 Absent |

Trois exigences sont **transverses** et reviennent dans la majorité des
compétences. Aucune n'est traitée aujourd'hui :

- **Accessibilité** — citée dans 8 compétences, sur les *documents* comme sur
  l'interface. Un standard à choisir une fois (RGAA ou WCAG) et à tenir partout.
- **OWASP top 10** — exigé sur les deux API (C9, C17).
- **Éco-conception / éco-responsabilité** — critère de choix des services (C7,
  C15) et des développements (C17).

---

## E1 — Extraction et stockage des données (C1-C5)

**Ce que le projet donne déjà.** `SOURCES_DONNEES.md` porte la structure du dump
catalogue Leroy Merlin et la contrainte légale (structure réelle, valeurs
simulées). Le référentiel métier du mois d'août est, lui, une collecte de
données de fabricants.

**Ce qui manque.** C1 exige un **mix** de sources : service web (API REST),
fichier de données, **scraping**, base de données, et **système big data**. Le
script doit être fonctionnel et versionné. S'y ajoutent la modélisation
**Merise** (C4), le **registre des traitements de données personnelles**, les
procédures de tri RGPD, et une **API REST de mise à disposition** du jeu de
données (C5).

**L'extension naturelle.** Le référentiel métier est déjà une collecte
multi-sources — il suffit de la *programmer* au lieu de la faire à la main :

| Source exigée | Ce que le projet peut y mettre |
|---|---|
| Scraping | Fiches techniques des fabricants (peinture, sols) |
| Fichier de données | Dump catalogue LM (structure réelle, valeurs simulées) |
| API REST | Un service externe — OCR des devis, ou données publiques BTP |
| Base de données | Le référentiel métier lui-même, une fois modélisé |
| Big data | Le point le plus artificiel — à arbitrer avec l'encadrant |

Le RGPD n'est pas un hors-sol ici : `DISPOSITIF_AGENT.md` §2 décrit déjà quatre
mémoires avec des durées de rétention et un consentement révocable. Le registre
des traitements en découle presque directement.

**Décision à prendre.** Le « système big data » est la seule exigence qui n'a pas
de place évidente dans le projet. À poser à l'encadrant avant d'inventer un
Spark décoratif.

---

## E2 — Veille et benchmark (C6-C8)

**Ce que le projet donne déjà.** `veille/` contient quatre livrables de veille
sur l'IA et le marché du travail. C'était classé « hors sujet » — c'était une
erreur de lecture : **c'est C6.**

**Ce qui manque.**

- ~~C6 exige une **récurrence planifiée** (au moins une heure hebdomadaire) et
  des **outils d'agrégation** cohérents.~~ **Fait** — `veille/DISPOSITIF.md`
  pose le rituel (vendredi, 1 h) et `veille/sources.opml` les cinq flux
  vérifiés. **Reste à produire la trace** : les comptes rendus dans
  `veille/seances/`. Le dispositif ne vaut que par eux.
- ~~C6 exige aussi que la thématique porte sur un outil ou une réglementation
  mobilisée dans le projet.~~ **Tranché** : **Unsloth et le fine-tuning de MoE**.
  Le devis BTP et la TVA travaux ont été écartés — trop stables pour une séance
  hebdomadaire sur quatre mois ; ils restent traités comme référentiel métier.
- **C7 — le benchmark de services IA préexistants** n'existe nulle part. C'est
  pourtant la justification la plus utile du projet : pourquoi fine-tuner
  gpt-oss plutôt que d'appeler une API généraliste. Le benchmark doit lister les
  services **écartés et pourquoi**, et documenter la démarche éco-responsable de
  chacun.
- **C8 — paramétrer un service IA préexistant** : l'API OCR du §6 est
  exactement ça. Il faut la documenter comme telle (accès, configuration,
  monitorage, dépendances).

**À faire.** ~~Recadrer la thématique de veille, poser le rituel hebdomadaire~~
(fait, voir `veille/DISPOSITIF.md`), **tenir les séances**, et écrire le
benchmark C7 — qui est de toute façon un argument de soutenance.

---

## E3 — Le modèle IA (C9-C13)

**Le cœur du projet.** C'est ici que le fine-tuning, le dataset, le référentiel
métier et le protocole de preuve trouvent leur place.

| Compétence | État |
|---|---|
| C11 — Monitorage du modèle | 🟢 Les 8 métriques de `DISPOSITIF_AGENT.md` §4. Manque le **vecteur de restitution temps réel** (dashboard) |
| C12 — Tests automatisés du modèle | 🟡 Le jeu de test gelé existe dans le planning. Manque leur **programmation** et la couverture |
| C9 — API exposant le modèle | 🔴 À développer : authentification, OWASP, tests de tous les endpoints, OpenAPI |
| C13 — Chaîne de livraison continue MLOps | 🔴 Absent : déclencheurs, test des données, entraînement et validation dans la chaîne |

**Le point à comprendre.** C12 et C13 ne parlent pas de tester le *code* mais de
**valider les jeux de données, la préparation, l'entraînement et l'évaluation**
— une approche MLOps. Le projet a déjà la matière : le référentiel versionné,
les bornes de plausibilité, les seuils d'acceptation. Ce sont des règles de
validation automatisables, pas des intentions.

C'est l'extension la plus rentable du projet : elle transforme le protocole de
preuve du §7 en chaîne exécutable.

---

## E4 — L'application (C14-C19)

**Ce que le projet donne déjà.** `DISPOSITIF_AGENT.md` couvre largement C14 et
C15 : workflow, points d'intervention humaine, mémoire, garde-fous. Le
diagramme de flux de données exigé par C15 existe en partie dans
`archive/renoassistant/DIAGRAMMES.md`, à refaire pour l'architecture actuelle.

**Ce qui manque.**

- **Formalisme.** C14 exige un formalisme nommé — Merise ou entités-relations
  pour les données, schéma fonctionnel ou **wireframes** pour les parcours. Les
  wireframes de l'interface web n'existent pas.
- **Accessibilité dans les critères d'acceptation.** C14 demande que les
  objectifs d'accessibilité soient intégrés **aux critères d'acceptation des
  user stories**, adossés à WCAG ou RGAA. À faire au moment d'écrire les user
  stories, pas après.
- **C16 — conduite agile.** Cycles, rituels, kanban, backlog, burndown. Le
  `PLANNING.md` est un calendrier, pas une conduite agile. À outiller.
- **C17 — développement.** L'interface web à deux sessions du §4, plus OWASP,
  plus éco-conception, plus tests d'intégration.
- **C18 et C19 — intégration et livraison continues de l'application**, distinctes
  de la chaîne MLOps de C13. 🔴 Absent.
- **Preuve de concept en pré-production** (C15) avec une conclusion tranchée sur
  la poursuite du projet. Le protocole 20b brut vs fine-tuné *est* cette preuve
  de concept — il suffit de l'énoncer comme telle.

---

## E5 — Exploitation (C20-C21)

**🔴 Rien aujourd'hui.** C'est le livrable le plus court (2-5 pages) et le plus
facile à obtenir tard, mais il exige du **code qui tourne** : journalisation
dans les sources de l'application, seuils d'alerte configurés et fonctionnels,
et un incident **réellement reproduit et résolu**, documenté depuis un outil de
suivi.

**Ce qu'il faut prévoir dès maintenant**, parce que ça ne se rattrape pas :

- Journaliser dès le premier jour de développement, pas à la fin.
- Tenir un **outil de suivi des incidents** (issues Git suffit) pendant tout le
  projet. C21 demande la trace de la procédure de débogage — elle ne se
  reconstitue pas de mémoire.
- La journalisation touche des données utilisateur : elle doit respecter les
  durées de rétention de `DISPOSITIF_AGENT.md` §2.

---

## Ce que cette grille change au planning

Le `PLANNING.md` couvre E3 et une partie de E4. Il ne dit rien de E1, E2 et E5.
Deux conséquences :

1. **La collecte du référentiel d'août doit être programmée, versionnée et
   documentée** — sinon le travail est fait mais le livrable E1 n'existe pas.
2. **Trois choses doivent démarrer maintenant et courir tout du long** : le
   rituel de veille hebdomadaire, l'outil de suivi des incidents, et la
   journalisation. Aucune ne se rattrape en fin de parcours.

## Points à trancher avec l'encadrant

- [ ] Le « système big data » de C1 — quelle forme acceptable dans ce projet ?
- [ ] Le standard d'accessibilité retenu (RGAA ou WCAG), une fois pour tout
- [x] La thématique de veille C6 — **outil : Unsloth et fine-tuning MoE**
      (31/07/2026). À confirmer auprès de l'encadrant, mais le dispositif est
      posé et le rituel peut démarrer sans attendre.
- [ ] E4 et E5 exigent une application déployée : jusqu'où va l'exigence de
      déploiement réel ?
