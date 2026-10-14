# Assistant devis BTP vocal — projet de soutenance

Application B2B pour artisans du bâtiment : l'artisan dicte son chantier
(peinture, sols, plomberie, électricité), un modèle de langage (gpt-oss)
structure la demande, et un code déterministe restitue un devis exportable
**sans jamais inventer un prix**. Le modèle décrit, le code calcule.

Déploiement sur GCP (Cloud Run), modèle hébergé appelé par API. **Commencer par
[DOSSIER_SPRINT_1.md](DOSSIER_SPRINT_1.md)** : le dossier de conception V1.

## Où lire quoi

| Entrer par | Pour |
|---|---|
| [PLANNING.md](PLANNING.md) | Les quatre mois, jalon par jalon |
| [docs/produit/CADRAGE_MODELE.md](docs/produit/CADRAGE_MODELE.md) | **Le document de référence** — périmètre, dataset, protocole de preuve |
| [docs/produit/DISPOSITIF_AGENT.md](docs/produit/DISPOSITIF_AGENT.md) | Workflow, mémoire, garde-fous, plan d'évaluation |
| [DOSSIER_SPRINT_1.md](DOSSIER_SPRINT_1.md) | **Le dossier de conception V1** — besoin, périmètre, composante agentique, stack, schémas, contrat, plan |
| [docs/DECISIONS.md](docs/DECISIONS.md) | **Le journal des décisions** — pourquoi, et les questions encore ouvertes |
| [docs/produit/STORIES.md](docs/produit/STORIES.md) | Les stories et leur état constaté |
| [docs/pilotage/COUVERTURE_RNCP.md](docs/pilotage/COUVERTURE_RNCP.md) | Grille de contrôle : ce que le projet couvre, ce qu'il ne couvre pas |

## Arborescence

```
.
├── README.md                  ← vous êtes ici
├── CLAUDE.md                  consignes pour Claude Code
├── PLANNING.md                le calendrier des 4 mois
├── DOSSIER_SPRINT_1.md        le dossier de conception V1 — à lire d'abord
├── Dockerfile                 empaquetage du produit en image OCI
│
├── app/                       l'implémentation : API, moteur de devis, front
├── tests/                     la suite pytest
├── tools/                     outillage hors produit : chaînes de données et du modèle
├── mlops/                     la déclaration de la chaîne du modèle
├── dataset/                   exemples de référence et de contrôle de la validation
├── catalogue/                 sources, extraits bruts et jeu de données agrégé
│
├── docs/                      l'état courant de la conception — fait autorité
│   ├── DECISIONS.md           le journal des décisions (seul fichier d'histoire)
│   ├── produit/               cadrage, dispositif agent, stories, maquettes
│   ├── donnees/               chaîne de données, modèle de données, RGPD
│   ├── modele/                chaîne MLOps, benchmark STT, conclusion du POC
│   ├── exploitation/          CI/CD, incidents, accessibilité des documents
│   ├── pilotage/              rituels, tableau Notion, couverture RNCP
│   ├── notion/                schémas et CSV de la transposition Notion
│   └── sprint/                consignes et grilles des sprints de conception
├── veille/                    veille technique (thématique précédente rangée à part)
└── reference/                 référentiel de compétences, matière première
```

**Règle de rangement :** `docs/` décrit l'état **courant** et rien d'autre ;
l'histoire des choix vit dans **un seul fichier**, `docs/DECISIONS.md`. Un
document qui n'est plus la cible est supprimé (git garde l'historique), il ne
reste pas « au cas où ».

## Lancer l'application

L'environnement est géré par **uv**, le venv vit hors du dépôt
(`~/.venvs/the-project`) et `pip` n'y est pas installé.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run pytest                       # la suite de tests
VIRTUAL_ENV=~/.venvs/the-project uv run uvicorn app.main:app --reload
```

Sans installer Python ni uv, l'image fait la même chose et embarque la base
catalogue :

```bash
docker build -t assistant-devis-btp:local .
docker run --rm -p 8000:8000 -v btp-donnees:/donnees assistant-devis-btp:local
```

Puis ouvrir `http://localhost:8000`. L'application demande une **phrase de passe** :
si `BTP_MOT_DE_PASSE` n'est pas configurée, le serveur en tire une au hasard et
l'affiche sur sa console au démarrage.

Variables d'environnement, toutes facultatives :

