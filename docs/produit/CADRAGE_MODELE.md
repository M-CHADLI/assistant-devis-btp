# Cadrage du modèle — Application B2B vocale pour prestataires BTP

> Document de référence **de l'état courant**. L'historique des choix et leurs raisons sont dans
> `docs/DECISIONS.md` ; ce document-ci ne les raconte pas.

---

## 1. Le produit

Une application web B2B pour prestataires de services (priorité BTP). L'artisan décrit son
chantier **à la voix** ; le pipeline produit un devis structuré, qu'il valide et corrige seul ;
le devis est ensuite modifiable dans l'interface et exportable en Word. La V1 s'arrête là ;
facture, signature électronique et relances client sont des pistes d'extension pour la suite.

| | |
|---|---|
| Utilisateur | L'artisan, seul. Le client final n'est pas utilisateur (ses coordonnées sont saisies pour les mentions obligatoires). |
| Entrée | La voix (STT), relecture systématique avant traitement |
| Chantiers pilotes | Peinture, sols, plomberie, électricité |
| Validation | L'artisan seul ; il fait autorité, ses corrections sont journalisées |
| Fin de parcours | Devis modifiable, export Word |
| Référentiel métier | Comblé par le LLM, relu et validé |

**Principes :**
- Le modèle ne calcule jamais les montants — code déterministe pour les prix et totaux.
- Schéma de sortie unique par `intent`.
- Données en Europe : l'application et le modèle tournent sur GCP (Google Cloud Platform), en
  région `europe-west1`, sur des services que nous administrons (`docs/DECISIONS.md` D-18, D-21).
- Le professionnel fait autorité ; ses corrections sont journalisées comme signal qualité.
- Le signal qualité est capturé à **deux points** : correction de transcription (reformulation)
  et correction de devis (artisan).

Le blocage légal sur les données d'enseigne est résolu par des valeurs de catalogue simulées
(`docs/donnees/CHAINE_DONNEES.md` §2).

---

## 2. Principe d'architecture

**Le modèle ne calcule jamais. Il décrit.**

```
Capture audio (plusieurs enregistrements — mesures, notes de chantier)
  ↓
STT (interface web pour l'input ; cible non tranchée — docs/modele/BENCHMARK_STT.md)
  ↓
LLM — correction/reformulation (modèle prompté, pas fine-tuné)
  ↓ (texte validé par l'utilisateur — HITL-0)
LLM fine-tuné → JSON structuré (intention, lots, quantités, réfs)
  ↓
Code Python déterministe → requêtes référentiel/catalogue, calculs, devis final
  ↓
Artisan valide/corrige (voix ou texte) — chaque correction journalisée comme signal qualité
  ↓
Devis modifiable / export Word
```

Le devis est généré **sans prix** : le modèle produit la structure et les quantités (stable) ;
le catalogue injecte prix et promos a posteriori (volatil). Zéro hallucination possible sur les
prix.

### Ce que le fine-tuning achète réellement

| Fine-tuning | Code / catalogue |
|---|---|
| Format de sortie, fiabilité du JSON | Catalogue produits, prix, promos |
| Vocabulaire et ton métier | Calculs, totaux |
| Classification d'intention | Stock, disponibilité |
| Gestes techniques stables | Données temps réel |

Un modèle généraliste sort du JSON valide ~70 % du temps ; la cible fine-tunée est ~98 %. **C'est
la métrique nº 1** (§7). Le chiffre de référence du 20b brut est relevé dans
`docs/modele/CONCLUSION_POC.md`.

### Orchestration

Le pipeline est du Python simple (`app/pipeline.py`) : capture, STT, reformulation, modèle
fine-tuné, outils déterministes, avec des points de validation humaine (`docs/produit/DISPOSITIF_AGENT.md`
§1.4). Aucun framework d'agents n'est utilisé.

### Déploiement

Deux services Cloud Run en région `europe-west1` :

| Service | Contenu | Exposition |
|---|---|---|
| Application | FastAPI, interface, catalogue SQLite embarqué ; projets sur un bucket Cloud Storage monté en volume, une instance au plus | Public, derrière la phrase de passe |
| Modèle | Ollama servant `gpt-oss:20b` sur un GPU NVIDIA L4 (24 Go) | Privé : seule l'identité de service de l'application peut l'appeler |

Le détail et ses raisons sont dans `docs/DECISIONS.md` (D-18, D-19, D-21).

### Services externes

- **Annuaire d'entreprises** : pré-remplit les mentions légales du prestataire à partir du SIRET
  (`app/annuaire.py`). Ce n'est pas une brique d'IA.
