# Cadrage du modèle — Application B2B vocale pour prestataires BTP

> Session de brainstorming du 28/07/2026 (pivot RenoAssistant → Assistant Bricolage)
> Pivot du 16/08/2026 (Assistant Bricolage → B2B BTP vocal) — voir
> `docs/superpowers/specs/2026-08-16-pivot-btp-vocal-design.md` pour le détail du raisonnement
> Objectif : cadrer le projet de soutenance

---

## 1. Le produit

**Deux pivots, en bref.** *RenoAssistant* (matching promos SMS, intégration Twilio + pgvector)
→ *Assistant Bricolage fine-tuné* (client final, devis interactif client + artisan, peinture et
sols uniquement) → **Application B2B vocale pour prestataires BTP** (cadrage actuel). Le premier
pivot est documenté dans `archive/renoassistant/`, le second dans
`docs/superpowers/specs/2026-08-16-pivot-btp-vocal-design.md`.

**Le produit actuel.** Une application web B2B pour prestataires de services (priorité BTP).
L'artisan décrit son chantier **à la voix** ; le pipeline produit un devis structuré, qu'il
valide et corrige seul ; le devis est ensuite modifiable dans l'interface et exportable en Word.
Le produit s'arrête là — facture, signature électronique et relances client sont **hors produit,
point final**, pas seulement hors périmètre des 4 mois.

Ce que le pivot vers le B2B vocal change par rapport à l'Assistant Bricolage :

| | Assistant Bricolage | B2B vocal BTP |
|---|---|---|
| Utilisateur principal | Client final | Artisan / prestataire |
| Entrée | Texte | Voix (STT local) |
| Chantier pilote | Peinture et sols uniquement | Peinture, sols, plomberie, électricité |
| Validation du devis | Client + artisan, à deux, en simultané | Artisan seul |
| Fin de parcours | Devis interactif arbitré à deux | Devis modifiable / export Word, côté artisan |
| Référentiel métier | Sourcé systématiquement (une valeur = une source) | Comblé par le LLM (décision assumée, cf. §6) |

**Principes conservés de l'ancien cadrage** (inchangés par ce pivot) :
- Le modèle ne calcule jamais les montants — code déterministe pour les prix et totaux
- Schéma de sortie unique par `intent`
- 100 % local pour le modèle fine-tuné (les données métier ne sortent jamais de la machine)
- Le professionnel fait autorité, ses corrections sont journalisées comme signal qualité

**Principe nouveau, introduit par ce pivot** : le signal qualité est capturé à **deux points** du
pipeline — correction de transcription (reformulation) et correction de devis (artisan) — pas un
seul comme dans l'ancien cadrage.

Ce pivot résout toujours le blocage légal identifié dans `docs/SOURCES_DONNEES.md` (même
dossier) : l'hébergement du modèle reste 100 % local.

---

## 2. Principe d'architecture

**Le modèle ne calcule jamais. Il décrit.**

```
Capture audio (plusieurs enregistrements — mesures, notes de chantier)
  ↓
STT local (type Whisper, tourne sur la DGX Spark — l'audio ne sort jamais de la machine)
  ↓
LLM — correction/reformulation (modèle prompté, pas fine-tuné — collabore avec
  l'utilisateur pour valider le texte)
  ↓ (texte validé par l'utilisateur)
LLM fine-tuné → JSON structuré (intention, lots, quantités, réfs)
  ↓
Code Python déterministe → requêtes référentiel/catalogue, calculs, devis final
  ↓
Artisan valide/corrige (voix ou texte) — chaque correction journalisée comme signal qualité
  ↓
Devis modifiable / export Word — le produit s'arrête ici (facture, signature,
  relances hors produit)
```

Corollaire, inchangé depuis l'ancien cadrage : le devis est généré **sans prix**. Le modèle
produit la structure et les quantités (stable, ne périme pas) ; le catalogue injecte les prix et
promos a posteriori (volatil). Résultat : zéro hallucination possible sur les prix.

### Ce que le fine-tuning achète réellement

| Fine-tuning | RAG / code |
|---|---|
| Format de sortie, fiabilité du JSON | Catalogue produits, prix, promos |
| Vocabulaire et ton métier | Calculs, totaux |
| Classification d'intention | Stock, disponibilité |
| Gestes techniques stables | Données temps réel |

