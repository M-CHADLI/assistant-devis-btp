# Tableau Notion — organisation agile du projet

> Ce document est la **transposition prête à poser** de l'organisation de projet sur Notion,
> dans un thème JIRA : épiques, stories, sprints, tâches, tableau kanban.
>
> **La source de vérité reste le dépôt.** `docs/STORIES.md` porte le découpage, `PLANNING.md`
> porte le calendrier. Notion en est la vue de pilotage — jamais l'inverse. Quand les deux
> divergent, c'est le dépôt qui a raison et Notion qu'on corrige.
>
> Sert la compétence **C16** (coordination agile : cycles, rôles, rituels, outils de pilotage
> accessibles à tout moment).

## Ce que ce dossier contient

| Fichier | Rôle |
|---|---|
| `docs/notion/stories.csv` | Les 26 stories, avec épique, file, rang, sprint, points, compétences |
| `docs/notion/sprints.csv` | Les 7 sprints de deux semaines, alignés sur les jalons de `PLANNING.md` |
| `docs/notion/taches.csv` | La décomposition technique des sprints S1 et S2 (22 tâches) |
| `docs/notion/schema-*.json` | Le schéma de chaque base : nom et type de chaque propriété |
| `tools/notion_cli.py` | Le CLI qui crée les bases et importe les CSV, sans passer par MCP |

## Pourquoi un CLI plutôt que le connecteur MCP

Le connecteur Notion expose **42 outils, soit 90 k jetons** chargés à chaque session — 45 % de
la fenêtre de contexte pour une tâche qui n'en utilise que six. Claude Code n'offre pas de
liste blanche par outil : `disabledMcpServers` est tout ou rien, et une règle de permission
`deny` empêche l'appel sans retirer la définition du contexte. Le mécanisme prévu pour ça
(*tool search*) est désactivé par la configuration locale, qui pointe `ANTHROPIC_BASE_URL` sur
un proxy en `127.0.0.1:4000`.

Le CLI coûte **zéro jeton de contexte** et fait exactement les six appels nécessaires.

## Arborescence à créer dans Notion

```
📁 Assistant BTP vocal — Projet             (page racine existante)
   ├── 🎯 Vue d'ensemble                     (page : objectif, jalons, définition de fini)
   ├── 🗂️ Backlog — Stories                  (base, 26 lignes)
   ├── 🏃 Sprints                            (base, 7 lignes)
   ├── ✅ Tâches                             (base, 22 lignes)
   └── 📈 Rituels                            (page : cadence, rôles, comptes rendus)
```

## Procédure — trois commandes

Prérequis : une **intégration interne** Notion (Paramètres → Connexions → Développer), partagée
avec la page racine du projet.

```bash
export NOTION_TOKEN=ntn_xxx
python tools/notion_cli.py whoami                    # vérifie le jeton
python tools/notion_cli.py search "Projet" --type page   # récupère l'identifiant de la page racine
```

Puis, pour chacune des trois bases :

```bash
python tools/notion_cli.py db-create --parent <page_id> --schema docs/notion/schema-stories.json
python tools/notion_cli.py import --db <db_id> --csv docs/notion/stories.csv \
                                  --schema docs/notion/schema-stories.json
```

`--simulation` sur `import` affiche ce qui serait écrit sans rien écrire. Les trois CSV ont été
vérifiés contre leur schéma : aucune colonne orpheline, aucune propriété sans colonne.

**Variante sans CLI** : Notion importe nativement un CSV (`···` → *Merge with CSV* / *Import*).
Les propriétés arrivent alors toutes en texte ; il faut les retyper à la main selon les
`schema-*.json`. Plus rapide à lancer, plus long à finir.

## Ce que l'API ne sait pas faire

**L'API publique Notion ne crée pas de vues.** Kanban, regroupements, filtres, calendrier,
graphiques : tout cela se fait à la main dans l'interface, une fois les bases peuplées. Compter
dix minutes. Voici les vues à créer, dans cet ordre :

| Base | Vue | Réglage |
|---|---|---|
| Backlog — Stories | **Tableau kanban** | Regrouper par `État` · filtrer `Sprint = S1` · trier par `Rang` |
| Backlog — Stories | **Backlog** (table) | Regrouper par `Épique` · trier par `File` puis `Rang` |
| Backlog — Stories | **Par compétence** (table) | Regrouper par `Compétences` — c'est la vue que le jury lit |
| Backlog — Stories | **Reste à faire** (table) | Filtrer `État ≠ Terminé` · somme de `Points` en pied de colonne |
| Sprints | **Chronologie** | Timeline sur `Début` → `Fin` |
| Tâches | **Kanban du sprint** | Regrouper par `État` · filtrer `Sprint = S1` |
| Tâches | **Par story** | Regrouper par `Story` |