- **OCR** : conversion image/PDF d'un devis existant en Markdown pour reprendre sa mise en page
  (`app/gabarit.py`). Jamais par le modèle : gpt-oss est purement textuel.

---

## 3. Choix du modèle et de l'infrastructure

### Le modèle : gpt-oss-20b

| Modèle | Paramètres total / actifs | Licence | Poids servis par Ollama |
|---|---|---|---|
| **gpt-oss-20b** | 21B / ~3,6B | Apache 2.0 | ~14 Go (quantification MXFP4) |

Trois raisons :

- **C'est le modèle de la mesure de référence** : 71,4 % de JSON conforme, relevé avec Ollama
  (`docs/modele/CONCLUSION_POC.md`). Le servir de la même façon en production garde la
  comparaison avec le fine-tuning honnête.
- **C'est un MoE** (*mixture of experts*) : seuls ~3,6 milliards de paramètres sont actifs par
  jeton, ce qui donne une vitesse de génération tenable sur un seul GPU de 24 Go.
- **Licence Apache 2.0** : on peut le fine-tuner et servir le résultat.

Alternatives écartées pour l'instant : Qwen3-30B-A3B (non mesuré), Gemma 4 26B A4B (licence à
vérifier). Le **gpt-oss-120b** de démonstration est **suspendu** : il demandait la DGX Spark,
qui n'est plus disponible (`docs/DECISIONS.md` D-04, D-20).

### Le service du modèle

Ollama sur Cloud Run avec un GPU L4, région `europe-west1`, service privé (D-21). Le service
s'éteint sans trafic : on paie le GPU à la seconde d'activité, au prix d'un démarrage à froid le
temps de charger les poids.

### Le fine-tuning

LoRA (*low-rank adaptation*, adaptation à bas rang) avec Unsloth, sur le 20b. L'adaptateur est
fusionné puis exporté au format d'Ollama, et servi par le même service que le modèle brut. Où
l'entraînement s'exécute n'est pas tranché : proposition d'une machine GPU GCP louée le temps de
l'entraînement (`docs/DECISIONS.md` Q-13).

---

## 4. Périmètre fonctionnel

### Les trois fonctions

| | Fonction | Ce qu'elle fait | Qui intervient |
|---|---|---|---|
| 1 | **Interroger** | Capture le chantier à la voix, passe d'une intention floue à un projet cadré | Artisan, sur chantier |
| 2 | **Calculer** | Traduit le projet en matériaux et quantités, y compris ce qu'on oublie toujours | Le modèle travaille |
| 3 | **Arbitrer** | Chiffre, puis l'artisan valide et corrige seul jusqu'à l'accord | Artisan |

**L'artisan pilote tout le parcours**, du chantier capté à la voix jusqu'au devis exporté. Le
devis n'est pas un document livré d'un bloc : c'est un objet que l'artisan corrige ligne à ligne
et que l'agent tient à jour. Ses corrections sont des **corrections techniques**, appliquées sans
discussion et journalisées (`docs/produit/DISPOSITIF_AGENT.md` §5). **L'artisan fait autorité, toujours.**

### Les six capacités internes

Elles sont le découpage du dataset et de l'évaluation, pas de la présentation.

| # | Fonction | Capacité | Justification |
|---|---|---|---|
| 1 | Interroger | **Clarification** — poser les bonnes questions avant de répondre | Sépare le jouet du produit |
| 2 | Interroger | **Décomposition en lots** — projet → préparation, plomberie, finitions | 100 % dépendant du fine-tuning |
| 3 | Calculer | **Quantitatif** — poser les calculs (m², rendements, chutes) | Cœur technique |
| 4 | Arbitrer | **Devis structuré sans prix** — JSON : lots, lignes, quantités, réfs | Livrable central |
| 5 | Calculer | **Consommables oubliés** — colle, joints, vis, EPI | Expertise métier pure |
| 6 | Arbitrer | **Injection prix + promos** sur le devis | Payoff business (côté code) |

### Parcours de démo

Un chantier continu multi-corps de métier : l'artisan décrit à la voix peinture, sols, plomberie
et électricité en une captation suivie → le pipeline interroge → décompose → quantifie → produit
le devis → rattrape les oublis → chiffre → **l'artisan valide et corrige volontairement une
erreur provoquée**, démontrant le signal qualité en direct. Le devis est ensuite exporté en Word
et/ou édité dans l'interface.

### Chantiers pilotes — quatre corps de métier

| Corps de métier | Rôle | Profondeur |
|---|---|---|
| Peinture | Cœur historique | Large, comblée par le LLM |
| Sols | Cœur historique | Large, comblée par le LLM |
| Plomberie | Rend `mention forte` réel | Large |
| Électricité | Rend `mention forte` réel | Large |