Un modèle généraliste sort du JSON valide ~70 % du temps. Fine-tuné sur un schéma unique : ~98 %.
**C'est la métrique nº 1 du projet** — voir §7 pour ce que cette métrique démontre désormais.

### Orchestration

Un framework d'agents (**LangChain** ou équivalent) pilote l'enchaînement — capture, appel STT,
appel LLM de reformulation, appel LLM fine-tuné, appels d'outils vers le référentiel/catalogue.
C'est une architecture réelle, pas un simple sujet de veille : elle est cohérente avec le
`ModelFallbackMiddleware` déjà exploré dans `docs/NOTES.md` comme piste de robustesse face à
l'hébergement mono-machine.

### API Pappers

Auto-remplit les informations légales du prestataire à l'inscription (SIRET, forme juridique,
adresse) à partir de son numéro SIRET — alimente les mentions obligatoires du devis (§6). Service
externe intégré, documenté comme tel ; il **ne revendique pas de compétence IA** (C8 reste porté
par l'OCR, cf. `docs/LIVRABLES.md`).

### Point ouvert, non bloquant

Un seul modèle chargé qui fait les deux rôles (reformulation promptée + génération JSON
fine-tunée), ou deux modèles séparés — à trancher plus tard sur la base de mesures mémoire
réelles sur la DGX Spark (voir §8).

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

Un MoE de 120B va **20× plus vite** qu'un dense de 70B. D'où l'abandon de l'idée initiale d'un
modèle dense de 40B (~10-12 tok/s estimés).

**Règle retenue : MoE + quantization FP4.** La capacité mémoire héberge tous les experts, la
bande passante n'en paie qu'une fraction.

### Modèles retenus

| Modèle | Total / actifs | Licence | Decode | LoRA VRAM |
|---|---|---|---|---|
| **gpt-oss-20b** | 21B / ~3,6B | Apache 2.0 | 79,7 tok/s | 14 Go |
| **gpt-oss-120b** | 117B / ~5B | Apache 2.0 | 52,9 tok/s | 65 Go |

Alternatives écartées pour l'instant : Qwen3-30B-A3B (Apache 2.0, non mesuré sur Spark), Gemma 4
26B A4B (**licence à vérifier** — sources contradictoires, Apache 2.0 annoncé mais les Gemma sont
historiquement sous licence propre).

### Stratégie en deux temps

1. **gpt-oss-20b** — LoRA en 14 Go, itérations rapides. C'est là que se valide le dataset.
2. **gpt-oss-120b** — une fois le dataset stabilisé. Modèle de démo + slide de comparaison.

Point remarquable : le LoRA du 120B tient en 65 Go via Unsloth, sur une machine qui en a 128.
Entraînement, merge MXFP4 natif et service, tout sur le même bureau, sans cloud.

---

## 4. Périmètre fonctionnel

### Les trois fonctions

L'agent fait trois choses, dans l'ordre :

| | Fonction | Ce qu'elle fait | Qui intervient |
|---|---|---|---|
| 1 | **Interroger** | Capture le chantier à la voix, passe d'une intention floue à un projet cadré (surface, budget, existant, contraintes) | Artisan, sur chantier |
| 2 | **Calculer** | Traduit le projet en matériaux et quantités, y compris ce qu'on oublie toujours | Personne — le modèle travaille |
| 3 | **Arbitrer** | Chiffre, puis l'artisan valide et corrige seul jusqu'à l'accord | Artisan |

Le produit se résume en une phrase : **l'artisan pilote tout le parcours**, du chantier capté à
la voix jusqu'au devis exporté. Le client ne participe qu'en amont, pour ses coordonnées — il n'a
plus de rôle actif à démontrer.

La troisième fonction n'est pas un aboutissement passif. Le devis n'est pas un document livré
d'un bloc, c'est un objet que l'artisan corrige ligne à ligne et que l'agent tient à jour.

### Le point de validation — l'artisan seul

L'artisan ouvre le devis, discute avec l'agent (à la voix ou au clavier), et valide ligne à
ligne. Ses corrections sont des **corrections techniques**, appliquées sans discussion et
**journalisées comme signal qualité**.

**Règle retenue, inchangée : l'artisan fait autorité, toujours.** Chaque correction d'artisan est
une donnée d'expert, gratuite et qualifiée. Elle alimente directement la boucle qualité (voir
`docs/DISPOSITIF_AGENT.md` §5).