Le **burndown** n'existe pas nativement dans Notion. Deux options honnêtes : une vue *Reste à
faire* avec la somme des points en pied de colonne (suffisant, et vrai), ou un relevé
hebdomadaire des points restants dans une petite base `Burndown` à deux colonnes (date, points
restants) — à ne créer que si le graphique est réellement demandé.

## Relations à poser après import

L'import CSV écrit `Story` et `Sprint` comme du texte. Pour obtenir de vraies liaisons JIRA :

1. Dans **Tâches**, ajouter une propriété `Relation` → *Backlog — Stories*, puis reporter les
   clés depuis la colonne texte `Story`. 22 lignes, cinq minutes.
2. Dans **Backlog — Stories**, ajouter une propriété `Relation` → *Sprints*, même principe.
3. Dans **Sprints**, ajouter un `Rollup` sur la relation Stories → somme de `Points`. C'est la
   vélocité par sprint, calculée et non déclarée.

## Contenu des deux pages de texte

### Page « Vue d'ensemble »

À reprendre tel quel :

- **Objectif produit** — un artisan décrit son chantier à la voix, obtient un devis BTP conforme
  et chiffré, qu'il valide et corrige. Le modèle décrit, le code calcule.
- **Jalons** — les quatre lignes du tableau de `PLANNING.md` (août référentiel, septembre dataset,
  octobre preuve, novembre démo).
- **Métrique nº 1** — taux de JSON valide ≥ 98 %, contre ~70 % en baseline. C'est elle qui porte
  la démonstration de l'apport du fine-tuning.
- **Définition de fini** — une story n'est finie que si : les critères fonctionnels **et** les
  critères d'accessibilité sont satisfaits, un test automatisé couvre le comportement, la ligne
  Traçabilité de `docs/STORIES.md` est mise à jour avec l'état de code **constaté**.
- **Les quatre exigences d'accessibilité transverses** (contraste ≥ 4,5:1 · clavier avec focus
  visible · jamais la couleur seule · cible ≥ 44 px), reprises du préambule de `docs/STORIES.md`.

### Page « Rituels »

- **Cadence** — sprints de deux semaines, du mardi au lundi, alignés sur les jalons mensuels.
- **Revue de sprint** — dernier jour : ce qui est démontrable est démontré, pas raconté.
- **Rétrospective** — trois questions, dix minutes, une action inscrite au sprint suivant.
- **Veille** — une heure le vendredi, thématique *Unsloth et fine-tuning MoE*, compte rendu dans
  `veille/seances/` au format `GABARIT-SEANCE.md` (compétence **C6**). C'est un rituel, pas une
  story : il ne rentre pas au backlog.
- **Rôles** — porteur de produit, développeur et recetteur sont la même personne. L'écrire est
  plus honnête que d'inventer une équipe ; ce qui compte pour C16, c'est que les cycles, les
  artefacts et les outils de pilotage existent et soient accessibles à tout moment.

## État de l'organisation au 08/09/2026

| | |
|---|---|
| Stories | 26, réparties sur 7 épiques |
| Terminées | 20 · en cours 3 · à faire 3 |
| Sprints clos | S1 à S4, **clos par anticipation** le 08/09 |
| Sprints ouverts | S5 et S6, entamés en avance sur le calendrier |
| Points restants au total | 29 sur 122 |
| Tâches décomposées | 53, dont 46 terminées |

L'avance sur le calendrier de `PLANNING.md` est réelle, pas déclarative : l'état de chaque story
est repris de sa ligne de traçabilité dans `docs/STORIES.md`, qui dit l'état du code **constaté**,
et les CSV de `docs/notion/` sont régénérés depuis ce fichier plutôt que tenus à la main. Les
dates de sprint, elles, n'ont pas été retouchées : un sprint clos avant sa date de fin se lit
mieux qu'un calendrier réécrit après coup.

S7 porte encore des stories sans tâches : le décomposer maintenant serait de la planification
fictive, révisée avant d'être exécutée.
