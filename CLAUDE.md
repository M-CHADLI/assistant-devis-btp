# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Dépôt de **cadrage / documentation** pour un projet de soutenance d'AI Engineer. Il ne contient
aujourd'hui **aucun code** : uniquement des specs Markdown, des supports HTML/PPTX et des images.
Toute la documentation est rédigée **en français** — conserver cette langue pour les nouveaux fichiers.

Pas de dépôt git, pas de système de build, de lint ou de tests. Ne pas inventer de telles commandes.

## Le pivot — ce qui fait autorité

Le projet a pivoté. L'ordre de lecture et le statut des documents comptent :

- **`CADRAGE_MODELE.md`** — document de référence **actuel**. Décrit l'*Assistant Bricolage fine-tuné*
  (le projet en cours). Toute nouvelle décision s'aligne dessus.
- **`SOURCES_DONNEES.md`** (racine) — ancienne conception *RenoAssistant*, **périmée en tant
  qu'architecture**, mais conservée à la racine car toujours utile : structure du dump catalogue
  Leroy Merlin et contrainte légale sur les données (structure réelle, valeurs simulées).
  Ne pas la traiter comme la cible actuelle.
- **`archive-renoassistant/`** — le reste de l'ancienne conception : `DIAGRAMMES.md`, le PDF de
  cadrage des flux, les images de user story SMS. Valeur historique uniquement.
- **`hors-sujet-veille-ia/`** — livrables de **veille IA / marché de l'emploi**, sans rapport avec
  le projet Assistant Bricolage. Ne pas en tenir compte.

## Idées directrices du projet (à respecter dans tout code futur)

Quand du code apparaîtra, il découlera de ces principes posés dans `CADRAGE_MODELE.md` :

- **Le modèle décrit, il ne calcule jamais.** Le LLM produit du JSON structuré (intention, lots,
  quantités, références) ; un **code Python déterministe** fait les requêtes catalogue, les calculs
  et le devis. Frontière stricte à ne pas franchir.
- **Devis généré sans prix.** Le modèle sort la structure et les quantités (stable) ; le catalogue
  injecte prix et promos a posteriori (volatil). Objectif : zéro hallucination de prix.
- **Schéma de sortie unique** partagé par les 6 fonctions du noyau — le modèle signale sa tâche via
  `intent`, le code route derrière :
  ```json
  { "intent": "clarification | lots | quantitatif | devis | consommables",
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

Le produit se démontre en **un seul parcours utilisateur continu** (« je refais ma salle de bain »
→ le modèle interroge → décompose → quantifie → produit le devis → rattrape les oublis → chiffre au
prix promo). Six fonctions, chacune adossée au schéma `intent` :

1. **Clarification** — poser les bonnes questions avant de répondre (sépare le jouet du produit).
2. **Décomposition en lots** — projet → gros œuvre, plomberie, finitions (100 % dépendant du FT).
3. **Quantitatif** — poser les calculs (m², rendements, chutes).
4. **Devis structuré sans prix** — le livrable central (JSON : lots, lignes, quantités, réfs).
5. **Consommables oubliés** — colle, joints, vis, EPI (fonction différenciante, expertise pure).
6. **Injection prix + promos** — côté code déterministe, jamais côté modèle.

Le « second cercle » (question technique, arbitrage budget, reco produit, adaptation SMS/web) est
optionnel ; le diagnostic de pathologie et l'estimation de main d'œuvre sont explicitement **écartés**.

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

- Diagrammes Mermaid (`archive-renoassistant/DIAGRAMMES.md`) : rendus sur https://mermaid.live
  ou dans tout Markdown.
- Skills projet dans `.claude/skills/` : `brainstorming`, `writing-plans`,
  `subagent-driven-development` (copiées depuis le plugin perso `mehdi-superpowers`).
- Le `docker-compose.yml` (PostgreSQL + pgvector, Redis) figurant dans `SOURCES_DONNEES.md` appartient
  à l'ancienne conception RenoAssistant, pas au projet actuel.