Ce point de validation n'est plus une scène à deux acteurs synchronisés : il n'y a qu'un
interlocuteur, l'artisan, ce qui simplifie l'interface à construire (voir `PLANNING.md` §Novembre)
sans rien retirer à la valeur du signal qualité capturé.

### Détail interne — 6 capacités

Les trois fonctions se décomposent en six capacités, qui sont le vrai découpage du dataset et de
l'évaluation. Elles n'ont pas à être présentées séparément : elles se déduisent. Ce découpage est
**inchangé par le pivot** (le spec du pivot ne touche pas au schéma JSON ni au dataset dans sa
forme).

| Fonction | Capacités |
|---|---|
| Interroger | Clarification, Décomposition en lots |
| Calculer | Quantitatif, Consommables oubliés |
| Arbitrer | Devis structuré sans prix, Injection prix + promos |

| # | Fonction | Justification |
|---|---|---|
| 1 | **Clarification** — poser les bonnes questions avant de répondre | Sépare le jouet du produit |
| 2 | **Décomposition en lots** — projet → gros œuvre, plomberie, finitions | 100 % dépendant du fine-tuning |
| 3 | **Quantitatif** — poser les calculs (m², rendements, chutes) | Cœur technique |
| 4 | **Devis structuré sans prix** — JSON : lots, lignes, quantités, réfs | Livrable central |
| 5 | **Consommables oubliés** — colle, joints, vis, EPI | Fonction « wow », expertise métier pure |
| 6 | **Injection prix + promos** sur le devis | Payoff business (côté code) |

Parcours de démo : un chantier continu multi-corps de métier — l'artisan décrit à la voix
peinture, sols, plomberie et électricité en une captation suivie → le pipeline interroge →
décompose → quantifie → produit le devis → rattrape les oublis → chiffre au prix promo →
**l'artisan valide et corrige volontairement une erreur provoquée**, démontrant le signal qualité
en direct (détail du parcours : `docs/superpowers/specs/2026-08-16-pivot-btp-vocal-design.md`
Section 4).

### Chantiers pilotes — quatre corps de métier

**Décision (pivot, Section 3 du spec) : le référentiel et la démo couvrent quatre corps de
métier, à profondeur uniforme.**

| Corps de métier | Rôle | Profondeur |
|---|---|---|
| Peinture | Cœur historique | Large, comblée par le LLM (pas de sourcing systématique) |
| Sols | Cœur historique | Large, comblée par le LLM |
| Plomberie | Démontre `mention forte` | Large aussi |
| Électricité | Démontre `mention forte` | Large aussi |

**Décision assumée et sa conséquence, nommée explicitement.** Le référentiel n'est plus sourcé
systématiquement (une ligne = une valeur = une source, comme dans l'ancien cadrage) — le LLM
comble les valeurs métier pour les quatre corps de métier, y compris peinture et sols qui
portaient auparavant l'argument central du pivot précédent (« le modèle généraliste produit du
plausible, pas du juste »). Détail de la production des données : §6.

**Conséquence pour la soutenance :** l'argument de différenciation du fine-tuning se déplace de
*« exactitude des valeurs métier »* vers *« fiabilité du format JSON »* et *« qualité de
structuration vocal → devis »*. Argument toujours défendable, mais différent — à énoncer comme
tel (voir §7).

Ce que ce choix achète : de la profondeur et du réalisme sur quatre corps de métier au lieu d'un
seul, et des cas `mention forte` réels (plomberie, électricité) plutôt qu'hypothétiques —
important pour §5.

### Canal de démo — web uniquement

**Décision, inchangée : une seule interface, web.** Le point de validation à un seul acteur (§4)
y est naturel. Le SMS reste une *capacité du modèle* — les exemples courts restent au dataset —
mais n'est pas démontré : la plomberie Twilio ne prouve rien sur le fine-tuning.

### Second cercle (si le temps le permet)

- Question technique de mise en œuvre
- Ajustement à un budget contraint (arbitrages de gamme)
- Recommandation produit simple
- Adaptation du format au canal (SMS vs web)
- Scraping ou MCP pour la recherche produit / liste de matériaux — piste notée par le pivot pour
  retrouver un sourcing plus rigoureux du référentiel sans repasser par la collecte manuelle
  (spec, Section 3)

### Écarté

