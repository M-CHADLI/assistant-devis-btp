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

## État d'avancement

Le cadrage est figé, **aucun code n'est écrit**. Les décisions actées :

- Chantier pilote **peinture et sols** (référentiel de 20-30 matériaux)
- Canal de démonstration **web uniquement**
- Preuve : **20b brut bien promptté vs 20b fine-tuné** — le 120b est la démo
- Frontière **modèle / code** stricte : aucun montant n'est produit par le modèle

Prochain jalon : le **référentiel métier** (août), chaque valeur sourcée.
