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
aucune collecte — voir `docs/LIVRAISON_CONTINUE.md`.

**Pas de linter configuré. Ne pas en inventer un.**

## Arborescence et statut des documents

Le projet a pivoté. Le rangement porte le statut : **`docs/` fait autorité, `archive/` non.**

```
README.md              porte d'entrée
CLAUDE.md              ce fichier
PLANNING.md            calendrier des 4 mois
docs/                  la conception — fait autorité
docs/STORIES.md        les 28 stories et l'ordre du backlog
docs/notion/           schémas et CSV de la transposition Notion
docs/MODELE_DONNEES.md le modèle de données — conceptuel constaté, logique cible
docs/MAQUETTES.md      parcours utilisateur et maquettes filaires annotées
docs/BENCHMARK_STT.md  le banc d'essai reconnaissance vocale — instruit, non tranché
docs/RGPD.md           registre des traitements et procédures de tri
docs/CHAINE_DONNEES.md la chaîne de collecte, nettoyage et mise en base du catalogue
docs/CHAINE_MLOPS.md   la chaîne du modèle : test des données, préparation, entraînement
app/                   l'implémentation (FastAPI, moteur de devis, front)
tests/                 la suite pytest
tools/                 outillage hors produit (CLI Notion, chaînes données et modèle)
mlops/                 la déclaration de la chaîne du modèle et ses hyperparamètres
dataset/               les exemples de référence et de contrôle de la validation
catalogue/             la chaîne de données : sources, extraits bruts, jeu agrégé
veille/                livrables de veille
reference/             référentiel de compétences
archive/renoassistant/ conception précédente
```

- **`docs/CADRAGE_MODELE.md`** — document de référence **actuel**. Décrit l'*Assistant Bricolage
  fine-tuné* (le projet en cours). Toute nouvelle décision s'aligne dessus.
- **`docs/DISPOSITIF_AGENT.md`** — workflow, mémoire, garde-fous, plan d'évaluation.
- **`docs/LIVRABLES.md`** — grille de contrôle de la couverture des cinq livrables attendus.
  **Ce n'est pas le projet** : le projet vaut par lui-même, cette grille ne fait que signaler
  les manques. Ne jamais dénaturer le cadrage pour cocher une case.
- **`docs/STORIES.md`** — le découpage en 28 stories, sept épiques, deux files de priorité.
  Chaque story porte un cas dégradé, des critères d'accessibilité **au même rang** que les
  critères fonctionnels, et une ligne de traçabilité qui dit l'état du code **constaté**.
  Sa mise à jour fait partie de la définition de fini.
- **`docs/RGPD.md`** — registre des traitements, procédures de tri, détail des opérations et de
  leur fréquence. Écrit **depuis le code** : chaque donnée personnelle listée est citée avec son
  module. Nomme aussi ce qui reste en défaut (aucune purge implémentée, aucun tri avant
  entraînement) plutôt que de décrire des mesures inexistantes.
- **`docs/MODELE_DONNEES.md`** — modèle Merise : conceptuel et dictionnaire des données
  **décrivent le code constaté**, le modèle logique est une **cible** (il n'y a pas de base de
  données). Les quatre déclencheurs de la migration y sont nommés — tant qu'ils ne sont pas
  atteints, ne pas introduire de base.
- **`docs/MAQUETTES.md`** — le parcours de bout en bout et six maquettes filaires, chacune
  annotée des règles d'accessibilité qu'elle porte **et du test qui les tient**. Les écrans
  restants s'y dessinent **avant** d'être codés, annotations comprises.
- **`docs/BENCHMARK_STT.md`** — le banc d'essai des six services de reconnaissance vocale, plus
  ceux écartés sans étude. **Il instruit l'arbitrage « 100 % local » sans le trancher** : le choix
  entre Whisper/Parakeet locaux et Gladia distant appartient à l'auteur du projet, et le document
  dit ce que chaque branche change dans le code. Ses chiffres sont **documentaires** : le
  protocole de mesure (§8) n'a pas encore tourné — ne pas présenter ses estimations comme des
  mesures, ni laisser une mesure future trancher un principe.
- **`docs/NOTION_BOARD.md`** — comment poser cette organisation sur Notion (thème JIRA) sans le
  connecteur MCP, qui charge 42 outils pour six appels utiles.
- **`docs/NOTES.md`** — bloc-notes des idées non encore arbitrées. Ce qui y est tranché remonte
  dans les documents de conception, et la note est retirée.
- **`docs/CHAINE_DONNEES.md`** — la chaîne qui va de trois sources hétérogènes (export
  fournisseur simulé, API Base Carbone de l'ADEME, page Wikipédia) à une base SQLite
  interrogeable. Modules dans `tools/donnees/`, tests dans `tests/test_chaine_donnees.py`.
  **Deux règles y sont non négociables** : rien n'est rejeté en silence (chaque ligne écartée
  est comptée avec son motif) et aucune valeur n'est inventée (les peintures n'ont pas de masse
  volumique publiée, le champ reste vide et porte sa réserve). La colonne
  `qualite_correspondance` dit `exacte`, `proxy` ou `absente` — ne jamais laisser l'aval prendre
  un proxy pour une mesure. La chaîne **n'alimente pas encore** `app/catalogue.py` : la couture
  est décrite au §8 du document.
