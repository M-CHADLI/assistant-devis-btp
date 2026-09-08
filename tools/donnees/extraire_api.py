"""Étape 2 — extraction depuis un **service web (API REST)**.

Source : *Base Carbone®* de l'ADEME, exposée par l'API data-fair de
`data.ademe.fr`, sous **Licence Ouverte / Open Licence**. Elle publie des
facteurs d'émission par matériau, en kgCO2e par kilogramme.

**Pourquoi cette source et pas une autre.** Le devis du produit chiffre des
matériaux ; la Base Carbone est la référence publique française pour leur
impact. C'est aussi la seule des trois sources de la chaîne qui soit
authentiquement externe, ouverte et citable — les deux autres sont un fichier
simulé et une page encyclopédique.

**Ce que l'extraction ne fait pas.** Elle ne décide pas que le produit
affichera une empreinte carbone : cette fonction n'est pas au périmètre
(`CLAUDE.md`, noyau de démo). Elle met la matière au jeu de données, où elle
attend un arbitrage. Extraire n'est pas livrer.

Dépendances : `requests` (déjà au projet).

**Reprise sur erreur.** L'API peut être indisponible ; le script ne doit alors
ni écraser l'extrait précédent, ni faire échouer la chaîne entière. Il tente
chaque requête trois fois, espacées, et n'écrit qu'à la fin, une fois toutes
les familles récupérées.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.extraire_api
```
"""
from __future__ import annotations

import sys
import time

import requests

from tools.donnees.commun import ecrire_brut

RACINE_API = "https://data.ademe.fr/data-fair/api/v1/datasets/base-carboner/lines"

CHAMPS = ("Nom_base_français,Nom_attribut_français,Unité_français,"
          "Total_poste_non_décomposé,Code_de_la_catégorie,Localisation_géographique,"
          "Type_Ligne,Incertitude,Date_de_modification")

# Les termes interrogés couvrent les matériaux des quatre corps de métier du
# périmètre pilote. Ils sont explicites plutôt que génériques : « peinture »
# seul ramène quatre lignes, la liste ci-dessous en ramène assez pour joindre.
TERMES = ["peinture", "résine", "plâtre", "ciment", "mortier", "carrelage",
          "céramique", "parquet", "bois", "stratifié", "PVC", "polyéthylène",
          "cuivre", "acier", "aluminium", "zinc", "verre", "laine de verre",
          "laine de roche", "polystyrène"]

TENTATIVES = 3
DELAI_ENTRE_TENTATIVES = 2.0
DELAI_ENTRE_REQUETES = 0.3   # politesse envers un service public gratuit


def _interroger(terme: str, taille: int = 40) -> list[dict]:
    """Une requête, réessayée. Lève après la dernière tentative."""
    parametres = {"q": terme, "size": taille, "select": CHAMPS,
                  "qs": 'Type_Ligne:"Elément"'}
    derniere: Exception | None = None
    for essai in range(1, TENTATIVES + 1):
        try:
            reponse = requests.get(RACINE_API, params=parametres, timeout=30)
            reponse.raise_for_status()
            return reponse.json().get("results", [])
        except (requests.RequestException, ValueError) as erreur:
            derniere = erreur
            if essai < TENTATIVES:
                time.sleep(DELAI_ENTRE_TENTATIVES * essai)
    raise RuntimeError(f"terme « {terme} » : {derniere}")


def extraire(termes: list[str] | None = None) -> list[dict]:
    """Les facteurs d'émission des termes demandés, dédoublonnés à la source."""
    vus: set[tuple] = set()
    lignes: list[dict] = []
    for terme in termes or TERMES:
        for resultat in _interroger(terme):
            cle = (resultat.get("Nom_base_français"),
                   resultat.get("Nom_attribut_français"),
                   resultat.get("Total_poste_non_décomposé"))
            if cle in vus:
                continue
            vus.add(cle)
            resultat["terme_interroge"] = terme
            resultat.pop("_score", None)
            lignes.append(resultat)
        time.sleep(DELAI_ENTRE_REQUETES)
    return lignes


def main() -> int:
    try:
        lignes = extraire()
    except RuntimeError as erreur:
        print(f"extraction API échouée, extrait précédent conservé : {erreur}",
              file=sys.stderr)
        return 1
    cible = ecrire_brut(
        "api_ademe_base_carbone",
        source=f"ADEME Base Carbone® — {RACINE_API}",
        licence="Licence Ouverte / Open Licence (Etalab)",
        lignes=lignes,
        notes="Facteurs d'émission en kgCO2e/kg. Interrogation par termes "
              "métier, lignes de type « Elément » uniquement, dédoublonnées "
              "sur (nom, attribut, valeur).")
    print(f"{cible} : {len(lignes)} facteurs d'émission")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