L'argument de différenciation du fine-tuning est **la fiabilité du format JSON** et **la qualité
de structuration vocal → devis**, non l'exactitude des valeurs métier (le référentiel est comblé
par le LLM — voir §6).

### Canal — web uniquement

Une seule interface, web. Aucun autre canal n'est prévu.

### Second cercle (si le temps le permet)

Question technique de mise en œuvre ; ajustement à un budget contraint ; recommandation produit
simple.

### Écarté

**Pistes d'extension au-delà du devis, après la V1 :** facture, signature électronique, relances
client, diagnostic de pathologie du bâtiment, estimation de main d'œuvre.

**Hors périmètre :** comparaison multi-critères, substitutions, alertes promo proactives, export
liste de courses.

---

## 5. Posture sur le conseil réglementé

**Modèle le moins restrictif possible. Mention, jamais refus.**

Le modèle **informe toujours**, mais ne **certifie jamais** : il explique comment ça marche, il
ne valide pas l'installation. C'est la posture d'un professionnel qui conseille sans engager sa
responsabilité à la place de l'artisan.

| Niveau | Domaines | Comportement |
|---|---|---|
| Rien | Peinture, carrelage, pose de meuble | Réponse seule |
| Mention simple | Perçage porteur, étanchéité, découpe | Réponse + point de vigilance |
| Mention forte | Gaz, tableau électrique, structure | Réponse + « faire valider par un pro » |

Avec plomberie et électricité dans le périmètre pilote, les cas `mention forte` sont fréquents
dans le parcours de démo.

**Risque technique :** gpt-oss embarque des refus de sécurité pré-entraînés. Si le dataset ne
traite pas explicitement les cas sensibles, le modèle refusera de façon imprévisible —
typiquement pendant la démo. Ces cas doivent figurer au dataset avec le comportement voulu.

---

## 6. Structure du dataset

### Schéma de sortie unique

Les six capacités partagent une seule enveloppe. Le modèle signale sa tâche via `intent`, le code
route derrière.

```json
{
  "intent": "clarification | lots | quantitatif | devis | consommables | reponse",
  "payload": { },
  "mention": null | "simple" | "forte"
}
```

`reponse` couvre les réponses directes hors devis (question technique, conseil court). Un format
à apprendre, un parseur à écrire, une métrique à mesurer.

### Format d'un exemple

gpt-oss étant un modèle de raisonnement, chaque exemple a trois parties :

```
user      : "Je refais le salon, 22 m² au sol, murs à repeindre, budget 1500 €"

reasoning : Sol 22 m² → stratifié, chutes +8 % (pose droite) → 23,8 m².
            Murs : périmètre ~19 m × 2,50 m = 47,5 m², moins ouvertures
            ≈ 42 m². Peinture 10 m²/L par couche, 2 couches → 8,4 L, plus
            sous-couche 1 couche → 4,2 L. Lots : préparation des supports,
            peinture, sol. Consommables : bandes, enduit de rebouchage,
            sous-couche, barres de seuil, cale de dilatation.

final     : { "intent": "devis", "payload": {...}, "mention": null }
```

Le bloc `reasoning` porte l'expertise métier (rendements, taux de chute, ordre des lots). Sans
lui, on n'entraîne qu'un formateur de JSON. Le champ `user` simule un texte **déjà validé** par
l'artisan via la reformulation : le dataset n'a pas à simuler de bruit de transcription.

### Répartition cible (~2000 exemples)

| Fonction | Volume | Raisonné |
|---|---|---|
| Devis complet | 500 | oui |
| Quantitatif | 400 | oui |
| Décomposition en lots | 300 | oui |
| Consommables oubliés | 250 | oui |
| Clarification | 200 | non (court) |
| Réponses directes | 350 | non (court) |

≈ 72 % de raisonné — proche de la recommandation Unsloth (75 % minimum pour préserver la capacité
de raisonnement de gpt-oss). Les **mentions ne sont pas une catégorie** : elles se répartissent à
travers toutes les autres (~15 % simple, ~5 % forte).

### Production des données et référentiel métier

Le LLM **comble les valeurs métier du référentiel** pour les quatre corps de métier (rendements,
taux de chute par type de pose, temps de séchage, consommables), puis le référentiel est **relu
et validé**. Pas de sourcing systématique ligne à ligne.

Le **scraping des fiches techniques fabricants** continue, comme exercice de collecte distinct
(compétence C1), sans alimenter directement le référentiel d'entraînement.

