"""Le contrat de lecture du catalogue en base — une requête par question.

Ce module vit dans `app/` et non dans `tools/donnees/`, alors qu'il termine la
chaîne de données. La raison tient en une phrase : `tools/` est de l'outillage
hors produit, et **ceci est le produit qui lit sa base**. La chaîne écrit,
l'application lit ; la frontière passe ici. `tools/donnees/requetes.py` en
reste le point d'entrée en ligne de commande, et n'en est qu'un appelant.

Chaque fonction porte **une** requête SQL commentée. Le SQL n'est jamais
construit par concaténation : les valeurs passent par des paramètres liés
(`?`), seule parade sûre à l'injection, y compris ici où les entrées viennent
d'un modèle de langage — un `lot_code` halluciné reste une chaîne, jamais du
code.

Ces requêtes sont le **contrat de lecture** du catalogue. L'application ne
parle pas SQL : elle appelle ces fonctions. Le jour où la base passe de SQLite
à PostgreSQL, c'est ce fichier qui change, et lui seul.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.requetes
```
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Le chemin par défaut suit la chaîne de données ; la variable
# d'environnement existe pour les tests et pour un déploiement qui rangerait
# la base ailleurs.
BASE = Path(os.environ.get("BTP_CATALOGUE_BASE", "catalogue/catalogue.sqlite3"))


def ouvrir(chemin: Path | str | None = None) -> sqlite3.Connection:
    """Connexion en lecture, lignes renvoyées comme des dictionnaires.

    Le chemin par défaut est résolu **à l'appel**, pas dans la signature : une
    valeur par défaut est figée à l'import, et `BASE` cesserait alors d'être
    modifiable — ce qui casse aussi bien un test qu'un déploiement qui range
    la base ailleurs.
    """
    chemin = Path(BASE if chemin is None else chemin)
    if not chemin.exists():
        # La base est un artefact reconstructible, donc non versionné. Le
        # message porte la commande plutôt que de laisser deviner.
        raise FileNotFoundError(
            f"{chemin} absent — reconstruire la base : "
            "python -m tools.donnees.agreger puis python -m tools.donnees.importer")
    connexion = sqlite3.connect(f"file:{chemin}?mode=ro", uri=True)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA foreign_keys = ON")
    return connexion


def produits_de_famille(cx: sqlite3.Connection, famille: str) -> list[dict]:
    """Le rayon : tous les produits d'une famille, du moins cher au plus cher.

    Trié sur le prix **remisé**, pas sur le prix affiché : un produit à 40 €
    remisé de 30 % passe devant un produit à 32 € sans promotion, et c'est
    celui-là que l'artisan doit voir en premier.
    """
    return [dict(l) for l in cx.execute(
        "SELECT * FROM produit_tarife WHERE famille_code = ?"
        " ORDER BY prix_remise_ht ASC, reference ASC", (famille,))]


def moins_cher_de_famille(cx: sqlite3.Connection, famille: str) -> dict | None:
    """Le choix par défaut du moteur de devis quand l'artisan ne tranche pas."""
    ligne = cx.execute(
        "SELECT * FROM produit_tarife WHERE famille_code = ?"
        " ORDER BY prix_remise_ht ASC, reference ASC LIMIT 1", (famille,)).fetchone()
    return dict(ligne) if ligne else None


def produit(cx: sqlite3.Connection, reference: str) -> dict | None:
    """Résolution d'une référence précise. `None` si elle n'existe pas — le
    code appelant doit traiter ce cas, jamais l'ignorer."""
    ligne = cx.execute(
        "SELECT * FROM produit_tarife WHERE reference = ?", (reference,)).fetchone()
    return dict(ligne) if ligne else None


def synthese_par_famille(cx: sqlite3.Connection) -> list[dict]:
    """Une ligne par famille : combien de produits, quelle fourchette de prix.

    Agrégation avec jointure : elle sert au contrôle de complétude du catalogue
    (une famille à un seul produit ne permet aucun arbitrage) autant qu'à la
    vue d'ensemble.
    """
    return [dict(l) for l in cx.execute("""
        SELECT f.code, f.matiere, f.qualite_correspondance,
               count(p.reference)                       AS nombre_de_produits,
               ROUND(min(p.prix_ht * (1 - p.taux_promo)), 2) AS prix_min,
               ROUND(max(p.prix_ht * (1 - p.taux_promo)), 2) AS prix_max,
               ROUND(avg(p.prix_ht * (1 - p.taux_promo)), 2) AS prix_moyen
        FROM famille f
        LEFT JOIN produit p ON p.famille_code = f.code
        GROUP BY f.code
        ORDER BY f.code""")]


def familles_incompletes(cx: sqlite3.Connection) -> list[dict]:
    """Ce que l'enrichissement n'a pas su remplir, et pourquoi.

    Requête d'honnêteté : elle existe pour que le manque soit interrogeable au
    lieu d'être invisible. Une famille sans facteur d'émission ou sans masse
    volumique ne doit jamais être présentée comme documentée.
    """
    return [dict(l) for l in cx.execute("""
        SELECT code, matiere, qualite_correspondance, reserve,
               facteur_kgco2e_par_kg IS NULL AS facteur_manquant,
               masse_volumique_kg_m3 IS NULL AS densite_manquante
        FROM famille
        WHERE facteur_kgco2e_par_kg IS NULL
           OR masse_volumique_kg_m3 IS NULL
           OR qualite_correspondance <> 'exacte'
        ORDER BY code""")]


def produits_en_promotion(cx: sqlite3.Connection, seuil: float = 0.05) -> list[dict]:
    """Les remises au-dessus d'un seuil, remise la plus forte en tête."""
    return [dict(l) for l in cx.execute(
        "SELECT reference, libelle, famille_code, prix_ht, taux_promo,"
        " ROUND(prix_ht * (1 - taux_promo), 2) AS prix_remise_ht"
        " FROM produit WHERE taux_promo >= ?"
        " ORDER BY taux_promo DESC, reference ASC", (seuil,))]


def tracabilite(cx: sqlite3.Connection) -> list[dict]:
    """D'où viennent les données, sous quelle licence. Toujours affichable."""
    return [dict(l) for l in cx.execute("SELECT * FROM source ORDER BY role")]
