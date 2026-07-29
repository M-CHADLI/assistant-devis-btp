# Cadrage du modèle — Assistant Bricolage fine-tuné

> Session de brainstorming du 28/07/2026
> Objectif : valider le choix de projet de soutenance

---

## 1. Le pivot

**Avant** — *RenoAssistant* : matching sémantique de promos via SMS + filtre agentique sur le site LM.
Techniquement, surtout de l'intégration (Twilio + pgvector + LLM générique).

**Après** — **Assistant Bricolage fine-tuné** : un petit modèle spécialisé, entraîné pour être expert
en bricolage et sur le catalogue Leroy Merlin.

Ce que le pivot apporte :

| | Avant | Après |
|---|---|---|
| Nature du travail | Intégration | R&D IA |
| Différenciation | Faible (stack standard) | Dataset propriétaire + modèle spécialisé |
| Démontrable | Un workflow | Une amélioration mesurable (avant/après FT) |
| Hébergement | Cloud/API | 100 % local — les données ne sortent jamais |

Le dernier point résout le blocage légal déjà identifié dans `SOURCES_DONNEES.md`.

---

## 2. Principe d'architecture

**Le modèle ne calcule jamais. Il décrit.**

```
LLM  →  JSON structuré (intention, lots, quantités, réfs)
          ↓
Code Python déterministe  →  requête catalogue, calculs, devis final
```

Corollaire, et c'est l'idée directrice du projet : le devis est généré **sans prix**.
Le modèle produit la structure et les quantités (stable, ne périme pas) ;
le catalogue injecte les prix et promos a posteriori (volatil).

Résultat : zéro hallucination possible sur les prix, devis exact à 100 %.

### Ce que le fine-tuning achète réellement

| Fine-tuning | RAG / code |
|---|---|
| Format de sortie, fiabilité du JSON | Catalogue produits, prix, promos |
| Vocabulaire et ton métier | Calculs, totaux |
| Classification d'intention | Stock, disponibilité |
| Gestes techniques stables | Données temps réel |

Un modèle généraliste sort du JSON valide ~70 % du temps.
Fine-tuné sur un schéma unique : ~98 %. **C'est la métrique nº1 du projet.**

---

## 3. Choix du matériel et du modèle

### Contrainte machine — NVIDIA DGX Spark

- 128 Go de mémoire unifiée LPDDR5X
- **Bande passante : 273 Go/s** ← le vrai goulot d'étranglement

### Le constat décisif

La vitesse de génération ne dépend pas du nombre total de paramètres, mais des
**paramètres actifs** :

> decode ≈ bande passante / paramètres *actifs*

Benchmarks mesurés (decode = vitesse ressentie) :

| Modèle | Quantization | Decode tok/s |
|---|---|---|
| Llama 3.1 70B — **dense** | FP8 | **2,7** |
| Llama 3.1 8B — dense | FP8, batch 1 | 20,5 |
| gpt-oss-120b — **MoE** | MXFP4 | **52,9** |
| gpt-oss-20b — **MoE** | MXFP4 | **79,7** |

Un MoE de 120B va **20× plus vite** qu'un dense de 70B. D'où l'abandon de
l'idée initiale d'un modèle dense de 40B (~10-12 tok/s estimés).

**Règle retenue : MoE + quantization FP4.** La capacité mémoire héberge tous les
experts, la bande passante n'en paie qu'une fraction.

### Modèles retenus

| Modèle | Total / actifs | Licence | Decode | LoRA VRAM |
|---|---|---|---|---|
| **gpt-oss-20b** | 21B / ~3,6B | Apache 2.0 | 79,7 tok/s | 14 Go |
| **gpt-oss-120b** | 117B / ~5B | Apache 2.0 | 52,9 tok/s | 65 Go |

Alternatives écartées pour l'instant : Qwen3-30B-A3B (Apache 2.0, non mesuré sur
Spark), Gemma 4 26B A4B (**licence à vérifier** — sources contradictoires,
Apache 2.0 annoncé mais les Gemma sont historiquement sous licence propre).

### Stratégie en deux temps

1. **gpt-oss-20b** — LoRA en 14 Go, itérations rapides. C'est là que se valide le dataset.
2. **gpt-oss-120b** — une fois le dataset stabilisé. Modèle de démo + slide de comparaison.

Point remarquable : le LoRA du 120B tient en 65 Go via Unsloth, sur une machine
qui en a 128. Entraînement, merge MXFP4 natif et service, tout sur le même
bureau, sans cloud.

---

## 4. Périmètre fonctionnel

### Noyau de démo — 6 fonctions

Principe : le noyau doit tenir en **une seule démo continue**, un seul parcours utilisateur.

| # | Fonction | Justification |
|---|---|---|
| 1 | **Clarification** — poser les bonnes questions avant de répondre | Sépare le jouet du produit |
| 2 | **Décomposition en lots** — projet → gros œuvre, plomberie, finitions | 100 % dépendant du fine-tuning |
| 3 | **Quantitatif** — poser les calculs (m², rendements, chutes) | Cœur technique |
| 4 | **Devis structuré sans prix** — JSON : lots, lignes, quantités, réfs | Livrable central |
| 5 | **Consommables oubliés** — colle, joints, vis, EPI | Fonction « wow », expertise métier pure |
| 6 | **Injection prix + promos** sur le devis | Payoff business (côté code) |

Parcours de démo : *« je refais ma salle de bain »* → le modèle interroge →
décompose → quantifie → produit le devis → rattrape les oublis → chiffre au prix promo.

### Second cercle (si le temps le permet)

