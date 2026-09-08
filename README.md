# Assistant Bricolage — projet de soutenance

Fine-tuning d'un modèle MoE local (gpt-oss) en expert du chantier peinture et
sols : il cadre un projet de travaux, calcule les quantités et restitue un devis
structuré **sans jamais inventer un prix**. Le modèle décrit, le code calcule.

Cible matérielle : NVIDIA DGX Spark, 128 Go de mémoire unifiée. Tout est local,
les données ne sortent pas de la machine.

## Où lire quoi

| Entrer par | Pour |
|---|---|
| [PLANNING.md](PLANNING.md) | Les quatre mois, jalon par jalon |
| [docs/CADRAGE_MODELE.md](docs/CADRAGE_MODELE.md) | **Le document de référence** — périmètre, dataset, protocole de preuve |
| [docs/DISPOSITIF_AGENT.md](docs/DISPOSITIF_AGENT.md) | Workflow, mémoire, garde-fous, plan d'évaluation |
| [docs/LIVRABLES.md](docs/LIVRABLES.md) | Grille de contrôle : ce que le projet couvre, ce qu'il ne couvre pas |
| [docs/NOTES.md](docs/NOTES.md) | Bloc-notes — idées attrapées au vol, pas encore arbitrées |
| [docs/SOURCES_DONNEES.md](docs/SOURCES_DONNEES.md) | Structure du dump catalogue et contrainte légale sur les données |

## Arborescence

```
.
├── README.md                  ← vous êtes ici
├── CLAUDE.md                  consignes pour Claude Code
├── PLANNING.md                le calendrier des 4 mois
│
├── docs/                      la conception du projet — fait autorité
├── veille/                    livrables de veille (thématique à recadrer)
├── reference/                 référentiel de compétences, matière première
└── archive/renoassistant/     conception précédente, valeur historique
```

**Règle de rangement :** `docs/` fait autorité, `archive/` ne fait plus autorité.
Un document qui n'est plus la cible descend dans `archive/`, il ne reste pas à la
racine « au cas où ».

## Lancer l'application

L'environnement est géré par **uv**, le venv vit hors du dépôt
(`~/.venvs/the-project`) et `pip` n'y est pas installé.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run pytest                       # la suite de tests
VIRTUAL_ENV=~/.venvs/the-project uv run uvicorn app.main:app --reload
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

Pour produire une empreinte à coller dans l'environnement, sans jamais écrire la
phrase nulle part :

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run python -c \
  "from app.authentification import empreinte; import getpass; print(empreinte(getpass.getpass('Phrase : ')))"
```

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

Vingt-deux étapes : application fermée sans jeton, profil, relecture de dictée
(HITL-0), tour modèle, absence de prix avant validation (HITL-2), chiffrage,
export, recalcul de chaque ligne, injection, hors périmètre, escalade, métriques,
fermeture. Sortie 0 si tout passe.

## État d'avancement

Le cadrage est figé et **l'implémentation est engagée** : FastAPI, moteur de devis
déterministe, front mono-fichier, suite de tests. `docs/STORIES.md` porte l'état
constaté story par story — c'est lui qui fait foi, pas cette section.

Les décisions actées :

- Chantier pilote **quatre corps de métier** : peinture, sols, plomberie, électricité
- Entrée du produit **la voix**, canal de démonstration **web uniquement**
- Preuve : **20b brut bien promptté vs 20b fine-tuné** — le 120b est la démo
- Frontière **modèle / code** stricte : aucun montant n'est produit par le modèle
