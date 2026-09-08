# Chaîne de données du catalogue

> Ce document décrit la chaîne qui va de trois sources hétérogènes à une base
> interrogeable. Il dit aussi ce que la chaîne **ne fait pas** et ce qu'elle
> laisse manquant : un jeu de données dont on ignore les trous n'est pas
> exploitable, il est seulement présentable.

Le catalogue de démonstration vivait dans un dictionnaire Python de douze
entrées (`app/catalogue.py`). C'est tenable pour faire tourner un devis, mais
cela ne produit aucune preuve : ni collecte, ni nettoyage, ni requête, ni
contrainte d'intégrité. Cette chaîne comble ce manque avec trois types de
sources réellement différents, et une seule destination.

## 1. Ce que la chaîne produit

Un jeu de données unique, `catalogue/jeu_de_donnees.json`, et sa projection en
base : `catalogue/catalogue.sqlite3`. Chaque produit y porte son prix, son
conditionnement, la matière dont il est fait, son facteur d'émission de CO2
(dioxyde de carbone) et sa masse volumique — quand ces deux dernières valeurs
existent.

État constaté au 8 septembre 2026 :

| Grandeur | Valeur |
| --- | --- |
| Lignes brutes collectées | 539 |
| Produits retenus après nettoyage | 104 |
| Familles de produits | 14 |
| Facteurs d'émission normalisés | 41 |
| Masses volumiques normalisées | 104 |
| Produits sans facteur d'émission | 8 |
| Produits sans masse volumique | 19 |

Les deux dernières lignes ne sont pas des défauts à corriger avant la
soutenance : ce sont des manques réels de sources publiques, déclarés comme
tels. La section 5 explique pourquoi les combler serait pire que les afficher.

## 2. Les trois sources

Le référentiel attend des types de sources variés. Ils ont été choisis pour
leur différence de nature, pas pour faire nombre : un fichier plat sale, une
interface de programmation applicative (API) publique paginée, et une page web
à analyser.

| Rôle | Source | Licence | Ce qu'elle apporte |
| --- | --- | --- | --- |
| Fichier | Export fournisseur simulé, format CSV (valeurs séparées par des virgules) | Données simulées, structure d'un export réel | Le produit vendable : référence, prix, conditionnement |
| API REST | Base Carbone de l'ADEME (Agence de la transition écologique) | Licence Ouverte (Etalab) | Le facteur d'émission par kilogramme de matière |
| Analyse de page web | Article « Masse volumique » de Wikipédia en français | CC BY-SA 4.0 (Creative Commons attribution, partage dans les mêmes conditions) | La masse volumique, qui relie les deux précédentes |

La troisième source n'est pas décorative. L'ADEME publie ses facteurs **par
kilogramme** ; l'export fournisseur vend **au litre, au mètre carré ou au mètre
linéaire**. Sans masse volumique, les deux sources ne peuvent pas se joindre.

Le fichier fournisseur est simulé, et c'est un choix assumé : les catalogues
des enseignes de bricolage sont protégés, et `docs/SOURCES_DONNEES.md` porte
déjà la contrainte légale. La **structure** est celle d'un export réel — mêmes
colonnes, mêmes défauts — seules les valeurs sont fabriquées.

## 3. Les six étapes

Chaque étape est un module de `tools/donnees/`, exécutable seul. La flèche se
lit « produit ».

```text
simuler_dump.py       →  catalogue/sources/export_fournisseur_simule.csv
extraire_fichier.py   →  catalogue/brut/fichier_export_fournisseur.json
extraire_api.py       →  catalogue/brut/api_ademe_base_carbone.json
extraire_scraping.py  →  catalogue/brut/scraping_masses_volumiques.json
                             │
agreger.py            ←──────┘
                      →  catalogue/jeu_de_donnees.json
importer.py           →  catalogue/catalogue.sqlite3
                             │
app/catalogue_base.py ←──────┘  le contrat de lecture, côté produit
app/main.py           →  cinq points de terminaison « Jeu de données »
```

Les trois extractions écrivent dans `catalogue/brut/`, et n'y écrivent **rien
sans provenance** : chaque fichier porte en en-tête sa source, sa licence, sa
date d'extraction et son nombre de lignes. L'écriture est atomique (fichier
temporaire puis remplacement), même parade que `app/persistance.py` contre une
interruption en cours d'écriture sur un dossier synchronisé.

Les extractions ne sont **pas** dans la suite de tests : un test qui dépend
d'un service distant échoue le jour où ce service tousse, et le rouge ne dit
alors rien du code. Leurs sorties, elles, sont versionnées — la chaîne est
donc rejouable hors ligne à partir de `agreger.py`.