**Hors produit, point final (pas seulement hors périmètre 4 mois) :** facture, signature
électronique, relances client. Le produit s'arrête au devis structuré, modifiable et exportable ;
au-delà, le client se débrouille. Décision assumée : ça simplifie l'architecture (§2) et recentre
l'argument de différenciation sur le devis par la voix.

**Hors périmètre, reconduit de l'ancien cadrage, sans lien avec le pivot :** diagnostic de
pathologie du bâtiment, comparaison multi-critères, substitutions, estimation de main d'œuvre,
alertes promo proactives, export liste de courses.

---

## 5. Posture sur le conseil réglementé

**Décision, inchangée : modèle le moins restrictif possible. Mention, jamais refus.**

Ligne directrice : le modèle **informe toujours**, mais ne **certifie jamais**. Il explique
comment ça marche, il ne valide pas l'installation. C'est la posture d'un professionnel qui
conseille sans engager sa responsabilité à la place de l'artisan — argumentable devant un jury,
contrairement à un refus sec.

| Niveau | Domaines | Comportement |
|---|---|---|
| Rien | Peinture, carrelage, pose de meuble | Réponse seule |
| Mention simple | Perçage porteur, étanchéité, découpe | Réponse + point de vigilance |
| Mention forte | Gaz, tableau électrique, structure | Réponse + « faire valider par un pro » |

Avec les corps de métier plomberie et électricité désormais dans le périmètre pilote (§4), les
cas de `mention forte` cessent d'être des cas rares : ils sont réels et fréquents dans le
parcours de démo. C'est une raison de plus pour ne rien laisser au hasard sur le point suivant.

**Risque technique à anticiper :** gpt-oss embarque des refus de sécurité entraînés en amont. Si
le dataset ne traite pas explicitement les cas sensibles, le modèle refusera de façon
imprévisible — typiquement pendant la démo. Ces cas doivent figurer au dataset avec le
comportement voulu.

---

## 6. Structure du dataset

### Schéma de sortie unique

Décision structurante, inchangée : les 6 fonctions partagent une seule enveloppe. Le modèle
signale lui-même sa tâche via `intent`, le code route derrière.

```json
{
  "intent": "clarification | lots | quantitatif | devis | consommables | reponse",
  "payload": { },
  "mention": null | "simple" | "forte"
}
```

Un format à apprendre, un parseur à écrire, une métrique à mesurer.

`reponse` couvre les réponses directes hors devis (question technique, conseil court). Sans lui,
les 350 exemples courts du dataset n'auraient pas d'intention.

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

Le bloc `reasoning` est le cœur du travail : il porte l'expertise métier (rendements, taux de
chute, ordre des lots). Sans lui, on n'entraîne qu'un formateur de JSON.

**Précision liée au pivot :** le champ `user` de chaque exemple simule un texte **déjà validé**
par l'utilisateur via l'étape de reformulation (§2) — pas un texte vocal brut. Le dataset n'a donc
pas à simuler de bruit de transcription ; le LLM de reformulation nettoie avant que le modèle
fine-tuné ne reçoive le texte.

### Répartition cible (~2000 exemples)

**Structure inchangée par le pivot** — répartition par capacité, indépendante du corps de métier :

| Fonction | Volume | Raisonné |
|---|---|---|
| Devis complet | 500 | oui |
| Quantitatif | 400 | oui |
| Décomposition en lots | 300 | oui |
| Consommables oubliés | 250 | oui |
| Clarification | 200 | non (court) |
| Réponses directes / SMS | 350 | non (court) |

≈ 72 % de raisonné — proche de la recommandation Unsloth (75 % minimum pour préserver la capacité
de raisonnement de gpt-oss).

Les **mentions ne sont pas une catégorie** : elles se répartissent à travers toutes les autres
(~15 % simple, ~5 % forte). La présence de plomberie et d'électricité (§4) rend les exemples
`mention forte` réels à générer, pas hypothétiques.

### Production des données et référentiel métier — décision assumée du pivot

**Ancien principe (Assistant Bricolage), abandonné pour le référentiel d'entraînement :** une
chaîne « documentation fabricants → référentiel de faits validé → génération des exemples », où
chaque valeur portait sa source.