| Variable | Effet | À défaut |
|---|---|---|
| `BTP_MOT_DE_PASSE` | Empreinte scrypt de la phrase de passe. Jamais la phrase en clair. | Une phrase est tirée au hasard et affichée sur la console |
| `BTP_CLE_SESSION` | Clé de signature des jetons de session | Tirée au hasard ; les jetons meurent au redémarrage |
| `BTP_DONNEES` | Racine des projets persistés | `donnees/` à la racine du dépôt |
| `BTP_SIGNAL_QUALITE` | Fichier du jeu de candidats d'entraînement (US-25) | `~/.local/share/the-project/signal_qualite.jsonl` |
| `BTP_CATALOGUE_BASE` | Base du jeu de données catalogue | `catalogue/catalogue.sqlite3` |
| `BTP_CATALOGUE_SOURCE` | Source des prix du devis : `base` pour la base catalogue, `simule` sinon | `simule` |

Pour produire une empreinte à coller dans l'environnement, sans jamais écrire la
phrase nulle part :

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run python -c \
  "from app.authentification import empreinte; import getpass; print(empreinte(getpass.getpass('Phrase : ')))"
```

### Reconstruire le jeu de données catalogue

La base du catalogue est un artefact **reconstructible**, donc absent du dépôt.
Tant qu'elle n'existe pas, les cinq routes `/api/catalogue/…` répondent un code
503 dont le message porte ces deux commandes :

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run python -m tools.donnees.agreger
VIRTUAL_ENV=~/.venvs/the-project uv run python -m tools.donnees.importer
```

Aucune des deux ne touche au réseau : elles repartent des extraits versionnés
dans `catalogue/brut/`. La collecte elle-même (`extraire_api.py`,
`extraire_scraping.py`) n'a besoin d'être relancée que pour rafraîchir ces
extraits. Tout est décrit dans `docs/donnees/CHAINE_DONNEES.md`.

**Attention au montage.** Ce dépôt est sur un montage OneDrive synchronisé : tout ce
qui y est écrit part en ligne. C'est pourquoi l'export du signal qualité refuse une
destination dans le dépôt et vise le disque local par défaut.

### Vérifier que tout marche vraiment

`pytest` remplace le modèle par une fausse fonction : c'est ce qu'il faut pour
tester le code, mais cela ne prouve rien sur la chaîne complète. Le parcours de
bout en bout, lui, ne neutralise rien — serveur réel, Ollama réel, `.docx` écrit
sur le disque :

```bash
export PHRASE="une-phrase-de-demonstration"
export BTP_MOT_DE_PASSE=$(VIRTUAL_ENV=~/.venvs/the-project uv run python -c \
  "from app.authentification import empreinte; import os; print(empreinte(os.environ['PHRASE']))")
VIRTUAL_ENV=~/.venvs/the-project uv run uvicorn app.main:app --port 8199 &
VIRTUAL_ENV=~/.venvs/the-project uv run python tools/parcours_bout_en_bout.py
```

Rejoué cinq fois de suite le 08/09/2026 : **24/24 à chaque exécution**, 21 appels à
`gpt-oss:20b`. Ce qu'on en a conclu — et le taux de JSON valide relevé, qui n'est pas
bon — est dans `docs/modele/CONCLUSION_POC.md`.

Vingt-quatre étapes : application fermée sans jeton, profil, relecture de dictée
(HITL-0), tour modèle, absence de prix avant validation (HITL-2), chiffrage,
export, recalcul de chaque ligne, contradiction entre deux dictées, forme des
mentions, injection, hors périmètre, escalade, métriques, fermeture. Sortie 0 si
tout passe.

`BTP_MOT_DE_PASSE` porte l'**empreinte** de la phrase, jamais la phrase :
l'exporter en clair ferait échouer l'authentification sans dire pourquoi.

### La chaîne du modèle

Elle existe **avant** l'entraînement, volontairement : écrite après, elle ne
pourrait plus porter la trace de l'entraînement, seulement le récit qu'on en fait.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run python -m tools.mlops.executer
```

Quatre étapes déclarées dans `mlops/pipeline.toml` — test des données,
préparation, entraînement, validation — et **trois** états possibles : `réussi`,
`échoué`, ou `ignoré` faute de prérequis. Aujourd'hui, le dataset restant à
écrire à la main, seule la première tourne ; les trois autres se déclarent
`ignoré` en nommant ce qui leur manque, jamais `réussi`. Tout est dans
`docs/modele/CHAINE_MLOPS.md`.

## État d'avancement

Le cadrage est figé et **l'implémentation est engagée** : FastAPI, moteur de devis
déterministe, front mono-fichier, suite de tests. `docs/produit/STORIES.md` porte l'état
constaté story par story — c'est lui qui fait foi, pas cette section.

Les décisions actées :

- Chantier pilote **quatre corps de métier** : peinture, sols, plomberie, électricité
- Entrée du produit **la voix**, canal de démonstration **web uniquement**
- Preuve : **20b brut bien promptté vs 20b fine-tuné** — le 120b est suspendu
- Frontière **modèle / code** stricte : aucun montant n'est produit par le modèle
