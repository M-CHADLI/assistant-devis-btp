# Chaîne de livraison continue

> Ce document couvre l'empaquetage du produit, la chaîne qui l'éprouve et le
> publie, et la façon de la reproduire localement. Il répond aux critères C19
> du référentiel et prolonge `docs/INTEGRATION_CONTINUE.md`, qui couvre C18.
>
> **Structure du document.** Titres hiérarchisés sans saut de niveau, tableaux
> avec ligne d'en-tête, liens explicites, aucune information portée par la
> seule couleur ou la seule mise en forme — conformément à
> `docs/ACCESSIBILITE_DOCUMENTS.md`.

## Ce que la livraison ajoute à l'intégration

L'intégration continue répond à « le code est-il juste ? ». La livraison
continue répond à une question différente : « quelqu'un d'autre peut-il faire
tourner ce produit ? ». Un dépôt peut être vert de bout en bout et rester
inlivrable — dépendance système implicite, version de Python que seule la
machine de l'auteur possède, base de données qu'il faut construire à la main en
connaissant la commande.

C'est exactement le risque de ce projet. L'environnement local est un venv hors
dépôt (`~/.venvs/the-project`) sans `pip`, sur Python 3.14, avec une base
SQLite reconstruite par deux commandes que rien n'oblige à lancer. La chaîne
décrite ici transforme cet enchaînement de gestes en un artefact qui démarre.

## L'artefact : une image OCI

`Dockerfile`, deux étapes.

| Étape | Ce qu'elle fait | Pourquoi séparée |
|---|---|---|
| `constructeur` | Installe les dépendances avec uv depuis `uv.lock`, puis construit la base catalogue | uv, les caches de compilation et les sources de construction n'ont rien à faire dans l'image finale. |
| `execution` | Copie l'environnement et le code, crée un utilisateur non privilégié, expose 8000 | Ce qui tourne en production ne contient que ce qui sert à tourner. |

### Quatre décisions, et leur motif

**Les dépendances sont figées.** `uv sync --frozen` : `uv.lock` fait autorité.
Sans ce drapeau, uv résoudrait les versions au moment de la construction, et
deux images du même commit pourraient différer. Une image non reproductible ne
prouve rien de ce qu'elle contient.

**La base catalogue est construite dans l'image, pas au démarrage.** L'étape
`constructeur` lance `python -m tools.donnees.importer`, qui ne lit que
`catalogue/jeu_de_donnees.json` — versionné. Aucune collecte n'est refaite :
ni l'API ADEME, ni le scraping Wikipédia. Deux raisons. D'abord la
reproductibilité — une construction qui dépend de la disponibilité de deux
services tiers échoue un jour sans que le code ait changé. Ensuite le
démarrage : un conteneur qui démarre ne doit pas dépendre d'une étape qui peut
échouer. Si la base manquait, l'API répondrait 503 sur tout le catalogue.

**Le conteneur ne tourne pas en root.** `USER artisan` (UID 10001). Un
conteneur root donne le root de l'hôte à qui s'en échappe. Le répertoire de
données `/donnees` lui appartient, et rien d'autre n'est inscriptible.

**Le modèle n'est pas dans l'image.** L'assistant appelle un LLM qui tourne
ailleurs, joint par `BTP_LLM_URL`. Embarquer 65 Go de poids dans une image de
démonstration n'aurait aucun sens, et l'application démarre sans lui en le
signalant — c'est le cas dégradé de la story US-26.

### Ce que l'image n'emporte pas

`.dockerignore` exclut d'abord ce qui ne doit **jamais** être publié : le
répertoire `donnees/` (coordonnées et devis clients), les fichiers `.env`,
l'historique `.git/`. Une couche d'image garde ce qu'on y a mis même après
suppression dans une couche suivante : la seule protection est de ne pas l'y
faire entrer. Il exclut ensuite ce qui est inutile à l'exécution — `docs/`,
`tests/`, `archive/`, `veille/`, et les artefacts reconstruits.

## Les déclencheurs

| Déclencheur | Ce qui s'exécute | Pourquoi |
|---|---|---|
| `push` sur `main` | Empaquetage, épreuve, publication | La branche de référence doit toujours être livrable, pas seulement verte. |
| `pull_request` visant `main` | Empaquetage et épreuve seulement | On éprouve une proposition ; on ne la publie pas. |
| Tag `v*` | Empaquetage, épreuve, publication étiquetée par version | C'est le geste de version explicite. |
| Lancement manuel | Empaquetage et épreuve | Pour vérifier après une modification du `Dockerfile`. |

