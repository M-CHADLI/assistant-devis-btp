> **Instruction pour l'agent qui lit ce document.**
> Ton interlocuteur est un **apprenti développeur agentique** qui prépare une soutenance
> d'AI Engineer. Il va discuter de ce projet **à la voix**, en français.
>
> - Réponds **en français**, sur un ton pédagogique et progressif.
> - **Pas de réponses télégraphiques**, pas de gros tableaux : à l'oral, un tableau ne
>   s'écoute pas. Explique en phrases, quitte à être un peu long.
> - Quand tu introduis un terme technique, définis-le en passant, sans t'excuser.
> - **Ce document fait foi** sur l'état du projet. Si l'utilisateur affirme quelque chose
>   qui le contredit, dis-le lui gentiment plutôt que de le suivre.
> - Ce qui est marqué « à faire » n'est **pas** fait. N'invente pas de code qui n'existe pas.

# Assistant chantier BTP vocal — contexte complet

---

## 1. C'est quoi ce projet

### L'objectif métier, en langage simple

Un artisan du bâtiment — peintre, carreleur, plombier, électricien — arrive sur un chantier
pour établir un devis. Aujourd'hui il prend des notes, rentre le soir, et passe une heure à
saisir un devis sur son ordinateur. C'est du temps non facturé, et c'est là que se glissent
les oublis : le ruban de masquage, les cales de dilatation, les barres de seuil.

Le produit qu'on construit fait ceci : **l'artisan décrit son chantier à voix haute, sur
place, et repart avec un devis conforme et chiffré.** Il dicte « je refais le salon,
22 m² au sol, murs à repeindre », relit la transcription, répond à une ou deux questions,
valide la structure proposée, et obtient un document Word aux normes du BTP.

C'est aussi un **projet de certification** : il doit démontrer 21 compétences d'un
référentiel RNCP d'AI Engineer. Cette double nature explique beaucoup de choix — certaines
briques existent parce qu'elles se notent, pas parce qu'elles se voient à la démonstration.

### Le principe qui structure tout le code

Une seule phrase gouverne l'architecture :

> **Le modèle décrit, il ne calcule jamais.**

Le grand modèle de langage produit du **JSON structuré** : quelle est l'intention de
l'artisan, quels lots de travaux, quelles dimensions. Ensuite, du **code Python
parfaitement déterministe** interroge le catalogue, applique les taux de chute, arrondit
aux conditionnements, ventile la TVA et assemble le devis.

Pourquoi cette frontière ? Parce qu'un modèle de langage qui calcule se trompe
*silencieusement*. Il produira « 3 pots de peinture, 240 € » avec le même aplomb, que ce
soit juste ou faux. Un `sum()` en Python, lui, ne se trompe pas.

Le garde-fou est **structurel**, pas incitatif. Le schéma JSON que le modèle doit remplir
ne comporte **ni champ prix, ni champ référence produit**. La formule retenue dans la
conception du projet :

> « Le modèle ne peut pas halluciner ce qu'il n'a pas la possibilité d'exprimer. »

### La pile technique

| Brique | Choix | Pourquoi |
|---|---|---|
| Langage | Python 3.14 | — |
| Gestion des dépendances | **uv** | rapide, et le venv vit hors du dépôt |
| API web | **FastAPI** + uvicorn | validation Pydantic native, OpenAPI gratuit |
| Validation de données | **Pydantic v2** | c'est lui qui rejette une sortie modèle non conforme |
| Modèle de langage | **gpt-oss:20b** servi par **Ollama** en local | Apache 2.0, tourne sur la machine, les données ne sortent jamais |
| Export bureautique | **python-docx** | le devis final est un `.docx` |
| Transcription vocale | **Gladia** (SDK installé) et prototype **Web Speech API** | point non tranché, voir §7 |
| Front | un seul fichier HTML, sans build | 221 lignes, pas de React, pas de bundler |
| Tests | **pytest** 9.1.1 | 20 tests, tous verts |

Il n'y a **pas de base de données**, pas de Docker, **pas de linter configuré**. C'est
volontaire à ce stade — l'état est tenu en mémoire dans le processus.

### Services et ports

```
localhost:8000    l'application (uvicorn)      → l'interface et l'API
localhost:11434   Ollama                       → sert gpt-oss:20b
```

