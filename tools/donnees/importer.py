"""Étape 5 — import : du jeu agrégé vers une base SQLite interrogeable.

Le catalogue vivait jusqu'ici dans un dictionnaire Python (`app/catalogue.py`).
C'est tenable pour douze produits, pas pour un catalogue fournisseur : il n'y a
ni requête, ni jointure, ni contrainte d'intégrité, et rien ne dit ce qui
manque. Cette étape le porte en base.

**Le schéma est en troisième forme normale, et son déterminant est la
famille — pas la matière.** La tentation serait une table `matiere` : elle
serait fausse. Le stratifié et le parquet sont tous deux du bois, mais leurs
masses volumiques diffèrent (panneau de fibres contre chêne massif). Ce qui
détermine la matière, le facteur d'émission et la densité, c'est la **famille
de produit** ; la matière n'est qu'un attribut de plus. Une table `matiere`
aurait introduit une dépendance fonctionnelle inexistante et forcé à choisir
arbitrairement l'une des deux densités.

Trois tables, une seule clé étrangère :

```text
source (role)          traçabilité : d'où vient chaque lot de données
famille (code)         matière, facteur d'émission, densité, qualité du lien
   ▲
   │ famille_code
produit (reference)    la ligne vendable : prix, unité, conditionnement
```

L'import est **idempotent** : la base est reconstruite depuis zéro à chaque
exécution. Le jeu de données agrégé fait foi ; la base n'est qu'une projection.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.importer
```
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SOURCE = Path("catalogue/jeu_de_donnees.json")
BASE = Path("catalogue/catalogue.sqlite3")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE source (
    role           TEXT PRIMARY KEY,   -- fichier | api_rest | scraping
    nom            TEXT NOT NULL,
    licence        TEXT NOT NULL,
    lignes_brutes  INTEGER NOT NULL
);

CREATE TABLE famille (
    code                    TEXT PRIMARY KEY,
    matiere                 TEXT NOT NULL,
    qualite_correspondance  TEXT NOT NULL
        CHECK (qualite_correspondance IN ('exacte', 'proxy', 'absente')),
    reserve                 TEXT,
    -- NULL assumé : la source ne couvre pas cette matière. Voir `reserve`.
    facteur_kgco2e_par_kg   REAL CHECK (facteur_kgco2e_par_kg > 0),
    facteur_min             REAL,
    facteur_max             REAL,
    masse_volumique_kg_m3   REAL CHECK (masse_volumique_kg_m3 > 0),
    source_facteur          TEXT,
    source_densite          TEXT
);

CREATE TABLE produit (
    reference         TEXT PRIMARY KEY,
    libelle           TEXT NOT NULL,
    famille_code      TEXT NOT NULL REFERENCES famille(code),
    marque            TEXT NOT NULL,
    unite_vente       TEXT NOT NULL CHECK (unite_vente IN ('m²', 'ml', 'u')),
    contenance        REAL CHECK (contenance IS NULL OR contenance > 0),
    contenance_unite  TEXT,
    prix_ht           REAL NOT NULL CHECK (prix_ht > 0),
    taux_promo        REAL NOT NULL CHECK (taux_promo >= 0 AND taux_promo < 1),
    ean               TEXT,
    date_maj          TEXT NOT NULL
);

-- Les deux accès du produit : « tous les produits de cette famille » (choix
-- d'un matériau pour un lot) et « ce produit-là » (résolution d'une référence).
CREATE INDEX idx_produit_famille ON produit(famille_code);
CREATE INDEX idx_produit_prix ON produit(famille_code, prix_ht);

-- Le prix effectivement payé, promotion déduite. Calculé ici plutôt que
-- stocké : une remise change tous les jours, une colonne dérivée se
-- désynchronise dès la première mise à jour partielle.
CREATE VIEW produit_tarife AS
SELECT p.*, ROUND(p.prix_ht * (1 - p.taux_promo), 2) AS prix_remise_ht,
       f.matiere, f.qualite_correspondance,
       f.facteur_kgco2e_par_kg, f.masse_volumique_kg_m3
FROM produit p JOIN famille f ON f.code = p.famille_code;
"""


def construire(jeu: dict, chemin: Path) -> sqlite3.Connection:
    """Reconstruit la base à partir du jeu agrégé. L'ancienne est écrasée."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.unlink(missing_ok=True)
    connexion = sqlite3.connect(chemin)
    connexion.executescript(SCHEMA)

    connexion.executemany(
        "INSERT INTO source VALUES (:role, :source, :licence, :lignes_brutes)",
        jeu["sources"])

    # Les attributs de famille sont répétés sur chaque produit dans le jeu
    # agrégé (format plat, lisible). La base les dénoue : une ligne par famille.
    familles: dict[str, dict] = {}
    for produit in jeu["produits"]:
        etendue = produit["facteur_etendue"] or [None, None]
        familles.setdefault(produit["famille"], {
            "code": produit["famille"],
            "matiere": produit["matiere"],
            "qualite": produit["qualite_correspondance"],
            "reserve": produit["reserve_correspondance"],
            "facteur": produit["facteur_kgco2e_par_kg"],
            "fmin": etendue[0], "fmax": etendue[1],
            "densite": produit["masse_volumique_kg_m3"],
            "src_f": produit["source_facteur"], "src_d": produit["source_densite"],
        })
    connexion.executemany(
        "INSERT INTO famille VALUES (:code, :matiere, :qualite, :reserve,"
        " :facteur, :fmin, :fmax, :densite, :src_f, :src_d)", familles.values())

    connexion.executemany(
        "INSERT INTO produit VALUES (:reference, :libelle, :famille, :marque,"
        " :unite_vente, :contenance, :contenance_unite, :prix_ht, :taux_promo,"
        " :ean, :date_maj)",
        [{k: p[k] for k in ("reference", "libelle", "famille", "marque",
                            "unite_vente", "contenance", "contenance_unite",
                            "prix_ht", "taux_promo", "ean", "date_maj")}
         for p in jeu["produits"]])
    connexion.commit()
    return connexion


def main() -> int:
    if not SOURCE.exists():
        print(f"{SOURCE} absent : lancer d'abord tools.donnees.agreger",
              file=sys.stderr)
        return 1
    jeu = json.loads(SOURCE.read_text(encoding="utf-8"))
    connexion = construire(jeu, BASE)
    for table in ("source", "famille", "produit"):
        nombre = connexion.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"{table} : {nombre} lignes")
    print(f"base écrite : {BASE} ({BASE.stat().st_size // 1024} Ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
