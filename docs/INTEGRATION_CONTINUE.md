# Chaîne d'intégration continue

> Ce document couvre l'outil retenu, les déclencheurs, les étapes, et la façon
> de reproduire la chaîne localement. Il répond aux critères C18 du référentiel
> et sert d'appui à C12 (exécution des tests) et C19 (livraison).
>
> **Structure du document.** Titres hiérarchisés sans saut de niveau, tableaux
> avec ligne d'en-tête, liens explicites, aucune information portée par la
> seule couleur ou la seule mise en forme — conformément à
> `docs/ACCESSIBILITE_DOCUMENTS.md`.

## L'outil retenu, et pourquoi

**GitHub Actions**, fichier `.github/workflows/tests.yml`.

Trois raisons, dans l'ordre où elles ont pesé :

1. **Zéro infrastructure à tenir.** Le projet est mené par une personne seule
   sur quatre mois. Un Jenkins ou un GitLab Runner auto-hébergé demanderait une
   machine, des mises à jour et une surveillance — du temps pris au projet.
2. **Cohérence avec l'hébergement du dépôt.** Le référentiel exige un dépôt Git
   distant à neuf reprises ; dès lors que le dépôt vit sur GitHub, la chaîne
   qui y est déjà intégrée évite un service de plus.
3. **`astral-sh/setup-uv` est officiel.** La stack repose sur uv ; l'action est
   maintenue par Astral, avec cache du résolveur. Reproduire l'environnement
   local en intégration ne demande alors aucune traduction.

**Ce qui a été écarté.** GitLab CI : cohérent, mais imposerait de déplacer le
dépôt. Un `pre-commit` local : ce n'est pas de l'intégration continue, ça
n'exécute rien sur le serveur et rien ne prouve qu'un contributeur l'a installé.
Une chaîne auto-hébergée sur la DGX Spark : la machine sert au fine-tuning, on
ne lui ajoute pas un rôle de serveur d'intégration.

## Les déclencheurs

| Déclencheur | Portée | Pourquoi |
|---|---|---|
| `push` sur `main` | Toujours | La branche de référence ne doit jamais rester rouge sans qu'on le sache. |
| `push` sur `feat/**`, `fix/**`, `docs/**` | Branches de travail | Le retour arrive pendant le développement, pas à la fusion. |
| `pull_request` visant `main` | Toute proposition de fusion | C'est le point de contrôle avant intégration. |
| `workflow_dispatch` | Manuel | Relancer après une panne de service, ou vérifier une branche hors convention de nommage. |

Une règle de concurrence (`concurrency`) annule l'exécution précédente d'une
même branche quand un nouveau `push` arrive : deux exécutions sur un état
dépassé ne prouvent rien et consomment des minutes.

## Les étapes

La chaîne comporte un seul travail, `pytest`, sur `ubuntu-latest`, plafonné à
dix minutes. Six étapes.

| # | Étape | Ce qu'elle fait |
|---|---|---|
| 1 | Récupérer les sources | `actions/checkout@v4`. |
| 2 | Installer uv | `astral-sh/setup-uv@v5`, avec cache indexé sur `uv.lock`. |
| 3 | Installer Python et les dépendances | `uv sync --frozen --all-groups`. |
| 4 | Lancer la suite de tests | `uv run --frozen pytest -q`, avec `BTP_DONNEES` pointé sur un répertoire jetable. |
| 5 | Vérifier l'accessibilité des documents | `tools/verifier_accessibilite_docs.py` : règles 1, 2 et 4 de `docs/ACCESSIBILITE_DOCUMENTS.md`. |
| 6 | Vérifier la syntaxe du front | Extraction des blocs `<script>` de `app/static/index.html`, puis `node --check`. |

### Pourquoi `--frozen`

`uv sync --frozen` refuse de résoudre les dépendances : `uv.lock` fait foi. Si
le fichier a dérivé de `pyproject.toml`, la chaîne **échoue** au lieu de
résoudre en silence. C'est voulu — une intégration qui installe des versions que
personne n'a vues en local ne teste pas ce qui sera livré.

Vérification locale avant de pousser :

```bash
VIRTUAL_ENV=~/.venvs/the-project uv lock --check
```

### Pourquoi `BTP_DONNEES`

Le registre de projets écrit des fichiers JSON sur disque (`app/persistance.py`).
Sans cette variable il écrirait dans `donnees/` à la racine du dépôt. La pointer
sur un répertoire temporaire garantit qu'**aucun test n'écrit dans l'arbre
versionné** — et fait échouer la chaîne si un jour l'un d'eux essaie.

### Pourquoi un contrôle d'accessibilité documentaire

Le référentiel réclame un format accessible dans huit compétences, et à chaque
fois sur les **documents livrés**. Trois des neuf règles du projet se vérifient
sans jugement humain ; les laisser à la relecture, c'est les perdre au premier
document écrit dans l'urgence. L'étape les tient à ma place.

Le contrôle ignore les blocs de code : un commentaire `# Règle 1` dans un
exemple bash n'est pas un titre de niveau 1.

### Pourquoi une vérification du front

Le front est un fichier unique, sans build, sans transpilation : rien ne
relirait son JavaScript avant qu'un visiteur ne l'exécute. `node --check` sur
les blocs `<script>` extraits attrape les fautes de syntaxe pour un coût nul.
Ce n'est **pas** un linter — le projet n'en a pas et n'en veut pas.

## Reproduire la chaîne en local

Les six étapes, à la main, dans l'ordre :

```bash
VIRTUAL_ENV=~/.venvs/the-project uv lock --check          # étape 3, le garde-fou
BTP_DONNEES=/tmp/donnees \
  VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync pytest -q   # étape 4

python3 tools/verifier_accessibilite_docs.py              # étape 5

python3 - <<'PY' > /tmp/front.js                          # étape 6
import re, pathlib
html = pathlib.Path("app/static/index.html").read_text(encoding="utf-8")
print("\n".join(re.findall(r"<script>(.*?)</script>", html, re.S)))
PY
node --check /tmp/front.js
```

Sur cette machine, `node` n'est pas dans le `PATH` par défaut : il se trouve
dans `~/.nvm/versions/node/v22.22.2/bin/`.

## Ce que la chaîne ne fait pas encore

Écrit ici pour que ce soit su, pas découvert le jour de la soutenance.

- **Elle n'a jamais tourné.** Le dépôt n'a pas de remote (`git remote -v` est
  vide) : la configuration est versionnée et valide, aucune exécution ne l'a
  encore confirmée. C'est le premier geste à faire au retour.
- **Pas de mesure de couverture.** C12-92 la demande. `pytest-cov` la
  fournirait ; la dépendance n'est pas encore ajoutée.
- **Pas d'étape de packaging ni de livraison** — c'est C19, qui reste entier.
- **Pas de test du modèle.** La chaîne teste le code déterministe. Le jeu de
  test de 150-200 exemples (`docs/DISPOSITIF_AGENT.md` §4) s'écrit à la main et
  n'existe pas encore ; quand il existera, il aura sa propre étape.

## État constaté

Les six étapes ont été exécutées à la main sur cette machine le 08/09/2026 :
`uv lock --check` passe, la suite rend **62 tests verts**, le contrôle
d'accessibilité déclare **16 documents conformes**, et `node --check` accepte
les 206 lignes de JavaScript extraites du front.