**Nouveau principe (pivot, décision assumée) : le LLM comble les valeurs métier du référentiel**
pour les quatre corps de métier, y compris peinture et sols. Pas de sourcing systématique
ligne à ligne. Ce choix élargit la profondeur du référentiel à quatre corps de métier sans faire
exploser le temps de collecte manuelle (voir `PLANNING.md` §Août).

**Ce que ce choix ne supprime pas : le scraping des fiches techniques fabricants continue**, mais
change de rôle. Il ne nourrit plus directement le référentiel d'entraînement ; il devient un
exercice de collecte de données à part entière, qui sert le livrable E1 (`docs/LIVRABLES.md`,
compétence C1 — collecte multi-sources). Deux usages distincts du scraping, assumés comme tels :
collecte structurée pour C1 d'un côté, référentiel d'entraînement comblé par le LLM de l'autre.

**Garde-fou conservé, non négociable : le jeu de test (150-200 exemples) reste écrit et corrigé à
la main, jamais généré.** Il porte plus de poids que dans l'ancien cadrage puisque le référentiel
d'entraînement n'est plus sourcé — c'est la seule mesure qui reste honnête devant le jury.

#### Contenu réglementaire du référentiel

Le référentiel ne porte pas que des rendements. Il porte aussi les règles qui rendent un devis
crédible — reprises d'une session de recherche antérieure (ex-`HANDOFF.md`). Ce contenu est
**inchangé par le pivot**.

**TVA à trois taux** — le point technique central du secteur :

| Taux | Cas |
|---|---|
| 20 % | Neuf, logement < 2 ans, agrandissement, gros équipements |
| 10 % | Amélioration, entretien, aménagement — logement achevé > 2 ans |
| 5,5 % | Rénovation énergétique et travaux induits — logement > 2 ans |

Pièges à encoder volontairement : les fournitures **posées par l'entreprise** suivent le taux
réduit, celles achetées séparément par le client sont à 20 % ; certains gros équipements restent
à 20 % même posés. Un devis réel mélange plusieurs taux → **la ventilation TVA par taux est un
champ à part entière**. *(Détail réglementaire à revérifier avant de figer le référentiel.)*

