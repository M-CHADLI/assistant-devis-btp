# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Dépôt de **cadrage puis d'implémentation** pour un projet de soutenance d'AI Engineer.
Toute la documentation est rédigée **en français** — conserver cette langue pour les nouveaux fichiers.

Le code vit dans `app/` (FastAPI + moteur de devis déterministe, front mono-fichier dans
`app/static/`), les tests dans `tests/`. Environnement géré par **uv** ; le venv est hors du dépôt
(`~/.venvs/the-project`), donc `pip` n'y est pas installé — passer par
`VIRTUAL_ENV=~/.venvs/the-project uv pip install …`.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run pytest      # la suite de tests
VIRTUAL_ENV=~/.venvs/the-project uv run uvicorn app.main:app --reload
```

Le produit s'empaquette aussi en image OCI (`Dockerfile`) : `docker build -t
assistant-devis-btp:local .` puis `docker run --rm -p 8000:8000
assistant-devis-btp:local`. L'image embarque la base catalogue et ne refait
aucune collecte — voir `docs/exploitation/CHAINE_CI_CD.md`.

**Pas de linter configuré. Ne pas en inventer un.**

## Arborescence et statut des documents

**Ce que l'auteur lit lui-même est à la racine** (`README.md`, `DOSSIER_SPRINT_1.md`,
`PLANNING.md`) ou à la racine de `docs/` (`DECISIONS.md`) ; le reste se range par thème en
sous-dossiers de `docs/` et se consulte à la demande.
**`docs/` décrit l'état courant, rien d'autre.** L'histoire des choix (pivots, décisions remplacées,
questions ouvertes) vit dans **un seul fichier : `docs/DECISIONS.md`**. Un changement de décision
s'écrit là **et** dans le document d'état concerné, dans le même commit. Ne pas réintroduire de
récit de pivot dans les autres documents.

```
README.md              porte d'entrée
CLAUDE.md              ce fichier
PLANNING.md            calendrier des 4 mois
DOSSIER_SPRINT_1.md    le dossier de conception V1 : besoin, périmètre, composante agentique,
                       stack, schémas, contrat, plan — à lire d'abord
docs/DECISIONS.md      LE journal des décisions et les questions ouvertes
docs/produit/          ce que fait le produit : CADRAGE_MODELE (référence), DISPOSITIF_AGENT,
                       STORIES (28 stories), MAQUETTES (parcours et maquettes filaires)