Pour tout relancer :

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.agreger
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.importer
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.requetes
```

## 4. Le nettoyage, et ce qu'il jette

Le dump simulé porte des défauts volontaires, semés parce qu'un jeu propre ne
prouverait rien : le code de nettoyage n'aurait alors aucune occasion de
s'exercer.

| Défaut semé | Traitement |
| --- | --- |
| Prix écrit « 34,90 » ou « 34.90 € » | Ramené à un nombre |
| Prix vide, nul ou négatif | Ligne rejetée, motif compté |
| Référence vide | Ligne rejetée, motif compté |
| Référence en double | La date de mise à jour la plus récente gagne |
| Unité écrite « m2 », « M2 » ou « m² » | Ramenée à « m² » |
| Libellé tout en capitales | Ramené en casse de phrase |
| Date en deux formats | Ramenée au format ISO 8601 (AAAA-MM-JJ) |
| Produit en arrêt de commercialisation | Ligne rejetée, motif compté |

Bilan de l'exécution du 8 septembre 2026 :

| Motif de rejet | Lignes |
| --- | --- |
| Produit en arrêt de commercialisation | 28 |
| Prix absent ou illisible | 3 |
| Doublon de référence | 3 |
| Référence absente | 2 |
| Prix négatif ou nul | 1 |

Du côté de l'API, la recherche plein texte ramène large : 227 lignes ont été
écartées comme hors matériaux — agro-alimentaire surtout, mais aussi
traitement de déchets et réseaux de chaleur — et 7 pour unité non massique. Un
facteur exprimé en kilogrammes de CO2 par kilowattheure ne se convertit pas en
kilogrammes de CO2 par kilogramme : il ne parle pas de la même grandeur, et le
convertir de force fabriquerait un chiffre.

Quand la Base Carbone publie plusieurs valeurs pour un même matériau (procédés,
taux de recyclage, pays), la chaîne retient la **médiane** et publie l'étendue
avec elle. N'en garder qu'une seule aurait été un choix caché.

## 5. Le manque est une donnée

C'est le point le plus important du document.

La source de masses volumiques couvre les minéraux, les métaux, les plastiques
et les bois. Elle ne couvre **pas les peintures**. Dix-neuf produits n'ont donc
pas de masse volumique, et huit produits de carrelage n'ont pas de facteur
d'émission, la Base Carbone ne publiant les produits céramiques qu'en ratios
monétaires.

Deux réponses étaient possibles : inventer une valeur plausible, ou déclarer le
trou. La chaîne déclare le trou. Une densité de peinture interpolée serait
indiscernable d'une densité mesurée une fois dans la base, et se propagerait
dans tous les calculs en aval sans que rien ne signale son origine.

Le même raisonnement vaut pour les correspondances approximatives. Rapprocher
une peinture acrylique murale d'un « Vernis Acrylique » de la Base Carbone est
un **proxy**, pas une identité. Chaque famille porte donc une qualité de
correspondance, et une réserve écrite qui la motive :

| Qualité | Sens | Familles concernées |
| --- | --- | --- |
| exacte | La source nomme la même matière | 6 familles sur 14 |
| proxy | La source nomme la matière la plus proche disponible | 7 familles sur 14 |
| absente | La source ne couvre pas cette matière | 1 famille sur 14 |

La requête `familles_incompletes()` rend ce manque **interrogeable** : il peut
être demandé à la base, pas seulement lu dans un rapport d'exécution.

## 6. Le schéma de la base

Trois tables, une clé étrangère, une vue. La flèche se lit « référence ».

```text
source (role)          traçabilité : d'où vient chaque lot de données
famille (code)         matière, facteur d'émission, densité, qualité du lien
   ▲
   │ famille_code
