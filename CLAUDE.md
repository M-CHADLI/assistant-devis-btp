# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Dépôt de **cadrage / documentation** pour un projet de soutenance d'AI Engineer. Il ne contient
aujourd'hui **aucun code** : uniquement des specs Markdown, des supports HTML et des images.
Toute la documentation est rédigée **en français** — conserver cette langue pour les nouveaux fichiers.

Dépôt git, mais pas de système de build, de lint ou de tests. Ne pas inventer de telles commandes.

## Arborescence et statut des documents

Le projet a pivoté. Le rangement porte le statut : **`docs/` fait autorité, `archive/` non.**

```
README.md              porte d'entrée
CLAUDE.md              ce fichier
PLANNING.md            calendrier des 4 mois
docs/                  la conception — fait autorité
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
- **`docs/NOTES.md`** — bloc-notes des idées non encore arbitrées. Ce qui y est tranché remonte
  dans les documents de conception, et la note est retirée.
- **`docs/SOURCES_DONNEES.md`** — ancienne conception *RenoAssistant*, **périmée en tant
  qu'architecture**, mais conservée car toujours utile : structure du dump catalogue Leroy Merlin
  et contrainte légale sur les données (structure réelle, valeurs simulées). Ne pas la traiter
  comme la cible actuelle.
- **`veille/`** — livrables de veille IA / marché de l'emploi. **Pas hors sujet** : c'est la
  compétence « veille technique et réglementaire ». La thématique doit toutefois être recadrée
  sur un outil ou une réglementation du projet (voir `docs/LIVRABLES.md`).
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

**Un seul interlocuteur au début, deux à la fin.** La scène finale réunit le client et *son*
artisan (pas un partenaire LM), à distance en simultané. **L'artisan fait autorité, toujours** ;
ses corrections sont journalisées comme signal qualité.

**Décisions de cadrage figées :**
- Chantier pilote : **peinture et sols** uniquement (référentiel de 20-30 matériaux).
- Canal de démo : **web uniquement**. Le SMS reste une capacité du modèle, non démontrée.
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
