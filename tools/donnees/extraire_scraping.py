"""Étape 3 — extraction par **scraping** d'une page web.

Source : l'article « Masse volumique » de Wikipédia en français, sous licence
**CC BY-SA**. L'attribution est portée dans l'en-tête de provenance de
l'extrait, comme la licence l'exige.

**Pourquoi cette page, et pourquoi ce n'est pas un prétexte.** L'API de l'ADEME
donne des facteurs d'émission **au kilogramme** ; l'export fournisseur vend au
litre, au m² ou au mètre linéaire. Sans masse volumique, les deux sources ne
peuvent pas se joindre — un seau de 10 L de peinture ne se convertit pas en
kilogrammes tout seul. Cette page est le chaînon manquant du jeu de données,
pas une case à cocher.

**Politesse.** Une seule requête, un agent utilisateur qui dit qui appelle, et
`robots.txt` vérifié le 08/09/2026 : `/wiki/Masse_volumique` n'est pas dans les
`Disallow` de `User-agent: *`. La page est relue depuis le disque tant qu'un
cache local existe, pour ne pas refrapper le serveur à chaque exécution.

**Analyse sans dépendance.** `html.parser` de la bibliothèque standard suffit à
lire des tableaux `wikitable` ; ajouter un analyseur HTML tiers pour cinq
tableaux alourdirait le projet sans rien apporter.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.extraire_scraping
```
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import requests

from tools.donnees.commun import ecrire_brut

URL = "https://fr.wikipedia.org/wiki/Masse_volumique"
AGENT = "the-project/0.1 (projet de soutenance AI Engineer ; une requête par exécution)"
CACHE = Path("catalogue/sources/wikipedia_masse_volumique.html")

# Les tableaux retenus, par leur titre de première colonne. Les gaz et le
# tableau d'humidité des bois ne servent à rien au chantier.
FAMILLES_RETENUES = {
    "roches, minéraux, matériaux usuels": "materiau_usuel",
    "métaux et alliages": "metal",
    "liquides": "liquide",
    "matières plastiques, caoutchouc": "plastique",
    "bois": "bois",
}


class _LecteurDeTableaux(HTMLParser):
    """Rend les tableaux `wikitable` sous forme de listes de listes de texte."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tableaux: list[list[list[str]]] = []
        self._profondeur = 0
        self._dans_cellule = False
        self._tampon: list[str] = []
        self._ligne: list[str] = []

    def handle_starttag(self, balise, attributs):
        valeurs = dict(attributs)
        if balise == "table":
            if "wikitable" in (valeurs.get("class") or ""):
                self._profondeur = 1
                self.tableaux.append([])
            elif self._profondeur:
                self._profondeur += 1     # tableau imbriqué : on le traverse
        elif self._profondeur == 1 and balise == "tr":
            self._ligne = []
        elif self._profondeur == 1 and balise in ("td", "th"):
            self._dans_cellule, self._tampon = True, []

    def handle_endtag(self, balise):
        if balise == "table" and self._profondeur:
            self._profondeur -= 1
        elif self._profondeur == 1 and balise in ("td", "th") and self._dans_cellule:
            self._ligne.append("".join(self._tampon).strip())
            self._dans_cellule = False
        elif self._profondeur == 1 and balise == "tr" and self._ligne:
            self.tableaux[-1].append(self._ligne)
            self._ligne = []

    def handle_data(self, donnee):
        if self._dans_cellule:
            self._tampon.append(donnee)


def telecharger(forcer: bool = False) -> str:
    """La page, depuis le cache local si possible."""
    if CACHE.exists() and not forcer:
        return CACHE.read_text(encoding="utf-8")
    reponse = requests.get(URL, headers={"User-Agent": AGENT}, timeout=30)
    reponse.raise_for_status()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(reponse.text, encoding="utf-8")
    return reponse.text


def extraire(html_source: str | None = None) -> list[dict[str, str]]:
    lecteur = _LecteurDeTableaux()
    lecteur.feed(html_source if html_source is not None else telecharger())

    lignes: list[dict[str, str]] = []
    for tableau in lecteur.tableaux:
        if not tableau:
            continue
        titre = re.sub(r"\s+", " ", tableau[0][0]).strip().lower()
        famille = FAMILLES_RETENUES.get(titre)
        if famille is None:
            continue
        for cellules in tableau[1:]:
            if len(cellules) < 2 or not cellules[0]:
                continue
            lignes.append({
                "famille_source": famille,
                "materiau": re.sub(r"\s+", " ", cellules[0]).strip(),
                "masse_volumique_brut": re.sub(r"\s+", " ", cellules[1]).strip(),
            })
    return lignes


def main() -> int:
    try:
        lignes = extraire()
    except (requests.RequestException, OSError) as erreur:
        print(f"scraping échoué, extrait précédent conservé : {erreur}",
              file=sys.stderr)
        return 1
    if not lignes:
        print("scraping : aucune ligne extraite — la page a probablement changé "
              "de structure. Extrait précédent conservé.", file=sys.stderr)
        return 1
    cible = ecrire_brut(
        "scraping_masses_volumiques",
        source=f"Wikipédia (fr) — {URL}",
        licence="CC BY-SA 4.0 — contributeurs de Wikipédia",
        lignes=lignes,
        notes="Cinq tableaux retenus sur sept (gaz et humidité des bois "
              "écartés). Valeurs laissées telles quelles : intervalles, "
              "renvois de note et espaces insécables sont normalisés à "
              "l'agrégation, pas ici.")
    print(f"{cible} : {len(lignes)} masses volumiques")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