docs/donnees/          les données : CHAINE_DONNEES, MODELE_DONNEES, RGPD
docs/modele/           le modèle : CHAINE_MLOPS, BENCHMARK_STT, CONCLUSION_POC
docs/exploitation/     la mise en service : CHAINE_CI_CD, INCIDENTS, ACCESSIBILITE_DOCUMENTS
docs/pilotage/         la conduite du projet : RITUELS, NOTION_BOARD, COUVERTURE_RNCP
docs/notion/           schémas et CSV de la transposition Notion
docs/sprint/           consignes et grilles des sprints de conception
app/                   l'implémentation (FastAPI, moteur de devis, front)
tests/                 la suite pytest
tools/                 outillage hors produit (CLI Notion, chaînes données et modèle)
mlops/                 la déclaration de la chaîne du modèle et ses hyperparamètres
dataset/               les exemples de référence et de contrôle de la validation
catalogue/             la chaîne de données : sources, extraits bruts, jeu agrégé
veille/                livrables de veille
reference/             référentiel de compétences
```

- **`docs/DECISIONS.md`** — journal unique des décisions (contexte, choix, raison, coût), décisions
  remplacées et questions ouvertes. Les questions ouvertes appartiennent à l'auteur : ne pas les
  trancher à sa place.
- **`docs/produit/CADRAGE_MODELE.md`** — document de référence **actuel** : l'application B2B vocale pour
  artisans BTP fine-tunée. Toute nouvelle décision s'aligne dessus.
- **`docs/produit/DISPOSITIF_AGENT.md`** — workflow, mémoire, garde-fous, plan d'évaluation.
- **`docs/pilotage/COUVERTURE_RNCP.md`** — grille de contrôle de la couverture des cinq livrables attendus.
  **Ce n'est pas le projet** : le projet vaut par lui-même, cette grille ne fait que signaler
  les manques. Ne jamais dénaturer le cadrage pour cocher une case.
- **`docs/produit/STORIES.md`** — le découpage en 28 stories, sept épiques, deux files de priorité.
  Chaque story porte un cas dégradé, des critères d'accessibilité **au même rang** que les
  critères fonctionnels, et une ligne de traçabilité qui dit l'état du code **constaté**.
  Sa mise à jour fait partie de la définition de fini.
- **`docs/donnees/RGPD.md`** — registre des traitements, procédures de tri, détail des opérations et de
  leur fréquence. Écrit **depuis le code** : chaque donnée personnelle listée est citée avec son
  module. Nomme aussi ce qui reste en défaut (aucune purge implémentée, aucun tri avant
  entraînement) plutôt que de décrire des mesures inexistantes.
- **`docs/donnees/MODELE_DONNEES.md`** — modèle Merise : conceptuel et dictionnaire des données
  **décrivent le code constaté**, le modèle logique est une **cible** (il n'y a pas de base de
  données). Les quatre déclencheurs de la migration y sont nommés — tant qu'ils ne sont pas
  atteints, ne pas introduire de base.
- **`docs/produit/MAQUETTES.md`** — le parcours de bout en bout et six maquettes filaires, chacune
  annotée des règles d'accessibilité qu'elle porte **et du test qui les tient**. Les écrans
  restants s'y dessinent **avant** d'être codés, annotations comprises.
- **`docs/modele/BENCHMARK_STT.md`** — le banc d'essai des six services de reconnaissance vocale, plus
  ceux écartés sans étude. **Il instruit le choix du service de transcription sans le trancher**
  (Q-03) : servir Whisper/Parakeet nous-mêmes ou appeler Gladia appartient à l'auteur du projet, et le document
  dit ce que chaque branche change dans le code. Ses chiffres sont **documentaires** : le
  protocole de mesure (§8) n'a pas encore tourné — ne pas présenter ses estimations comme des
  mesures, ni laisser une mesure future trancher un principe.
- **`docs/pilotage/NOTION_BOARD.md`** — comment poser cette organisation sur Notion (thème JIRA) sans le
  connecteur MCP, qui charge 42 outils pour six appels utiles.

- **`docs/donnees/CHAINE_DONNEES.md`** — la chaîne qui va de trois sources hétérogènes (export
  fournisseur simulé, API Base Carbone de l'ADEME, page Wikipédia) à une base SQLite
  interrogeable. Modules dans `tools/donnees/`, tests dans `tests/test_chaine_donnees.py`.
  **Deux règles y sont non négociables** : rien n'est rejeté en silence (chaque ligne écartée
  est comptée avec son motif) et aucune valeur n'est inventée (les peintures n'ont pas de masse
  volumique publiée, le champ reste vide et porte sa réserve). La colonne
  `qualite_correspondance` dit `exacte`, `proxy` ou `absente` — ne jamais laisser l'aval prendre
  un proxy pour une mesure. La chaîne **alimente** le moteur de devis derrière un
  réglage explicite (`BTP_CATALOGUE_SOURCE=base`), par la table lot ↔ famille déclarée dans
  `app/correspondance.py`. Deux lots sur treize y portent `arbitrage_requis` et **ne servent
  pas** : trancher ce qu'ils désignent appartient à l'artisan, pas au code. La couture est
  décrite au §8 du document.
- **`docs/pilotage/RITUELS.md`** — les cinq rituels du projet et la **définition de fini** qui vaut
  pour toute story : comportement **et** cas dégradé, critères d'accessibilité satisfaits,
  tests sur le nominal et le dégradé, ligne de traçabilité de `docs/produit/STORIES.md` mise à jour
  avec l'état **constaté**, décisions écrites dans le document de conception concerné. Le
  point le plus souvent oublié est l'avant-dernier, et c'est le seul qui permette de répondre
  « où en est-on » sans relire le code.
- **`docs/modele/CONCLUSION_POC.md`** — la conclusion de la preuve de concept, adossée à cinq
  exécutions de `tools/parcours_bout_en_bout.py` relevées le 08/09/2026. **Le chiffre à
  connaître** : `gpt-oss:20b` brut produit du JSON conforme dans **71,4 %** des cas (15 sur
  21 appels), contre 98 % visés — c'est la valeur de référence contre laquelle se mesurera le
  fine-tuning. Le reste tient : 0 prix inventé, latence p95 de 12,8 s, 24 étapes sur 24 aux
  cinq exécutions. Ne pas rejouer ces chiffres de mémoire : les relever à nouveau.
- **`docs/modele/CHAINE_MLOPS.md`** — la chaîne du modèle : `donnees` → `preparation` →
  `entrainement` → `validation`, déclarées dans `mlops/pipeline.toml` et exécutées par
  `tools/mlops/executer.py` (`uv run python -m tools.mlops.executer`).
  **Trois principes à ne pas défaire** : la chaîne connaît **trois** états — `réussi`,
  `échoué`, `ignoré` — parce que confondre « pas encore lancé » avec « réussi » ferait
  mentir le rapport ; la **détection de fuite** entre `dataset/entrainement.jsonl` et
  `dataset/essai.jsonl` est bloquante et sans tolérance, c'est la seule mesure honnête du
  projet ; l'étape d'entraînement **ne simule rien** et ne produit aucun artefact factice.
  L'écart à la répartition cible, lui, est écrit et non bloquant : un dataset déséquilibré
  se rééquilibre en écrivant des exemples. Tests dans `tests/test_mlops.py`.

- **`veille/`** — la compétence « veille technique et réglementaire » (C6). Le dispositif est
  décrit dans `veille/DISPOSITIF.md` : thématique **Unsloth et fine-tuning MoE**, cinq flux dans
  `sources.opml`, rituel d'une heure le vendredi, comptes rendus dans `veille/seances/` au format
  `GABARIT-SEANCE.md`. Les quatre supports HTML « IA et marché de l'emploi » sont la **thématique
  précédente**, écartée car le référentiel exige un outil ou une réglementation du projet —
  rangés dans `veille/thematique-precedente/`, non reconduits.
- **`reference/referentiel-rncp-ai-engineer.xlsx`** — les 21 compétences et 5 livrables attendus.
  Matière première de `docs/pilotage/COUVERTURE_RNCP.md`, à ne pas paraphraser ailleurs.

## Idées directrices du projet (à respecter dans tout code futur)

Le code découle de ces principes, posés dans `docs/produit/CADRAGE_MODELE.md` :

- **Le modèle décrit, il ne calcule jamais.** Le LLM produit du JSON structuré (intention, lots,
  quantités, références) ; un **code Python déterministe** fait les requêtes catalogue, les calculs
  et le devis. Frontière stricte à ne pas franchir.
- **Devis généré sans prix.** Le modèle sort la structure et les quantités (stable) ; le catalogue
  injecte prix et promos a posteriori (volatil). Objectif : zéro hallucination de prix.
- **Schéma de sortie unique** partagé par toutes les capacités — le modèle signale sa tâche via
  `intent`, le code route derrière :
  ```json
  { "intent": "clarification | lots | quantitatif | devis | consommables | reponse",
    "payload": { },
    "mention": null | "simple" | "forte" }
  ```
- **`reasoning` obligatoire** dans les exemples raisonnés : c'est lui qui porte l'expertise métier
  (rendements, taux de chute, ordre des lots). Cible ~72 % d'exemples raisonnés (min. 75 % recommandé
  par Unsloth pour préserver le raisonnement de gpt-oss).
- **`mention` est une propriété transverse**, pas une catégorie d'exemples — la répartir à travers
  toutes les fonctions (~15 % simple, ~5 % forte).
- **Métrique nº 1 : taux de JSON valide** (mesure directe de l'apport du fine-tuning).

## Périmètre du noyau de démo

Le produit se démontre en **un seul parcours utilisateur continu** (« je refais mon salon —
peinture et sol » → interroger → calculer → arbitrer). **Trois fonctions**, qui recouvrent six
capacités internes (celles-ci sont le découpage du dataset, pas de la présentation) :

| Fonction | Ce qu'elle fait | Capacités internes |
|---|---|---|
| **1. Interroger** | Intention floue → projet cadré | Clarification, Décomposition en lots |
| **2. Calculer** | Projet → matériaux et quantités | Quantitatif, Consommables oubliés |
| **3. Arbitrer** | Chiffrage, puis accord client + artisan | Devis sans prix, Injection prix + promos |

**Un seul interlocuteur, du début à la fin : l'artisan.** Il n'y a pas de
session à deux : à la validation de structure (HITL-2), « le client n'a plus de rôle actif »
(`docs/produit/DISPOSITIF_AGENT.md` §1.4). Le client final n'est **pas utilisateur** du produit — pas de
compte, pas d'écran ; seules ses coordonnées sont saisies, parce que les mentions obligatoires
BTP les exigent. **L'artisan fait autorité, toujours** ; ses corrections sont journalisées comme
signal qualité.

**Décisions de cadrage figées :**
- Chantier pilote : **quatre corps de métier** — peinture, sols, plomberie, électricité
  (`PLANNING.md`, `docs/produit/DISPOSITIF_AGENT.md` §3.3). Les deux derniers rendent les exemples
  `mention forte` réels plutôt qu'hypothétiques.
- Entrée du produit : **la voix** (dictée sur chantier, reformulée par l'agent sans relecture de
  l'artisan — `docs/DECISIONS.md` D-28). Canal : **web uniquement** ; le SMS est hors projet (`docs/DECISIONS.md` D-11).
- Protocole de preuve : **20b brut (bien promptté) vs 20b fine-tuné**, servis de la même façon.
  Le 120b est suspendu faute de machine (`docs/DECISIONS.md` D-04, D-20).
- TVA, mentions obligatoires BTP et unités du secteur appartiennent au **référentiel métier** ;
  le modèle *qualifie* le taux, le code calcule tous les montants.
- L'OCR devis image/PDF → Markdown passe par une **API externe**, jamais par le modèle.

Le « second cercle » (question technique, arbitrage budget, reco produit) est optionnel ; le
diagnostic de pathologie et l'estimation de main d'œuvre sont explicitement **écartés**.

## Contraintes techniques structurantes

- **Tout tourne sur GCP, en région `europe-west1`** (`docs/DECISIONS.md` D-18 à D-21) : un service
  Cloud Run pour l'application, un second, **privé**, qui sert `gpt-oss:20b` par Ollama sur un
  GPU L4 (24 Go). Le client du modèle doit être **configurable** (URL et authentification par
  identité de service), jamais câblé sur `localhost`. Il n'y a plus de DGX Spark.
- **Cloud Run efface son disque** : tout ce qui doit durer passe par `BTP_DONNEES`, monté sur un
  bucket Cloud Storage, avec une instance au plus. Pas de base de données (D-17).
- Modèle : **gpt-oss-20b** (MoE, ~3,6B paramètres actifs, Apache 2.0). Le 120b est suspendu.
- Fine-tuning via **Unsloth** (LoRA), adaptateur fusionné puis servi par le même service Ollama.
  **Où** il s'exécute est ouvert (Q-13) — ne pas le trancher à la place de l'auteur.
- gpt-oss embarque des refus de sécurité pré-entraînés : les cas sensibles (gaz, électrique, structure)
  **doivent figurer au dataset** avec le comportement voulu (informer, jamais certifier), sinon refus
  imprévisibles en démo.
- Jeu de test : 150-200 exemples écrits/corrigés **à la main**, jamais vus à l'entraînement — seule
  mesure honnête.

## Outils

- Diagrammes Mermaid : rendus sur https://mermaid.live ou dans tout Markdown.
- Skills projet dans `.claude/skills/` : `brainstorming`, `writing-plans`,
  `subagent-driven-development` (copiées depuis le plugin perso `mehdi-superpowers`).