Vérifié le 08/09/2026 : Ollama répond et expose `gpt-oss:20b`, ainsi que
`mixtral:8x22b`, `mixtral:latest`, `gemma4:latest` et `llama2:latest` (le projet
n'utilise que le premier).

### Les points d'entrée

```
GET  /              l'interface web (le fichier HTML unique)
GET  /api/devis     l'état courant du devis (resynchronise après rechargement)
POST /api/message   un tour de conversation : texte → modèle → devis mis à jour
POST /api/corriger  l'artisan supprime une ligne ; la correction est journalisée
POST /api/reset     repart de zéro
GET  /api/export    télécharge le devis en .docx
GET  /docs          la documentation OpenAPI, générée par FastAPI
```

---

## 2. Architecture

### Le flux complet, de la voix au devis

```
   ARTISAN
      │  parle
      ▼
 ┌─────────────┐
 │ 0a. capture │  micro, navigateur
 └─────┬───────┘
       ▼
 ┌─────────────────┐
 │ 0b. TRANSCRIPT. │  ← JAMAIS un modèle génératif
 └─────┬───────────┘
       ▼
 ┌───────────────────────────┐
 │ HITL-0 : l'artisan relit  │  ← 1ᵉʳ point de capture du signal qualité
 │ et corrige le texte       │     (à faire — n'existe pas encore)
 └─────┬─────────────────────┘
       ▼
 ┌────────────────────────────────────────────┐
 │  LE MODÈLE (gpt-oss:20b via Ollama)        │
 │  1. comprend l'intention                   │
 │  2. pose des questions si ça manque (HITL-1)│
 │  3. décompose en lots ordonnés             │
 │  4. exprime les dimensions                 │
 │  → rend UN objet JSON, rien d'autre        │
 └─────┬──────────────────────────────────────┘
       ▼
 ┌────────────────────────────────────────────┐
 │  LE CODE (déterministe, app/devis.py)      │
 │  6.  évalue les formules                   │  ← JAMAIS un modèle
 │  9.  résout le catalogue                   │  ← JAMAIS un modèle
 │  10. injecte prix et promos                │  ← JAMAIS un modèle
 │  11. contrôle la sortie                    │  ← JAMAIS un modèle
 └─────┬──────────────────────────────────────┘
       ▼
 ┌───────────────────────────┐
 │ HITL-2 : l'artisan valide │  ← 2ᵉ point de capture du signal qualité
 │ la structure, PUIS on     │     (partiellement fait : la correction existe,
 │ chiffre                   │      mais le chiffrage est immédiat)
 └─────┬─────────────────────┘
       ▼
   DEVIS .docx
```

Les étapes numérotées 0b, 6, 9, 10 et 11 **ne passent jamais par un modèle génératif**.
C'est écrit noir sur blanc dans la conception, et c'est ce qui rend la garantie
« zéro prix halluciné » tenable.

### Les cinq points de reprise en main humaine (HITL)

*HITL* signifie « human in the loop », l'humain dans la boucle. Le projet en définit cinq,
numérotés de 0 à 4 :

- **HITL-0 — relecture de la transcription.** Systématique. L'artisan relit ce que la
  machine a entendu avant tout traitement. C'est nouveau depuis le virage vocal, et c'est
  aussi une mine de données : l'écart entre ce que la machine a transcrit et ce que
  l'artisan corrige, c'est du signal d'entraînement gratuit.
- **HITL-1 — clarification.** Systématique, mais **plafonné à trois tours**. Au-delà,
  l'agent pose des hypothèses par défaut *explicites* plutôt que d'interroger sans fin.
- **HITL-2 — validation de la structure avant chiffrage.** L'artisan valide **seul** ; le
  client final n'a aucun rôle actif. Le raisonnement derrière : « on fait valider ce qui
  est stable, avant d'y accrocher ce qui est volatil ». Valider un devis déjà chiffré,
  c'est valider le prix ; valider un devis nu, c'est valider le métier.
- **HITL-3 — renvoi vers un professionnel** sur mention forte. L'agent **répond
  complètement**, puis signale. Il ne tronque pas, ne refuse pas, ne moralise pas.
- **HITL-4 — escalade humaine.** Quand les contrôles de sortie échouent de façon répétée.
  « Un agent qui n'a pas de sortie de secours produit des réponses dégradées plutôt que
  d'admettre sa limite. »

### Le schéma de sortie unique

Toutes les capacités du modèle passent par **une seule enveloppe JSON**. Le modèle signale
sa tâche par le champ `intent`, et le code route derrière :

```json
{
  "intent": "clarification | lots | quantitatif | devis | consommables | reponse",
  "payload": { },
  "mention": null | "simple" | "forte"
}
```

`mention` est une **propriété transverse**, pas une catégorie. Elle dit si le sujet touche
un domaine réglementé : rien (peinture, carrelage), « simple » (perçage en mur porteur,
étanchéité), « forte » (gaz, tableau électrique, structure).

---

## 3. Le code, fichier par fichier

### Arborescence commentée

```
app/
  schema.py       51 l.  l'enveloppe JSON et ses payloads — le contrat avec le modèle
  referentiel.py  90 l.  le savoir métier : 13 lots, rendements, taux de chute, TVA
  catalogue.py    67 l.  13 produits simulés : prix, promo, unité de vente, contenance
  devis.py       129 l.  LE MOTEUR — quantités, prix, ventilation TVA. Aucun modèle ici.
  llm.py          95 l.  le client Ollama et le prompt système
  pipeline.py    174 l.  l'orchestrateur : valide, appelle, route, reprend, escalade
  export.py       78 l.  génération du .docx aux normes BTP
  main.py        102 l.  l'API FastAPI, 6 endpoints
  static/
    index.html   221 l.  toute l'interface : HTML + CSS + JS dans un seul fichier

tests/
  test_referentiel.py  57 l.   8 tests — les invariants du référentiel
  test_devis.py       149 l.  12 tests — le comportement du moteur de calcul

tools/
  notion_cli.py         CLI Notion léger (hors produit, outillage de pilotage)

docs/                   la conception — fait autorité
  CADRAGE_MODELE.md     ce qu'est le produit, le dataset, le protocole de preuve
  DISPOSITIF_AGENT.md   le workflow en 11 étapes, la mémoire, les garde-fous, l'évaluation
  STORIES.md            26 stories, 7 épiques, deux files de priorité
  NOTION_BOARD.md       comment poser l'organisation agile sur Notion
  LIVRABLES.md          grille de couverture des 5 livrables du jury
  NOTES.md              idées non encore arbitrées
  SOURCES_DONNEES.md    ancienne conception, gardée pour la contrainte légale sur les données

archive/renoassistant/  la conception d'avant le virage. Valeur historique uniquement.
main.py                 un « Hello world » résiduel, non utilisé
```

### `app/schema.py` — le contrat avec le modèle

C'est le fichier le plus court et le plus important. Il définit ce que le modèle a le droit
de dire. Regarde ce qui **n'y est pas** :

```python
Intent = Literal["clarification", "lots", "quantitatif", "devis", "consommables", "reponse"]
Mention = Literal["simple", "forte"] | None


class Dimension(BaseModel):
    type: Literal["surface", "longueur", "unite"]
    valeur: float = Field(gt=0)


class LigneDevis(BaseModel):
    lot_code: str  # doit exister dans app.referentiel.REFERENTIEL — validé au routage
    dimension: Dimension
    commentaire: str | None = None
```

Une ligne de devis, vue du modèle, c'est un **code de lot** et une **dimension**. Pas de
prix. Pas de référence produit. Pas de total. Le `Field(gt=0)` de Pydantic rejette d'office
une surface négative ou nulle.

### `app/referentiel.py` — le savoir métier

Treize lots répartis sur quatre corps de métier. Chaque lot porte son rendement, son taux
de chute et ses consommables associés :

```python
Lot("PEINT_FINITION", "Peinture de finition (2 couches)", "peinture", "m²",
    consommation_par_unite=0.2, taux_chute=0.05,
    consommables=["bâche de protection", "ruban de masquage"], ordre=3),

Lot("SOL_POSE_CARRELAGE", "Pose carrelage", "sols", "m²", taux_chute=0.10,
    consommables=["colle carrelage", "croisillons", "joint de carrelage"], ordre=3),
```

Trois notions à retenir :

- **`consommation_par_unite`** : 0,2 litre de peinture par mètre carré. C'est le rendement.
- **`taux_chute`** : la fraction perdue à la pose. 5 % en peinture, 8 % pour du stratifié,
  10 % pour du carrelage — parce qu'on coupe plus, et qu'on casse.
- **`ordre`** : l'ordre d'intervention. La préparation avant la sous-couche, la sous-couche
  avant la finition. Ce n'est pas décoratif : ça conditionne le planning du chantier.

Le même fichier porte les mentions réglementaires et les taux de TVA :

```python
MENTIONS: dict[str, str] = {
    "ELEC_TABLEAU": "forte",
    "PLOMB_ALIM": "simple",
    "PLOMB_EVAC": "simple",
}

TAUX_TVA = {
    "20": "Neuf, logement < 2 ans, agrandissement, gros équipements",
    "10": "Amélioration, entretien, aménagement — logement achevé > 2 ans",
    "5.5": "Rénovation énergétique et travaux induits — logement > 2 ans",
}
DEFAULT_TAUX_TVA = "10"
```

### `app/catalogue.py` — les produits

Treize produits simulés. La **structure** est fidèle à ce qu'expose un vrai catalogue de
distributeur ; les **valeurs** sont inventées, parce qu'on n'a pas le droit de redistribuer
un vrai dump catalogue.

```python
Produit("LM-PE-003", "Peinture acrylique mate 10L", "PEINT_FINITION", "u", 79.90,
        promo_pct=0.15, contenance=10),
Produit("LM-SO-003", "Stratifié pose flottante", "SOL_POSE_STRATIFIE", "m²", 16.90,
        promo_pct=0.20),
```

La subtilité, c'est le couple `unite_vente` / `contenance`. Un pot de peinture se vend à
l'unité (`"u"`) et contient 10 litres : il faudra arrondir au pot supérieur. Du stratifié se
vend au mètre carré (`"m²"`) : on peut en commander 23,76 m², pas besoin d'arrondir.

La résolution est délibérément naïve, et le commentaire du code le dit :

```python
def resoudre_produit(lot_code: str) -> Produit | None:
    """Résolution catalogue déterministe : le premier produit du lot (démo).

    En production : critères de gamme, disponibilité, préférence artisan.
    Le modèle ne voit jamais cette fonction — il ne connaît que des `lot_code`.
    """
```

### `app/devis.py` — le moteur, le cœur du projet

C'est ici que tout se calcule, et **aucun modèle n'y met les pieds**. La fonction centrale :

```python
def _quantite_achat(lot_code, type_dimension, valeur) -> tuple[float, Produit | None]:
    lot = REFERENTIEL.get(lot_code)
    if lot is None:
        raise LotInconnu(f"lot_code inconnu du référentiel : {lot_code!r}")

    taux_chute = lot.taux_chute if type_dimension in ("surface", "longueur") else 0.0
    valeur_avec_chute = valeur * (1 + taux_chute)
    quantite_technique = valeur_avec_chute * (lot.consommation_par_unite or 1.0)

    produit = resoudre_produit(lot_code)
    if produit is None:
        return round(quantite_technique, 2), None

    contenance = produit.contenance or 1.0
    quantite_technique_par_contenance = quantite_technique / contenance

    if produit.unite_vente in ("m²", "ml"):
        # Vente au détail : quantité fractionnelle acceptée.
        return round(quantite_technique_par_contenance, 2), produit
    # Vente packagée ("u") : on arrondit au conditionnement supérieur.
    return math.ceil(quantite_technique_par_contenance), produit
```

Déroulons-le sur 20 m² de sous-couche, pour que ce soit concret :

1. Taux de chute de 5 % → 20 × 1,05 = **21 m²**
2. Rendement 0,1 L/m² → 21 × 0,1 = **2,1 litres**
3. Le seau fait 10 L → 2,1 / 10 = **0,21 seau**
4. Le seau se vend à l'unité → `math.ceil(0.21)` = **1 seau**

Noter le détail qui compte : **le taux de chute ne s'applique pas aux dimensions en
`unite`**. On ne « perd » pas 10 % d'un lavabo.

Les totaux sont des propriétés calculées, jamais stockées — donc jamais désynchronisées :

```python
@property
def ventilation_tva(self) -> dict[str, float]:
    """Montant de TVA dû, par taux — un devis réel mélange plusieurs taux."""
    par_taux: dict[str, float] = {}
    for l in self.lignes:
        montant_tva = l.prix_ht * (float(l.taux_tva) / 100)
        par_taux[l.taux_tva] = round(par_taux.get(l.taux_tva, 0.0) + montant_tva, 2)
    return par_taux
```

Un vrai devis BTP **mélange les taux** : 10 % sur la main d'œuvre de rénovation, 20 % sur
un gros équipement. D'où la ventilation, et pas un taux unique.

### `app/llm.py` — le client du modèle et le prompt

Le modèle est appelé chez Ollama, en local :

```python
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gpt-oss:20b"
```

Le prompt système est construit **dynamiquement à partir du référentiel** — c'est
astucieux : ajouter un lot au référentiel Python le rend automatiquement disponible au
modèle, sans toucher au prompt.

```python
LOTS_DISPONIBLES = "\n".join(
    f"- {code} ({lot.corps_metier}, unité {lot.unite}) : {lot.nom}"
    for code, lot in sorted(REFERENTIEL.items())
)
```

Et le cœur de la consigne :

```
RÈGLE ABSOLUE : tu ne produis jamais de prix, jamais de référence produit. Le code
s'en charge après toi. Tu ne connais que des `lot_code` parmi cette liste fermée —
n'en invente aucun

Domaines à mention réglementaire (tu dois répondre puis signaler, jamais refuser)
```

Comme un modèle brut ajoute volontiers du bavardage autour de son JSON, il y a un
extracteur, et une reprise :

```python
def _extraire_json(texte: str) -> dict:
    """Le modèle brut ajoute parfois du texte autour du JSON — on l'isole."""
    match = re.search(r"\{.*\}", texte, re.DOTALL)
    if not match:
        raise SortieModeleInvalide(f"aucun JSON trouvé dans la sortie : {texte[:200]!r}")
    return json.loads(match.group(0))
```

### `app/pipeline.py` — l'orchestrateur

Il fait quatre choses : valider l'entrée, appeler le modèle, router la sortie, et décider
de reprendre ou d'escalader.

Le routage est un simple aiguillage sur `intent`, avec validation Pydantic du payload :

```python
elif intent in ("devis", "lots"):
    p = PayloadDevis.model_validate(payload)
    for ligne in p.lignes:
        if ligne.lot_code not in REFERENTIEL:
            raise LotInconnu(f"lot_code inconnu : {ligne.lot_code!r}")
```

Deux détails valent qu'on s'y arrête.

**L'idempotence.** Un artisan qui parle se répète. « Le salon, 22 m². … Donc le salon,
22 m² de peinture. » Le pipeline reconnaît la reconfirmation et ne crée pas de doublon :

```python
cle = (ligne.lot_code, ligne.dimension.type, ligne.dimension.valeur)
if cle in deja_presentes:
    continue  # reconfirmation orale identique — idempotent, pas un doublon
```

**La mention forcée par le code.** Même si le modèle « oublie » de signaler qu'un tableau
électrique relève d'un domaine réglementé, le code le rajoute depuis le référentiel :

```python
if ligne.lot_code in MENTIONS and MENTIONS[ligne.lot_code] not in mentions:
    mentions.append(MENTIONS[ligne.lot_code])
```

C'est important à comprendre : la sécurité ne repose pas sur la bonne volonté du modèle.

La mémoire de conversation est une fenêtre glissante volontairement courte :

```python
session.historique = session.historique[-10:]  # mémoire de tour glissante
```

### `app/main.py` — l'API

Six endpoints, et une ligne qui explique une bonne partie de ce qui reste à faire :

```python
app = FastAPI(title="Démo — Assistant chantier BTP vocal")

SESSION = Session()
```

**Une seule session, au niveau du module.** Tous les visiteurs partagent le même devis. Pour
une démonstration à un artisan, ça suffit ; pour tout le reste, non. C'est la story US-16.

### `app/export.py` — le devis Word

Génère un `.docx` en mémoire avec `python-docx`. Le numéro, la date, la validité à 30 jours,
un tableau à cinq colonnes, la ventilation TVA, l'acompte de 30 %, les mentions, et le
« Bon pour accord ».

Les informations légales sont pour l'instant des placeholders assumés :

```python
PLACEHOLDER_ARTISAN = {
    "raison_sociale": "[Raison sociale artisan — à renseigner]",
    "siret": "[SIRET — auto-rempli via API Pappers]",
    "assurance_decennale": "[Assureur et n° de contrat décennale]",
}
```

*Pappers* est une API française qui donne l'identité légale d'une entreprise à partir de son
numéro SIRET. Elle remplira ces champs à l'inscription. À noter : cette API **ne compte pas**
comme une compétence en intelligence artificielle, et le projet ne la présente pas comme telle.

### `app/static/index.html` — l'interface

221 lignes, deux panneaux côte à côte : la conversation à gauche, le devis à droite. Pas de
framework, pas d'étape de compilation.

Le bouton de dictée porte un commentaire d'une honnêteté qu'il faut souligner :

```javascript
// Dictée — prototype navigateur (Web Speech API), pas le STT local de production
// (docs/CADRAGE_MODELE.md §2 prévoit un Whisper local sur la DGX Spark).
const Reco = window.SpeechRecognition || window.webkitSpeechRecognition;
```

C'est un **écart assumé et documenté dans le code** : la Web Speech API envoie l'audio chez
l'éditeur du navigateur, ce qui contredit la règle « 100 % local ». Le savoir et l'écrire vaut
mieux que le découvrir en soutenance.

---

## 4. Les concepts clés

**Fine-tuning (affinage).** Réentraîner un modèle existant sur ses propres exemples pour
qu'il adopte un comportement précis. *Analogie :* engager un cuisinier déjà formé et lui
apprendre la carte de votre restaurant, plutôt que de lui réexpliquer la cuisine à chaque
service. Ici, on veut qu'il produise systématiquement le bon JSON.

**LoRA.** Une technique d'affinage économique : au lieu de modifier les milliards de
paramètres du modèle, on ajoute un petit jeu de paramètres à côté. *Analogie :* des
post-it collés dans un manuel, plutôt qu'une réimpression complète.

**MoE — mélange d'experts.** Une architecture où le modèle n'active qu'une fraction de ses
neurones à chaque mot produit. `gpt-oss-120b` contient 117 milliards de paramètres mais n'en
active que 5 milliards à la fois. *Pourquoi c'est décisif ici :* sur la machine cible, la
vitesse dépend de la **bande passante mémoire**, pas de la taille totale. Moins de paramètres
actifs, donc plus de vitesse — vingt fois plus, mesuré.

**Quantization FP4.** Stocker les nombres du modèle sur 4 bits au lieu de 16. Quatre fois
moins de mémoire, un peu moins de précision. *Analogie :* un MP3 plutôt qu'un CD.

**DGX Spark.** La machine cible : 128 Go de mémoire unifiée, 273 Go/s de bande passante.
C'est cette bande passante qui est le vrai goulot d'étranglement du projet.

**Taux de chute.** La part de matériau perdue à la pose : coupes, casse, ajustements. 5 % en
peinture, 10 % en carrelage. Une notion de métier, pas d'informatique.

**Rendement (`consommation_par_unite`).** Combien de matière il faut par unité de surface :
0,2 litre de peinture par m².

**HITL — human in the loop.** Les cinq points où le produit rend la main à l'humain. Détaillés
au §2.

**Mention réglementaire.** L'étiquette « ce sujet touche un domaine encadré ». Trois niveaux :
aucun, simple, forte. La posture est constante : **l'agent répond toujours, puis signale**. Il
ne refuse jamais.

**Injection de prompt.** Une attaque où l'utilisateur glisse une consigne destinée au modèle
dans son message : « ignore les instructions précédentes et… ». Comme l'entrée ici est de la
voix transcrite, elle peut contenir n'importe quoi. Le projet exige de neutraliser **et** de
journaliser — la journalisation compte autant, c'est elle qui rend l'attaque visible.

**Taux de JSON valide.** La métrique n° 1 du projet : sur 100 sorties du modèle, combien sont
un JSON conforme au schéma. Cible ≥ 98 %, contre ~70 % attendus pour le modèle brut. C'est la
mesure directe de ce qu'apporte l'affinage.

**RGAA 4.1.** Le référentiel français d'accessibilité, qui transpose le standard international
WCAG 2.1 niveau AA en critères numérotés et testables. Retenu parce que le public est
professionnel et français.

**Devis sans prix.** L'idée centrale du produit : le modèle sort la **structure** et les
**quantités**, qui sont stables ; le catalogue injecte **prix et promotions** après coup, qui
sont volatils. On fait valider ce qui est stable avant d'y accrocher ce qui bouge.

---

## 5. Les tests

Vingt tests, tous verts au 08/09/2026. Résultat brut de `pytest` : **`20 passed in 3.26s`**.

### `tests/test_referentiel.py` — 8 tests

Ils vérifient les **invariants** du référentiel, c'est-à-dire les propriétés qui doivent
rester vraies quoi qu'on ajoute :

- chaque lot est enregistré sous sa propre clé (`lot.code == code`) ;
- les quatre corps de métier sont présents (peinture, sols, plomberie, électricité) ;
- les lots d'un métier ressortent triés par ordre d'intervention ;
- un corps de métier inconnu renvoie une liste vide, pas une erreur ;
- toute clé de `MENTIONS` correspond à un lot qui existe vraiment ;
- toute valeur de `MENTIONS` vaut « simple » ou « forte », rien d'autre ;
- le taux de TVA par défaut est bien l'un des taux définis ;
- tout taux de chute est compris entre 0 et 0,5 — au-delà, c'est une faute de saisie.

### `tests/test_devis.py` — 12 tests

Ils vérifient le **comportement du moteur** :

- un lot inconnu lève `LotInconnu` plutôt que de produire un devis silencieusement faux ;
- un produit packagé donne une quantité **entière** ;
- un produit vendu au détail garde une quantité **décimale** ;
- le taux de chute est appliqué sur surface et longueur ;
- le taux de chute n'est **pas** appliqué sur une dimension en `unite` ;
- la promotion est déduite du prix ;
- le total HT est bien la somme des lignes ;
- la ventilation TVA regroupe correctement par taux ;
- le TTC est cohérent avec HT + TVA à un centime près ;
- l'acompte vaut 30 % du TTC ;
- les consommables créent des lignes marquées comme telles ;
- les consommables par défaut correspondent à ce que dit le référentiel.

### Une fragilité à connaître

Plusieurs tests de `test_devis.py` **recopient en dur** des valeurs du référentiel et du
catalogue — le taux de chute 0,05, le rendement 0,1, la contenance 10, le prix 34,90, la
promo 0,10. Conséquence : le jour où on ajuste une valeur métier, **le test casse alors que
le code est juste**. Ce sont des tests qui vérifient le calcul *et* les données, au lieu du
seul calcul. À reprendre : lire ces valeurs depuis la source plutôt que les recopier.

Un autre test, celui de la ventilation TVA, se contente d'un `>=` là où une égalité exacte
serait vérifiable. C'est une assertion faible : elle passerait même si le montant était trop
élevé.

### Ce qui n'est pas testé du tout

`app/pipeline.py`, `app/main.py`, `app/llm.py` et `app/export.py` n'ont **aucun test**. C'est
plus de la moitié du code applicatif. Le fait que « les tests passent » ne dit donc rien du
routage, de l'API, ni de l'export.

---

## 6. État actuel

### Ce qui fonctionne — vérifié le 08/09/2026

- La suite de tests passe : `20 passed in 3.26s`.
- L'application démarre et expose ses six endpoints, plus `/docs` et `/openapi.json`.
- Ollama répond sur le port 11434 et sert bien `gpt-oss:20b`.
- Le moteur de devis calcule juste. Vérification faite en direct sur un cas réaliste :
  22 m² de peinture de finition plus 22 m² de stratifié donnent **389,16 € HT**,
  **428,07 € TTC**, acompte **128,42 €**.
- L'export `.docx` se génère avec ventilation TVA, acompte et mentions.
- Le front tient dans un fichier, sans build, et se resynchronise après rechargement.

### Bugs et dettes connus

**Anomalie ouverte — l'intention `quantitatif` n'est pas routée.** Elle figure dans le
`Literal` de `app/schema.py` et le prompt système l'annonce au modèle, mais `_router` n'a
aucune branche pour elle : elle tombe dans le `else` final et lève
`ValueError("intent inconnu du routeur")`. Autrement dit, le modèle a le droit de dire un mot
que le code ne sait pas entendre.

**Les reprises se superposent.** `appeler_modele` réessaie deux fois, et `traiter_message`
réessaie deux fois par-dessus : jusqu'à **quatre appels modèle** pour un seul message, avec un
délai d'attente de 120 secondes chacun. Sur l'objectif de latence (moins de 30 secondes au
95ᵉ centile), c'est intenable.

**Aucune authentification, session unique.** `SESSION = Session()` au niveau du module : tous
les visiteurs partagent le même devis. Rien n'est persisté au-delà du processus.

**Chemin relatif.** `app/main.py` ouvre `"app/static/index.html"` en relatif : lancer
l'application depuis un autre répertoire casse la page d'accueil.

**Accessibilité du front.** Aucun `<label>`, la gravité des mentions passe par la **seule
couleur**, la fenêtre modale n'a ni `role="dialog"`, ni piège de focus, ni fermeture par
`Échap`, les boutons de suppression `✕` n'ont pas de nom accessible, et il manque la balise
`viewport`. Le classement de gravité en JavaScript se fait par **détection de chaîne**
(`startsWith('⚠️')`), ce qui est fragile.

**Écart sur la transcription.** Le prototype utilise la Web Speech API du navigateur, qui
envoie l'audio à distance — contradiction avec la règle « 100 % local ». Le SDK Gladia est
installé mais Gladia est également un service distant. Le choix entre Gladia et un Whisper
local **n'est pas tranché**, et c'est une décision qui appartient à l'utilisateur.

**Conformité du devis incomplète.** L'export applique la TVA **inconditionnellement** : le cas
de l'auto-entrepreneur en franchise de base (article 293 B) n'existe pas. Manquent aussi le
délai d'exécution, l'identité du client, l'adresse de chantier, le RCS, le code APE/NAF et le
numéro de TVA intracommunautaire.

**Non implémenté depuis la conception** : le plafond de trois tours de clarification, la
neutralisation des injections, les bornes de plausibilité par matériau, la journalisation
applicative, le tableau de bord des métriques, le cycle de vie de la mémoire.

**Le dossier `veille/seances/` est vide**, alors que la compétence C6 exige une séance
hebdomadaire tracée.

### Le backlog

Vingt-six stories dans `docs/STORIES.md`, réparties en sept épiques : profil artisan, capture
vocale, interroger, calculer, arbitrer, garde-fous, socle. Les trois épiques centrales sont
exactement les trois fonctions du cadrage ; les quatre autres sont ce qu'il a fallu ajouter
pour que ces trois-là tiennent dans un produit réel plutôt que dans une démonstration de modèle.

Le total fait **122 points**, dont 8 déjà faits — **114 restants**. Le backlog se lit en deux
files distinctes, et c'est un point de méthode important : d'un côté ce qui fait exister la
**démonstration**, de l'autre ce qui se note à la **certification**. Les mélanger reviendrait à
arbitrer au hasard sous la pression du calendrier.

### Historique des décisions

Le projet a **pivoté deux fois**, et il faut le savoir pour ne pas se perdre dans les documents :

1. **RenoAssistant** — mise en relation par SMS entre promotions de magasin et clients, avec
   Twilio et une base vectorielle. Archivé dans `archive/renoassistant/`.
2. **Assistant Bricolage affiné** — grand public, devis à deux (le client et son artisan),
   peinture et sols seulement.
3. **B2B BTP vocal** — le projet actuel, arbitré le 16/08/2026. L'utilisateur est l'artisan,
   seul ; l'entrée est la voix ; le périmètre couvre quatre corps de métier.

Ce que le dernier virage a changé concrètement : le client final **n'est plus utilisateur** du
produit (pas de compte, pas d'écran — seules ses coordonnées sont saisies, parce que les
mentions obligatoires les exigent) ; la validation se fait par l'artisan **seul** ; et le
référentiel métier n'est plus sourcé ligne par ligne mais comblé par un modèle puis relu, ce
qui donne au jeu de test manuel un poids bien plus lourd qu'avant.

Le calendrier tient en quatre mois : août pour le référentiel, septembre pour le dataset et le
jeu de test gelé, octobre pour la preuve chiffrée, novembre pour la démonstration et la
soutenance. La règle qui tient tout le reste : **plus rien n'entre dans le périmètre.**

### Les huit métriques d'évaluation

Elles sont fixées et **ne sont pas négociables à la baisse** pour les deux qui relèvent de la
sécurité (la 5 et la 7) :

1. Taux de JSON valide ≥ 98 % (contre ~70 % en référence)
2. Exactitude des quantités, écart ≤ 5 % → ≥ 90 %
3. Complétude des lots ≥ 85 %
4. Rappel des consommables ≥ 80 %
5. Justesse de la mention ≥ 95 % — **sécurité**
6. Détection du hors périmètre ≥ 95 %
7. Prix ou référence inventés = **0** — **sécurité**, garanti structurellement
8. Latence d'un devis, 95ᵉ centile < 30 s

Le jeu de test compte 150 à 200 cas, **écrits et corrigés à la main**, jamais vus à
l'entraînement — c'est la seule mesure honnête. Il est réparti en cinq familles : nominal 40 %,
incomplet 20 %, limite 15 %, réglementé 15 %, hors périmètre 10 %. Et une règle intangible :
**le jeu de test ne rétrécit jamais.**

### Variables d'environnement

Le fichier `.env` existe à la racine et **est ignoré par git** — vérifié, il n'a jamais été
versionné. Il contient :

- `GLADIA_API_KEY` : **configurée** (transcription vocale distante)
- des variables Azure AI Foundry pour l'outillage de développement : **configurées**

Aucune valeur n'est reproduite ici, et le code applicatif ne lit aujourd'hui **aucune** de ces
variables — `app/` n'appelle jamais `os.getenv`. Seul `tools/notion_cli.py` lit `NOTION_TOKEN`,
qui n'est pas dans le fichier.

---

## 7. Commandes utiles

Le venv vit **hors du dépôt**, en `~/.venvs/the-project`, et il est géré par uv — donc `pip`
n'y est pas installé.

```bash
export VIRTUAL_ENV=~/.venvs/the-project     # à faire une fois par terminal

# Lancer les tests
uv run pytest
uv run pytest -v                            # détail test par test
uv run pytest tests/test_devis.py::test_acompte_30_pct   # un seul test

# Lancer l'application
uv run uvicorn app.main:app --reload
# puis http://localhost:8000  (et http://localhost:8000/docs pour l'API)

# Installer une dépendance
uv pip install <paquet>

# Vérifier qu'Ollama tourne et sert le bon modèle
curl -s http://localhost:11434/api/tags

# Essayer le moteur de devis sans passer par le modèle
uv run python -c "
from app.devis import Devis, ajouter_ligne
d = Devis()
ajouter_ligne(d, 'PEINT_FINITION', 'surface', 22.0)
print(d.total_ht, d.total_ttc, d.acompte_30_pct)
"

# Envoyer un message à l'API sans passer par l'interface
curl -s -X POST http://localhost:8000/api/message \
     -H 'Content-Type: application/json' \
     -d '{"texte":"je refais le salon, 22 m2 au sol, murs a repeindre"}'
```

**Il n'y a pas de linter et pas d'étape de build.** Ne pas en inventer.

**Une précaution particulière :** le dépôt est sur un montage OneDrive. Les commandes git y
expirent parfois, un fichier peut être vu comme vide au moment de l'indexation, et deux
processus git concurrents peuvent se bloquer. Si une commande git semble figée, c'est
généralement le montage, pas le dépôt.

---

## 8. Glossaire express

| Terme | En une ligne |
|---|---|
| **Lot** | Un poste de travaux : préparation, sous-couche, finition, pose |
| **`lot_code`** | L'identifiant d'un lot, ex. `PEINT_FINITION`. Liste fermée, le modèle ne peut pas en inventer |
| **Taux de chute** | La part de matériau perdue à la pose (coupes, casse) |
| **Rendement** | La matière nécessaire par unité, ex. 0,2 L de peinture par m² |
| **Contenance** | Ce que couvre une unité de vente : un seau de 10 L, un rouleau de 25 m² |
| **Mention** | Étiquette de domaine réglementé : aucun, simple, forte |
| **HITL** | *Human in the loop* — un point où le produit rend la main à l'humain |
| **Intent** | Le champ JSON par lequel le modèle dit ce qu'il fait ; le code route derrière |
| **Devis sans prix** | Le modèle sort structure et quantités ; le catalogue injecte les prix après |
| **Ventilation TVA** | Le détail de la TVA par taux, parce qu'un devis en mélange plusieurs |
| **Acompte** | 30 % du TTC, versés à la signature |
| **Décennale** | L'assurance obligatoire d'un artisan du bâtiment, dix ans |
| **SIRET** | Le numéro d'identification d'un établissement français |
| **Pappers** | L'API qui donne l'identité légale d'une entreprise depuis son SIRET |
| **293 B** | L'article du code général des impôts qui dispense de TVA les petites structures |
| **LoRA** | Affinage économique : on ajoute des paramètres au lieu de tout modifier |
| **MoE** | Mélange d'experts : le modèle n'active qu'une fraction de ses neurones |
| **Unsloth** | La bibliothèque d'affinage utilisée, optimisée pour LoRA |
| **gpt-oss** | La famille de modèles ouverts d'OpenAI, sous licence Apache 2.0 |
| **DGX Spark** | La machine cible : 128 Go unifiés, 273 Go/s de bande passante |
| **RGAA** | Le référentiel français d'accessibilité numérique |
| **RNCP** | Le répertoire des certifications professionnelles françaises |
| **C1 à C21** | Les 21 compétences du référentiel que le projet doit démontrer |

---

## 9. Comment m'utiliser

1. Copie **l'intégralité de ce document** dans une nouvelle conversation ChatGPT, ou dépose-le
   dans un **Project ChatGPT** pour qu'il serve de contexte permanent.
2. Passe en **mode vocal** et discute normalement : « explique-moi pourquoi le modèle ne
   calcule jamais », « qu'est-ce qui reste à faire avant la démo », « redis-moi comment
   marche le taux de chute ».
3. Si tu changes le code, **régénère ce document** plutôt que de le corriger à la main — il
   perd sa valeur dès qu'il ment sur un point.

---

*Document généré le 08/09/2026 à partir de l'état réel du dépôt : 20 tests exécutés et verts,
neuf modules Python lus intégralement, Ollama interrogé, moteur de devis exécuté sur un cas
réel. Commit courant : `a781711`.*