produit (reference)    la ligne vendable : prix, unité, conditionnement
```

Le déterminant est la **famille**, pas la matière. Une table `matiere` aurait
paru plus élégante ; elle aurait été fausse. Le stratifié et le parquet sont
tous deux du bois, mais leurs masses volumiques diffèrent — panneau de fibres
contre chêne massif. Faire de la matière une entité aurait introduit une
dépendance fonctionnelle inexistante, et forcé à choisir arbitrairement l'une
des deux densités.

Les contraintes du schéma sont exécutoires, pas documentaires : clé étrangère
active, unité de vente restreinte à trois valeurs, prix strictement positif,
taux de promotion dans l'intervalle [0, 1[. Quatre tests les éprouvent sur une
connexion en écriture.

Le prix remisé est une **vue**, pas une colonne. Une remise change tous les
jours ; une colonne dérivée se désynchronise dès la première mise à jour
partielle.

L'import est idempotent : la base est reconstruite depuis zéro à chaque
exécution. Le jeu de données agrégé fait foi, la base n'en est qu'une
projection — et l'application l'ouvre en lecture seule pour que cette règle
tienne à l'exécution.

## 7. Les requêtes

L'application ne parle pas SQL (langage de requête structuré) : elle appelle
les fonctions de `app/catalogue_base.py`, qui portent chacune une requête
commentée. Le jour où la base passe de SQLite à PostgreSQL, c'est ce fichier
qui change, et lui seul.

Ce module est dans `app/` et non dans `tools/donnees/`, alors qu'il termine la
chaîne. La raison tient en une phrase : `tools/` est de l'outillage hors
produit, et ceci est le produit qui lit sa base. La chaîne écrit,
l'application lit, la frontière passe là. `tools/donnees/requetes.py` en reste
le point d'entrée en ligne de commande, et n'en est qu'un appelant.

| Fonction | Ce qu'elle répond |
| --- | --- |
| `produits_de_famille` | Le rayon, du moins cher au plus cher |
| `moins_cher_de_famille` | Le choix par défaut quand l'artisan ne tranche pas |
| `produit` | Une référence précise |
| `synthese_par_famille` | Nombre de produits et fourchette de prix, par famille |
| `familles_incompletes` | Ce que l'enrichissement n'a pas su remplir, et pourquoi |
| `produits_en_promotion` | Les remises au-dessus d'un seuil |
| `tracabilite` | La provenance et la licence de chaque lot de données |

Le classement se fait sur le prix **remisé**, jamais sur le prix affiché : un
produit à 40 euros remisé de 30 % passe devant un produit à 32 euros sans
promotion, et c'est celui-là que l'artisan doit voir en premier.

### Mise à disposition par l'API

Cinq points de terminaison exposent le jeu, en lecture seule, derrière la même
authentification que le reste de l'application.

| Point de terminaison | Ce qu'il rend |
| --- | --- |
| `GET /api/catalogue/sources` | Provenance et licence de chaque lot de données |
| `GET /api/catalogue/familles` | Effectifs et fourchettes de prix, par famille |
| `GET /api/catalogue/familles/{code}/produits` | Le rayon d'une famille |
| `GET /api/catalogue/produits/{reference}` | Un produit précis |
| `GET /api/catalogue/manques` | Ce qui n'a pas pu être rempli, et pourquoi |

Une famille inconnue donne un code 404 et non une liste vide : le client doit
pouvoir distinguer « cette famille n'existe pas » de « elle est vide », sans
quoi une faute de frappe passe inaperçue.

La base étant reconstructible, elle n'est pas versionnée. Sur un dépôt
fraîchement cloné, ces cinq routes répondent donc un code 503 dont le message
porte les deux commandes à lancer. C'est un état prévu, testé, et préférable à
une base versionnée qui divergerait en silence de son jeu de données source.

Aucune requête n'est construite par concaténation. Les valeurs passent par des
paramètres liés, seule parade sûre à l'injection SQL — et la précaution n'est
pas théorique ici : le code de lot peut venir d'un modèle de langage, donc
d'une source qui n'a aucune notion de ce qu'est une chaîne dangereuse. Un test
le vérifie en passant une référence hostile.

## 8. Ce que la chaîne ne fait pas

Trois limites, énoncées pour qu'elles ne soient pas prises pour des oublis.

**Elle n'alimente pas encore le moteur de devis.** `app/catalogue.py` garde ses
douze produits de démonstration, choisis pour correspondre aux lots du
référentiel métier. Les familles du dump simulé ne portent pas les mêmes codes.
Brancher l'un sur l'autre demande une table de correspondance entre lots et
familles, qui est une décision de conception, pas une opération de plomberie.
La couture est nette : `resoudre_produit()` est le seul point d'entrée à
réécrire, et `moins_cher_de_famille()` est la requête qui le remplacera. Le jeu
est en revanche mis à disposition d'un tiers par l'API, ce qui est exactement
ce à quoi un jeu de données sert.

**Elle ne calcule pas d'empreinte carbone.** Les facteurs d'émission sont
collectés et joints parce que c'est la seule manière de rendre la chaîne
honnête sur ses unités, pas parce que le produit afficherait un bilan carbone —
cette fonction n'est pas au périmètre défini dans `CLAUDE.md`. Extraire n'est
pas livrer.

**Elle ne traite pas de données à caractère personnel.** Le catalogue ne
contient que des produits. Les données personnelles du projet sont ailleurs,
dans le registre de traitements, et suivent leur propre régime.

## Sources

- [Base Carbone de l'ADEME, jeu de données ouvert](https://data.ademe.fr/datasets/base-carbone), sous Licence Ouverte (Etalab), consultée le 8 septembre 2026.
- [Article « Masse volumique » de Wikipédia en français](https://fr.wikipedia.org/wiki/Masse_volumique), sous licence CC BY-SA 4.0, par les contributeurs de Wikipédia, consulté le 8 septembre 2026.