## Les étapes, dans l'ordre

`.github/workflows/livraison.yml`, deux tâches enchaînées.

### Tâche 1 — Empaquetage

1. **Construire l'image**, avec le cache GitHub Actions (`type=gha`) pour ne pas
   réinstaller les dépendances à chaque exécution.
2. **Éprouver le démarrage.** Le conteneur est lancé, et la chaîne attend que la
   sonde de santé passe au vert — pas un `sleep` arbitraire. Puis deux requêtes :
   la page d'accueil doit répondre **200**, et une route de catalogue doit
   répondre **401**. Cette seconde vérification est la plus importante des deux :
   si elle répondait 200, la chaîne publierait une image dont l'API est ouverte.
3. **Vérifier la base embarquée** en comptant les produits dans le conteneur.
   Une image qui démarre mais dont le catalogue est vide répondrait 503 à tout
   ce qui compte.
4. **Déposer l'image comme artefact** (`docker save`), consultable sept jours.
   C'est ce qui permet de récupérer exactement l'image éprouvée, sans la
   reconstruire.

### Tâche 2 — Publication

Elle porte `needs: empaquetage` : elle ne peut pas s'exécuter avant que l'image
ait démarré et répondu. Elle est de plus conditionnée à `push` — jamais sur une
pull request.

L'image part sur **GHCR** (`ghcr.io`), avec le jeton fourni par GitHub Actions :
aucun secret à créer, aucun registre tiers à administrer. Les étiquettes sont
calculées par `docker/metadata-action` : nom de branche, version sémantique sur
tag, et SHA long — ce dernier étant le seul identifiant qui désigne une image
sans ambiguïté.

## Reproduire la chaîne localement

Aucune de ces commandes n'a besoin du réseau, sauf la première fois pour
télécharger les images de base.

```bash
docker build -t assistant-devis-btp:local .

docker run --rm -p 8000:8000 -v btp-donnees:/donnees assistant-devis-btp:local
```

La phrase de passe de la session est affichée au démarrage dans les journaux du
conteneur : elle est tirée au hasard tant que `BTP_MOT_DE_PASSE` n'est pas
fourni, et elle change à chaque redémarrage. Pour la fixer, passer une empreinte
scrypt — jamais un mot de passe en clair :

```bash
docker run --rm -e BTP_MOT_DE_PASSE="$EMPREINTE" -p 8000:8000 assistant-devis-btp:local
```

| Variable | Rôle | Défaut dans l'image |
|---|---|---|
| `BTP_MOT_DE_PASSE` | Empreinte scrypt de la phrase de passe | Absente — une phrase est tirée au hasard et affichée |
| `BTP_CLE_SESSION` | Clé de signature des jetons | Absente — tirée au hasard, les jetons ne survivent pas au redémarrage |
| `BTP_DONNEES` | Répertoire des devis et du journal qualité | `/donnees`, monté en volume |
| `BTP_CATALOGUE_BASE` | Base SQLite du catalogue | `/app/catalogue/catalogue.sqlite3`, embarquée |

## Ce que cette chaîne ne fait pas

**Elle ne déploie rien.** Publier une image et la faire tourner quelque part
sont deux gestes ; le second suppose une cible d'hébergement que ce projet n'a
pas, et n'en aura pas : le produit s'exécute sur le poste de l'artisan ou sur la
DGX Spark, jamais chez un tiers, parce que les dictées et les coordonnées
clients ne sortent pas de la machine.

**Elle ne s'exécute nulle part aujourd'hui.** Aucun `remote` git n'est
configuré. Le fichier de chaîne est écrit, éprouvé dans ses parties
reproductibles en local — l'image est construite, elle démarre, elle répond —
mais GitHub Actions ne l'a jamais lancé. C'est le même constat que pour
l'intégration continue, et il tient à une seule cause, notée en tête de
`docs/AUDIT_JURY.md`.

**Elle ne signe pas l'image et ne produit pas de SBOM.** Ce sont des ajouts
d'une demi-heure (`cosign`, `docker/scout` ou `syft`) qui n'ont d'intérêt qu'une
fois la publication réellement en marche.