**Garde-fou non négociable : le jeu de test (150-200 exemples) est écrit et corrigé à la main,
jamais généré.** Il est la seule mesure honnête devant le jury, d'autant plus que le référentiel
d'entraînement n'est pas sourcé.

#### Contenu réglementaire du référentiel

**TVA à trois taux** — le point technique central du secteur :

| Taux | Cas |
|---|---|
| 20 % | Neuf, logement < 2 ans, agrandissement, gros équipements |
| 10 % | Amélioration, entretien, aménagement — logement achevé > 2 ans |
| 5,5 % | Rénovation énergétique et travaux induits — logement > 2 ans |

Pièges à encoder : les fournitures **posées par l'entreprise** suivent le taux réduit, celles
achetées séparément par le client sont à 20 % ; certains gros équipements restent à 20 % même
posés. Un devis réel mélange plusieurs taux → **la ventilation TVA par taux est un champ à part
entière**. *(Détail réglementaire à revérifier avant de figer le référentiel.)*

**Mentions obligatoires d'un devis BTP** : n° de devis, dates d'émission et de validité,
coordonnées émetteur (SIRET, RCS, APE/NAF, TVA intracom. — pré-remplies depuis l'annuaire),
**assurance décennale**, client, adresse de chantier (parfois ≠ adresse client), détail par
poste, ventilation TVA, acompte (souvent 30 %), délai d'exécution, « Bon pour accord ».

**Cas limite** : auto-entrepreneur → « TVA non applicable, art. 293 B du CGI », aucune ligne de
TVA.

**Unités du secteur** : m², ml, m³, u, h, j, forfait, ens., kg.

**Frontière.** Le modèle *qualifie* le taux de TVA et *restitue* la structure du devis. Il ne
calcule aucun montant : ventilation, totaux et acompte sont du code. Le SIRET et la décennale
appartiennent à l'artisan, ils ne sont jamais produits par le modèle.

**Reprise du devis de l'artisan.** À l'inscription, l'artisan dépose un devis existant pour que
l'agent reprenne sa mise en page (OCR externe, §2). Le gabarit est stocké en mémoire utilisateur
(`docs/produit/DISPOSITIF_AGENT.md` §2).

---

## 7. Métriques

La métrique nº 1, le **taux de JSON valide**, porte l'intégralité de l'argument de différenciation
du fine-tuning : fiabilité du format et qualité de structuration vocal → devis.

### Protocole de preuve

**gpt-oss-20b brut contre gpt-oss-20b fine-tuné.** Même modèle de base, même jeu de test gelé,
même prompt système. La seule variable est le fine-tuning — tout écart mesuré lui est imputable.

Deux garde-fous :

- Le modèle brut reçoit un **prompt sérieux** (schéma décrit, exemple few-shot). Comparer à une
  baseline mal promptée gonfle artificiellement le résultat.
- Le jeu de test est **gelé avant l'entraînement** et jamais élargi.

Le **gpt-oss-120b** n'est plus au programme tant qu'aucune machine ne permet de l'entraîner
(`docs/DECISIONS.md` D-04).

| Métrique | Pourquoi |
|---|---|
| **Taux de JSON valide** | Métrique nº 1 |
| Exactitude des quantités vs. golden set | Cœur technique |
| Exhaustivité des consommables | Fonction différenciante |
| Justesse du niveau de mention | Sécurité — plomberie/électricité rendent les cas `mention forte` réels |
| Latence p95 d'un devis | Contrainte d'usage — le démarrage à froid du GPU s'y voit |

---

## 8. Points ouverts

Les questions non arbitrées sont tenues dans `docs/DECISIONS.md` (« Questions ouvertes »). Reste
spécifique à ce document :

- [ ] Valider les seuils d'acceptation de `docs/produit/DISPOSITIF_AGENT.md` §4
- [ ] Trancher les points de `docs/pilotage/COUVERTURE_RNCP.md` avec l'encadrant — dont le « système big data »
      et le standard d'accessibilité
- [ ] Revérifier les règles de TVA avant de figer le référentiel
- [ ] Schéma JSON détaillé de chaque `payload`
- [ ] Vérifier la licence réelle de Gemma 4 26B A4B

---

## Sources

- [Vertex AI — fiche du modèle géré gpt-oss-20b (régions, dépréciation)](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/maas/openai/gpt-oss-20b)
- [Cloud Run — prise en charge des GPU](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- [Unsloth — Tutorial: How to Fine-tune gpt-oss](https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune/tutorial-how-to-fine-tune-gpt-oss)
- [Which Open-Source Model Should You Fine-Tune in 2026](https://www.ertas.ai/blog/best-open-source-model-fine-tune-2026)
