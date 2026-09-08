"""Fabrique le dump fournisseur **simulé** qui sert de source « fichier ».

Contrainte légale héritée de `docs/SOURCES_DONNEES.md` : un vrai export de
catalogue Leroy Merlin ne peut être ni redistribué ni versionné. La parade du
projet est constante depuis l'origine — **structure réelle, valeurs simulées**.

Ce script n'est donc pas une étape de la chaîne d'extraction : il fabrique la
matière que l'étape 1 lira. Le script d'extraction, lui, ne sait pas que le
fichier est simulé, et c'est le point : le jour où un vrai export arrive, il se
substitue au fichier sans qu'une ligne de `extraire_fichier.py` change.

**Les défauts sont volontaires.** Un dump réel arrive sale : doublons de
référence, prix au format français avec le symbole monétaire collé, unités
écrites de trois façons, lignes tronquées, dates à deux formats. Les semer ici
est la seule manière de prouver que `agreger.py` les traite — un jeu propre ne
prouverait rien.

Lancement :

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.simuler_dump
```
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

DESTINATION = Path("catalogue/sources/export_fournisseur_simule.csv")

# Les colonnes d'un export fournisseur tel qu'il se présente réellement : une
# ligne par référence vendable, la famille en texte libre, le conditionnement
# séparé de l'unité de vente.
COLONNES = ["reference", "libelle", "famille", "marque", "unite_vente",
            "contenance", "contenance_unite", "prix_ht", "taux_promo", "ean",
            "disponibilite", "date_maj"]

# Familles alignées sur les quatre corps de métier du périmètre pilote. Chaque
# entrée : (préfixe de référence, famille, gabarit de libellé, unité de vente,
# conditionnement, bornes de prix).
FAMILLES = [
    ("PE", "PEINTURE_PREPARATION", "Enduit de rebouchage {v} kg", "u", (1, 5), (5, 18)),
    ("PE", "PEINTURE_SOUS_COUCHE", "Sous-couche universelle {v} L", "u", (2.5, 10), (18, 55)),
    ("PE", "PEINTURE_FINITION", "Peinture acrylique mate {v} L", "u", (2.5, 10), (29, 95)),
    ("PE", "PEINTURE_FINITION", "Peinture glycéro satinée {v} L", "u", (2.5, 10), (39, 110)),
    ("SO", "SOL_PREPARATION", "Ragréage autolissant {v} kg", "u", (5, 25), (12, 34)),
    ("SO", "SOL_SOUS_COUCHE", "Film pare-vapeur {v} m2", "u", (10, 25), (9, 29)),
    ("SO", "SOL_STRATIFIE", "Stratifié pose flottante ép. {v} mm", "M2", None, (9, 39)),
    ("SO", "SOL_CARRELAGE", "Carrelage grès cérame {v} cm", "m²", None, (14, 59)),
    ("SO", "SOL_PARQUET", "Parquet contrecollé chêne {v} mm", "m2", None, (29, 89)),
    ("PL", "PLOMBERIE_ALIMENTATION", "Tube multicouche Ø{v} mm", "ml", None, (2, 9)),
    ("PL", "PLOMBERIE_EVACUATION", "Tube PVC évacuation Ø{v} mm", "ML", None, (3, 12)),
    ("PL", "PLOMBERIE_ROBINETTERIE", "Mitigeur {v}", "u", None, (39, 189)),
    ("EL", "ELECTRICITE_CABLE", "Câble rigide {v} mm2", "ml", None, (1, 6)),
    ("EL", "ELECTRICITE_APPAREILLAGE", "Prise {v}", "u", None, (4, 29)),
    ("EL", "ELECTRICITE_TABLEAU", "Disjoncteur {v} A", "u", None, (8, 34)),
]

VARIANTES = {
    "Mitigeur {v}": ["lavabo", "évier", "douche", "bain"],
    "Prise {v}": ["2P+T 16A", "RJ45 cat.6", "USB-C double", "étanche IP55"],
    "Carrelage grès cérame {v} cm": ["30x30", "45x45", "60x60", "80x80"],
    "Stratifié pose flottante ép. {v} mm": ["7", "8", "10", "12"],
    "Parquet contrecollé chêne {v} mm": ["10", "12", "14"],
    "Tube multicouche Ø{v} mm": ["16", "20", "26", "32"],
    "Tube PVC évacuation Ø{v} mm": ["32", "40", "50", "100"],
    "Câble rigide {v} mm2": ["1,5", "2,5", "6"],
    "Disjoncteur {v} A": ["10", "16", "20", "32"],
}

# Les marques suivent le corps de métier : une prise de marque de peinture
# trahirait tout de suite le caractère fabriqué du fichier.
MARQUES = {
    "PE": ["Dulux", "Tollens", "Zolpan", "Sikkens"],
    "SO": ["Weber", "Quick-Step", "Gerflor", "Tarkett"],
    "PL": ["Rehau", "Nicoll", "Grohe", "Hansgrohe"],
    "EL": ["Legrand", "Schneider", "Hager", "Nexans"],
}


def _libelle(gabarit: str, contenance: tuple[float, float] | None,
             alea: random.Random) -> tuple[str, str]:
    """Rend le libellé et la valeur variable qu'il porte."""
    if gabarit in VARIANTES:
        valeur = alea.choice(VARIANTES[gabarit])
        return gabarit.format(v=valeur), valeur
    bas, haut = contenance or (1, 1)
    valeur = alea.choice([bas, haut, (bas + haut) / 2])
    valeur = int(valeur) if float(valeur).is_integer() else valeur
    return gabarit.format(v=valeur), str(valeur)


