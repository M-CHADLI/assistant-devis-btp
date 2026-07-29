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

### Les trois fonctions

L'agent fait trois choses, dans l'ordre :

| | Fonction | Ce qu'elle fait | Qui parle |
|---|---|---|---|
| 1 | **Interroger** | Passe d'une intention floue à un projet cadré : surface, budget, existant, contraintes | Client |
| 2 | **Calculer** | Traduit le projet en matériaux et quantités, y compris ce qu'on oublie toujours | Personne — le modèle travaille |
| 3 | **Arbitrer** | Chiffre, puis laisse le client et son artisan ajuster jusqu'à l'accord | Client + artisan |

Le produit se résume en une phrase : **un seul interlocuteur au début, deux à la
fin.** Le client arrive seul avec une intention, il repart avec un accord.

La troisième fonction n'est pas un aboutissement passif. Le devis n'est pas un
document livré, c'est un objet qu'on négocie à deux et que l'agent tient à jour.

### La scène finale — devis interactif à deux

Le client et son artisan — celui qu'il a engagé, pas un partenaire Leroy Merlin —
ouvrent le devis ensemble, **chacun de son côté, en simultané**. Ils discutent avec
l'agent, à la voix ou au clavier, et valident ligne à ligne.

**Autorité différenciée.** Les deux interlocuteurs ne pèsent pas pareil. Une demande
du client est une *préférence* (« je veux du carrelage blanc »). Une objection de
l'artisan est une *correction technique* (« il faut du placo hydrofuge, pas du
standard ») — et il a raison contre le modèle.

**Règle retenue : l'artisan fait autorité, toujours.** Sa correction est appliquée
sans discussion et **journalisée comme signal qualité**.

Conséquence importante pour le projet : chaque correction d'artisan est une donnée
d'expert, gratuite et qualifiée. Elle alimente directement la boucle qualité (voir
`DISPOSITIF_AGENT.md` §5). Un professionnel qui corrige le modèle en production vaut
mieux qu'une journée d'entretien avec un vendeur.

**Deux avertissements de périmètre :**

- Le temps réel partagé (sessions synchronisées, présence, conflits d'édition) est
  de la **plomberie** : plusieurs semaines de travail qui ne démontrent rien sur le
  sujet de la soutenance. Côté modèle, le design est identique que les deux soient
  sur une tablette ou sur deux écrans — l'agent voit une conversation à trois voix.
  Démontrer avec deux fenêtres sur la même machine est acceptable.
- Le distanciel **simplifie** la voix : chacun sur son micro, donc on sait toujours
  qui parle. En présentiel il aurait fallu séparer deux voix sur un seul micro —
  problème difficile et hors sujet.

### Détail interne — 6 capacités

Les trois fonctions se décomposent en six capacités, qui sont le vrai découpage du
dataset et de l'évaluation. Elles n'ont pas à être présentées séparément : elles se
déduisent.

| Fonction | Capacités |
|---|---|
| Interroger | Clarification, Décomposition en lots |
| Calculer | Quantitatif, Consommables oubliés |
| Arbitrer | Devis structuré sans prix, Injection prix + promos |

Réserve assumée sur ce regroupement : « Arbitrer » réunit une étape modèle (le
devis) et une étape code (les prix), ce qui brouille légèrement la frontière
architecturale du §2. Le choix est de la nommer plutôt que de changer le découpage.

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
décompose → quantifie → produit le devis → rattrape les oublis → chiffre au prix
promo → **le client et son artisan arbitrent et valident ensemble**.

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

Génération synthétique par un gros modèle, puis revue humaine. 2000 exemples à la
main ne sont pas tenables en 4 mois.

**Vigilance :** un seul modèle + un seul prompt = 2000 variantes de trois exemples.
Faire varier explicitement les axes : type de pièce, surface, budget, niveau du
bricoleur, précision de la formulation.

#### Le référentiel métier — livrable intermédiaire

Le risque principal du projet : un modèle généraliste ne *connaît* pas les valeurs
métier (rendements, taux de chute, ordre des lots). Il produit du **plausible**, pas
du **juste**. Générer les exemples directement depuis sa mémoire revient à entraîner
le modèle sur de l'expertise inventée — apprise parfaitement, restituée avec
assurance, et invisible à la relecture.

**Chaîne retenue :**

```
Documentation fabricants  →  référentiel de faits validé  →  génération des exemples
```

Ne jamais court-circuiter l'étape du milieu. Une valeur fausse se corrige à un seul
endroit et on régénère ; diluée dans 2000 exemples, elle est irrécupérable.

Chaque valeur du référentiel porte **sa source** (« 4 kg/m², fiche technique Weber,
p. 3 »). C'est ce qui rend le travail défendable en soutenance.

**Source retenue : documentation technique des fabricants uniquement.**
Publique, elle fait autorité, et les fiches donnent les rendements explicitement.
Critère de sélection : **les fabricants dont Leroy Merlin vend les produits** — ça
borne la liste et aligne le référentiel sur le catalogue.

Sources écartées pour l'instant :

- **Normes (DTU)** — vendues par l'AFNOR et le CSTB, non librement accessibles.
  Les scraper poserait un problème de droits, visible sur un projet lié à une enseigne.
  Contournement : les docs fabricants reprennent légalement les prescriptions DTU
  applicables à leurs produits.
- **Transcriptions YouTube** — sources non techniques, transcriptions automatiques
  peu fiables sur les chiffres et unités, et volume qui écraserait mécaniquement les
  bonnes sources. Si réintroduites plus tard : vocabulaire, gestes et erreurs
  courantes uniquement, **jamais une valeur numérique**.

**Limite de périmètre — impérative.** Le pipeline d'extraction est un projet en soi
et peut absorber les 4 mois, laissant le projet sans modèle fine-tuné. Plafond :
**2 à 3 semaines**, et un référentiel volontairement étroit — les 20 à 30 matériaux
qui couvrent le parcours de démo salle de bain. Élargissement seulement si le reste
avance vite.

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

- [ ] **Protocole de preuve du fine-tuning** — à décider *avant* d'entraîner :
      modèle de référence, métriques, jeu de test gelé. Conditionne tout le reste
- [ ] Répercuter la scène à deux acteurs dans `DISPOSITIF_AGENT.md` : le point
      d'intervention HITL-2 devient multipartite, la fiche projet porte deux
      utilisateurs de statut différent, les corrections d'artisan entrent dans la
      boucle qualité
- [ ] La voix : modalité d'entrée à décider (essentielle à la démo, ou confort ?).
      Impacte la validation des entrées, pas le modèle
- [ ] Liste des fabricants et des fiches techniques à extraire (20-30 matériaux)
- [ ] Format du référentiel métier
- [ ] Schéma JSON détaillé de chaque `payload` (au moment d'écrire le code)
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