- **`docs/CHAINE_MLOPS.md`** — la chaîne du modèle : `donnees` → `preparation` →
  `entrainement` → `validation`, déclarées dans `mlops/pipeline.toml` et exécutées par
  `tools/mlops/executer.py` (`uv run python -m tools.mlops.executer`).
  **Trois principes à ne pas défaire** : la chaîne connaît **trois** états — `réussi`,
  `échoué`, `ignoré` — parce que confondre « pas encore lancé » avec « réussi » ferait
  mentir le rapport ; la **détection de fuite** entre `dataset/entrainement.jsonl` et
  `dataset/essai.jsonl` est bloquante et sans tolérance, c'est la seule mesure honnête du
  projet ; l'étape d'entraînement **ne simule rien** et ne produit aucun artefact factice.
  L'écart à la répartition cible, lui, est écrit et non bloquant : un dataset déséquilibré
  se rééquilibre en écrivant des exemples. Tests dans `tests/test_mlops.py`.
- **`docs/SOURCES_DONNEES.md`** — ancienne conception *RenoAssistant*, **périmée en tant
  qu'architecture**, mais conservée car toujours utile : structure du dump catalogue Leroy Merlin
  et contrainte légale sur les données (structure réelle, valeurs simulées). Ne pas la traiter
  comme la cible actuelle.
- **`veille/`** — la compétence « veille technique et réglementaire » (C6). Le dispositif est
  décrit dans `veille/DISPOSITIF.md` : thématique **Unsloth et fine-tuning MoE**, cinq flux dans
  `sources.opml`, rituel d'une heure le vendredi, comptes rendus dans `veille/seances/` au format
  `GABARIT-SEANCE.md`. Les quatre supports HTML « IA et marché de l'emploi » sont la **thématique
  précédente**, écartée car le référentiel exige un outil ou une réglementation du projet —
  conservés, non reconduits.
- **`reference/referentiel-rncp-ai-engineer.xlsx`** — les 21 compétences et 5 livrables attendus.
  Matière première de `docs/LIVRABLES.md`, à ne pas paraphraser ailleurs.
- **`archive/renoassistant/`** — le reste de l'ancienne conception : `DIAGRAMMES.md`, le PDF de
  cadrage des flux, les images de user story SMS, le handoff dataset devis. Valeur historique
  uniquement.

## Idées directrices du projet (à respecter dans tout code futur)

Quand du code apparaîtra, il découlera de ces principes posés dans `docs/CADRAGE_MODELE.md` :

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

**Un seul interlocuteur, du début à la fin : l'artisan.** Le pivot B2B vocal a supprimé la
session à deux : à la validation de structure (HITL-2), « le client n'a plus de rôle actif »
(`docs/DISPOSITIF_AGENT.md` §1.4). Le client final n'est **pas utilisateur** du produit — pas de
compte, pas d'écran ; seules ses coordonnées sont saisies, parce que les mentions obligatoires
BTP les exigent. **L'artisan fait autorité, toujours** ; ses corrections sont journalisées comme
signal qualité.

**Décisions de cadrage figées :**
- Chantier pilote : **quatre corps de métier** — peinture, sols, plomberie, électricité
  (`PLANNING.md`, `docs/DISPOSITIF_AGENT.md` §3.3). Les deux derniers rendent les exemples
  `mention forte` réels plutôt qu'hypothétiques.
- Entrée du produit : **la voix** (dictée sur chantier, relecture systématique en HITL-0 avant
  traitement). Canal de démo : **web uniquement**. Le SMS appartient à l'ancienne conception.
- Protocole de preuve : **20b brut (bien promptté) vs 20b fine-tuné**. Le 120b est la démo, pas
  la preuve.
- TVA, mentions obligatoires BTP et unités du secteur appartiennent au **référentiel métier** ;
  le modèle *qualifie* le taux, le code calcule tous les montants.
- L'OCR devis image/PDF → Markdown passe par une **API externe**, jamais par le modèle.

Le « second cercle » (question technique, arbitrage budget, reco produit) est optionnel ; le
diagnostic de pathologie et l'estimation de main d'œuvre sont explicitement **écartés**.

## Contraintes techniques structurantes

- Cible matérielle : **NVIDIA DGX Spark** (128 Go mémoire unifiée, bande passante 273 Go/s — le vrai
  goulot). La vitesse de decode dépend des **paramètres actifs**, pas du total → **MoE + quantization FP4**.
- Modèles retenus : **gpt-oss-20b** (LoRA 14 Go, itérations rapides, validation du dataset) puis
  **gpt-oss-120b** (LoRA 65 Go via Unsloth, modèle de démo). Les deux en Apache 2.0.
- Fine-tuning via **Unsloth** (LoRA), 100 % local — les données ne sortent jamais de la machine.
- gpt-oss embarque des refus de sécurité pré-entraînés : les cas sensibles (gaz, électrique, structure)
  **doivent figurer au dataset** avec le comportement voulu (informer, jamais certifier), sinon refus
  imprévisibles en démo.
- Jeu de test : 150-200 exemples écrits/corrigés **à la main**, jamais vus à l'entraînement — seule
  mesure honnête.

## Outils

- Diagrammes Mermaid (`archive/renoassistant/DIAGRAMMES.md`) : rendus sur https://mermaid.live
  ou dans tout Markdown.
- Skills projet dans `.claude/skills/` : `brainstorming`, `writing-plans`,
  `subagent-driven-development` (copiées depuis le plugin perso `mehdi-superpowers`).
- Le `docker-compose.yml` (PostgreSQL + pgvector, Redis) figurant dans `docs/SOURCES_DONNEES.md` appartient
  à l'ancienne conception RenoAssistant, pas au projet actuel.