- Question technique de mise en œuvre
- Ajustement à un budget contraint (arbitrages de gamme)
- Recommandation produit simple
- Adaptation du format au canal (SMS vs web)

### Écarté

Diagnostic de pathologie, comparaison multi-critères, substitutions, estimation
main d'œuvre, alertes promo proactives, export liste de courses.

---

## 5. Posture sur le conseil réglementé

**Décision : modèle le moins restrictif possible. Mention, jamais refus.**

Ligne directrice : le modèle **informe toujours**, mais ne **certifie jamais**.
Il explique comment ça marche, il ne valide pas l'installation.
C'est la posture d'un vendeur en magasin — argumentable devant un jury,
contrairement à un refus sec.

| Niveau | Domaines | Comportement |
|---|---|---|
| Rien | Peinture, carrelage, pose de meuble | Réponse seule |
| Mention simple | Perçage porteur, étanchéité, découpe | Réponse + point de vigilance |
| Mention forte | Gaz, tableau électrique, structure | Réponse + « faire valider par un pro » |

**Risque technique à anticiper :** gpt-oss embarque des refus de sécurité entraînés
en amont. Si le dataset ne traite pas explicitement les cas sensibles, le modèle
refusera de façon imprévisible — typiquement pendant la démo. Ces cas doivent
figurer au dataset avec le comportement voulu.

---

## 6. Structure du dataset

### Schéma de sortie unique

Décision structurante : les 6 fonctions partagent une seule enveloppe.
Le modèle signale lui-même sa tâche via `intent`, le code route derrière.

```json
{
  "intent": "clarification | lots | quantitatif | devis | consommables",
  "payload": { },
  "mention": null | "simple" | "forte"
}
```

Un format à apprendre, un parseur à écrire, une métrique à mesurer.

### Format d'un exemple

gpt-oss étant un modèle de raisonnement, chaque exemple a trois parties :

```
user      : "Je refais ma salle de bain, 8 m², budget 5000 €"

reasoning : Surface 8 m² → sol + murs jusqu'à 1,20 m ≈ 14 m² de faïence.
            Chutes +10 % → 15,4 m². Lots : dépose, plomberie, étanchéité,
            revêtements, sanitaires. Budget 5000 € → gamme intermédiaire.
            Étanchéité obligatoire sous douche → mention.

final     : { "intent": "devis", "payload": {...}, "mention": "simple" }
```

Le bloc `reasoning` est le cœur du travail : il porte l'expertise métier
(rendements, taux de chute, ordre des lots). Sans lui, on n'entraîne qu'un
formateur de JSON.

### Répartition cible (~2000 exemples)

| Fonction | Volume | Raisonné |
|---|---|---|
| Devis complet | 500 | oui |
| Quantitatif | 400 | oui |
| Décomposition en lots | 300 | oui |
| Consommables oubliés | 250 | oui |
| Clarification | 200 | non (court) |
| Réponses directes / SMS | 350 | non (court) |

≈ 72 % de raisonné — proche de la recommandation Unsloth (75 % minimum pour
préserver la capacité de raisonnement de gpt-oss).

Les **mentions ne sont pas une catégorie** : elles se répartissent à travers
toutes les autres (~15 % simple, ~5 % forte). Sinon le modèle apprend
« mention = un type de question » au lieu de « mention = une propriété du sujet ».

### Production des données

Génération synthétique par un gros modèle depuis la structure du catalogue,
puis revue humaine. 2000 exemples à la main ne sont pas tenables en 4 mois.

**Vigilance :** un seul modèle + un seul prompt = 2000 variantes de trois exemples.
Faire varier explicitement les axes : type de pièce, surface, budget, niveau du
bricoleur, précision de la formulation.

**Jeu de test : 150-200 exemples écrits ou corrigés à la main.** Jamais vus à
l'entraînement, jamais générés. Seule mesure honnête.

---

## 7. Métriques

| Métrique | Pourquoi |
|---|---|
| **Taux de JSON valide** | Métrique nº1 — mesure directe de l'apport du fine-tuning |
| Exactitude des quantités vs. golden set | Cœur technique |
| Exhaustivité des consommables | Fonction différenciante |
| Justesse du niveau de mention | Sécurité |
| Decode tok/s | Contrainte machine |
| Comparatif 20b vs 120b | Slide de soutenance |

---

## 8. Points ouverts

- [ ] Schéma JSON détaillé de chaque `payload`
- [ ] Pipeline de génération synthétique
- [ ] Vérifier la licence réelle de Gemma 4 26B A4B
- [ ] Structure du dump catalogue LM (réutiliser celle de `SOURCES_DONNEES.md`)
- [ ] Choix du canal de démo (SMS Twilio conservé ? web ? les deux ?)
- [ ] Décider si le second cercle entre dans le périmètre

---

## Sources

- [LMSYS — DGX Spark In-Depth Review](https://www.lmsys.org/blog/2025-10-13-nvidia-dgx-spark/)
- [JetsonHacks — llama.cpp on DGX Spark Benchmarks](https://jetsonhacks.com/wp-content/uploads/2025/10/spark-llamacpp-bench.html)
- [llama.cpp Discussion #16578 — Performance on DGX Spark](https://github.com/ggml-org/llama.cpp/discussions/16578)
- [Unsloth — Tutorial: How to Fine-tune gpt-oss](https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune/tutorial-how-to-fine-tune-gpt-oss)
- [Which Open-Source Model Should You Fine-Tune in 2026](https://www.ertas.ai/blog/best-open-source-model-fine-tune-2026)