def fabriquer(graine: int = 20260908) -> list[dict[str, str]]:
    """Le dump complet, défauts compris. Déterministe à graine égale."""
    alea = random.Random(graine)
    lignes: list[dict[str, str]] = []
    compteur: dict[str, int] = {}

    for prefixe, famille, gabarit, unite, contenance, (px_bas, px_haut) in FAMILLES:
        for _ in range(9):
            compteur[prefixe] = compteur.get(prefixe, 0) + 1
            libelle, valeur = _libelle(gabarit, contenance, alea)
            prix = round(alea.uniform(px_bas, px_haut), 2)
            promo = alea.choice([0, 0, 0, 5, 10, 15, 20])
            lignes.append({
                "reference": f"LM-{prefixe}-{compteur[prefixe]:03d}",
                "libelle": libelle,
                "famille": famille,
                "marque": alea.choice(MARQUES[prefixe]),
                "unite_vente": unite,
                "contenance": valeur if contenance else "",
                "contenance_unite": ("L" if "L" in gabarit else "kg" if "kg" in gabarit
                                     else "m²" if "m2" in gabarit else "") if contenance else "",
                "prix_ht": f"{prix:.2f}".replace(".", ","),
                "taux_promo": str(promo),
                "ean": str(alea.randrange(3_000_000_000_000, 3_999_999_999_999)),
                "disponibilite": alea.choice(["EN_STOCK", "EN_STOCK", "EN_STOCK",
                                              "SUR_COMMANDE", "ARRET"]),
                "date_maj": alea.choice(["2026-08-14", "14/08/2026", "2026-09-01"]),
            })

    # --- Les défauts, semés sciemment ---------------------------------------
    # Un dump réel n'est pas propre. Chaque défaut ci-dessous a sa règle de
    # nettoyage dans `agreger.py` et son test dans `tests/test_chaine_donnees.py`.
    doublons = [dict(l) for l in alea.sample(lignes, 6)]
    for ligne in doublons:                      # même référence, prix différent
        ligne["prix_ht"] = ligne["prix_ht"].replace(",", ".") + " €"
        ligne["date_maj"] = "01/09/2026"
    lignes.extend(doublons)

    for ligne in alea.sample(lignes, 4):        # prix manquant
        ligne["prix_ht"] = ""
    for ligne in alea.sample(lignes, 2):        # prix aberrant
        ligne["prix_ht"] = "-12,00"
    for ligne in alea.sample(lignes, 3):        # libellé bruité
        ligne["libelle"] = "  " + ligne["libelle"].upper() + "   "
    for ligne in alea.sample(lignes, 2):        # référence tronquée
        ligne["reference"] = ""

    alea.shuffle(lignes)
    return lignes


def main() -> None:
    lignes = fabriquer()
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with DESTINATION.open("w", encoding="utf-8", newline="") as flux:
        graveur = csv.DictWriter(flux, fieldnames=COLONNES, delimiter=";")
        graveur.writeheader()
        graveur.writerows(lignes)
    print(f"{DESTINATION} : {len(lignes)} lignes (défauts compris)")


if __name__ == "__main__":
    main()