**Mentions obligatoires d'un devis BTP** : n° de devis, dates d'émission et de validité,
coordonnées émetteur (SIRET, RCS, APE/NAF, TVA intracom. — auto-remplies via l'API Pappers, §2),
**assurance décennale** (assureur, n° de contrat, couverture géographique), client, adresse de
chantier (parfois ≠ adresse client), détail par poste, ventilation TVA, acompte (souvent 30 %),
délai d'exécution, mention « Bon pour accord ».

**Cas limite à ne pas oublier** : auto-entrepreneur → mention « TVA non applicable, art. 293 B du
CGI », et aucune ligne de TVA.

**Unités du secteur** : m², ml, m³, u, h, j, forfait, ens., kg.

**Frontière maintenue.** Le modèle *qualifie* le taux de TVA applicable et *restitue* la
structure du devis commercial. Il ne calcule aucun montant : la ventilation, les totaux et
l'acompte sont du code. Le SIRET et la décennale appartiennent à l'artisan (auto-remplis via
l'API Pappers), ils ne sont jamais produits par le modèle.

**Reprise du devis de l'artisan.** À l'inscription, l'artisan dépose un devis existant pour que
l'agent reprenne sa mise en page. La conversion image/PDF → Markdown passe par une **API OCR
externe**, jamais par le modèle — gpt-oss est purement textuel et un VLM serait un second projet.
Le gabarit obtenu est stocké en mémoire utilisateur (voir `docs/DISPOSITIF_AGENT.md` §2).

**Jeu de test : 150-200 exemples écrits ou corrigés à la main.** Jamais vus à l'entraînement,
jamais générés. Seule mesure honnête — et plus centrale qu'avant (voir plus haut).

---

## 7. Métriques

### Ce que la métrique nº 1 démontre désormais

Le pivot déplace ce que le taux de JSON valide est censé prouver. Dans l'ancien cadrage, le
référentiel sourcé permettait d'argumenter aussi sur l'exactitude des valeurs métier. Le
référentiel étant désormais comblé par le LLM (§4, §6), cet argument n'est plus disponible tel
quel : la métrique nº 1 porte maintenant l'intégralité de l'argument de différenciation du
fine-tuning, recentré sur **la fiabilité du format** et **la qualité de structuration
vocal → devis**. Argument toujours défendable, mais à énoncer comme tel devant le jury — pas à
laisser dériver silencieusement vers l'ancien argument.

### Protocole de preuve — décidé, inchangé dans sa forme

**gpt-oss-20b brut contre gpt-oss-20b fine-tuné.** Même modèle de base, même jeu de test gelé,
même prompt système. La seule variable est le fine-tuning — donc tout écart mesuré lui est
imputable. C'est la seule comparaison défendable devant un jury.

Deux garde-fous :

- Le modèle brut reçoit un **prompt sérieux** (schéma décrit, exemple few-shot). Comparer à une
  baseline mal promptée gonfle artificiellement le résultat et se détecte en cinq minutes de
  questions.
- Le jeu de test est **gelé avant l'entraînement** et jamais élargi en cours de route.

Le **gpt-oss-120b fine-tuné** reste au programme, mais comme **modèle de démo**, pas comme
preuve. Il répond à « est-ce que ça passe à l'échelle », pas à « est-ce que le fine-tuning sert ».
S'il manque du temps, il saute sans compromettre la démonstration.

| Métrique | Pourquoi |
|---|---|
| **Taux de JSON valide** | Métrique nº 1 — porte maintenant l'intégralité de l'argument de différenciation (voir plus haut) |
| Exactitude des quantités vs. golden set | Cœur technique |
| Exhaustivité des consommables | Fonction différenciante |
| Justesse du niveau de mention | Sécurité — d'autant plus mesurable que plomberie/électricité rendent les cas `mention forte` réels (§5) |
| Decode tok/s | Contrainte machine |
| Comparatif 20b vs 120b | Slide de soutenance |

---

## 8. Points ouverts

- [x] ~~Protocole de preuve~~ — 20b brut vs 20b fine-tuné (§7)
- [x] ~~Chantiers pilotes~~ — peinture, sols, plomberie, électricité, comblés par le LLM (§4, §6)
- [x] ~~Canal de démo~~ — web uniquement, interface unique artisan (§4)
- [x] ~~Planning des 4 mois~~ — voir `PLANNING.md`
- [ ] Un seul modèle chargé pour reformulation + génération JSON, ou deux modèles séparés — à
      trancher sur mesures mémoire réelles sur la DGX Spark (§2)
- [ ] Modèle de reformulation : quel modèle prompté pour l'étape STT → texte validé — non tranché,
      non bloquant (§2)
- [ ] Stack technique de la couche application (GCP, PostHog vs Piano Analytics, Supabase, Gladia
      vs Whisper local pour le STT) — catalogué dans `docs/NOTES.md`, en attente d'une séance de
      grill-me dédiée
- [ ] Valider les seuils d'acceptation de `docs/DISPOSITIF_AGENT.md` §4
- [ ] Trancher les quatre points de `docs/LIVRABLES.md` avec l'encadrant — dont le « système big
      data » et le standard d'accessibilité
- [ ] Liste des fabricants et des fiches techniques à extraire pour les quatre corps de métier
      (peinture, sols, plomberie, électricité) — collecte qui sert désormais C1, indépendamment
      du référentiel d'entraînement (§6)
- [ ] Revérifier les règles de TVA avant de figer le référentiel
- [ ] Format du référentiel métier
- [ ] Schéma JSON détaillé de chaque `payload` (au moment d'écrire le code)
- [ ] Pipeline de génération synthétique
- [ ] Vérifier la licence réelle de Gemma 4 26B A4B
- [ ] Structure du dump catalogue LM (réutiliser celle de `docs/SOURCES_DONNEES.md`)
- [ ] Décider si le second cercle entre dans le périmètre

---

## Sources

- [LMSYS — DGX Spark In-Depth Review](https://www.lmsys.org/blog/2025-10-13-nvidia-dgx-spark/)
- [JetsonHacks — llama.cpp on DGX Spark Benchmarks](https://jetsonhacks.com/wp-content/uploads/2025/10/spark-llamacpp-bench.html)
- [llama.cpp Discussion #16578 — Performance on DGX Spark](https://github.com/ggml-org/llama.cpp/discussions/16578)
- [Unsloth — Tutorial: How to Fine-tune gpt-oss](https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune/tutorial-how-to-fine-tune-gpt-oss)
- [Which Open-Source Model Should You Fine-Tune in 2026](https://www.ertas.ai/blog/best-open-source-model-fine-tune-2026)
