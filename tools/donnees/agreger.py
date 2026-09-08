"""Étape 4 — agrégation : nettoyer, homogénéiser, joindre, en un seul jeu.

Les trois extractions ne se ressemblent pas : un export fournisseur sale, une
API publique aux unités hétérogènes, un tableau encyclopédique aux valeurs
écrites en toutes lettres. Ce script en fait **un seul jeu de données**,
`catalogue/jeu_de_donnees.json`, et rend compte de ce qu'il a jeté.

**Trois principes tiennent l'algorithme.**

1. *Rien n'est supprimé en silence.* Chaque ligne écartée est comptée avec son
   motif dans le rapport. Un script d'agrégation qui perd des lignes sans le
   dire est indétectable jusqu'au jour où le devis est faux.
2. *Aucune valeur n'est inventée.* Quand la correspondance n'existe pas — il
   n'y a pas de masse volumique de peinture dans la source scrapée — le champ
   reste `null` et porte son motif. Interpoler une densité plausible
   fabriquerait une donnée que rien ne soutient.
3. *La qualité de correspondance est une donnée.* Rapprocher une peinture
   acrylique murale d'un « Vernis Acrylique » est un **proxy**, pas une
   identité. Le jeu de données le dit, colonne `qualite_correspondance`, pour
   que l'aval ne prenne jamais un proxy pour une mesure.

Enchaînement : lecture des trois extraits → nettoyage du fichier fournisseur →
normalisation des facteurs d'émission → normalisation des masses volumiques →
jointure par famille via une table de correspondance explicite → rapport.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.agreger
```
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tools.donnees.commun import lire_brut

DESTINATION = Path("catalogue/jeu_de_donnees.json")

# --- Table de correspondance ------------------------------------------------
# Écrite à la main, une ligne par famille de l'export. C'est le seul endroit du
# projet où un humain décide qu'un produit « est » telle matière ; le reste du
# script n'est que de la mécanique. La qualité annoncée engage : « exacte »
# quand la source nomme la même chose, « proxy » quand elle nomme le plus
# proche disponible.
CORRESPONDANCES: dict[str, dict[str, Any]] = {
    "PEINTURE_PREPARATION": {
        "matiere": "enduit", "ademe": ("Chaux", None), "qualite": "proxy",
        "densite": "craie",
        "reserve": "L'enduit de rebouchage est plâtreux ; la source ne publie "
                   "ni plâtre ni enduit, la chaux en est le liant le plus proche."},
    "PEINTURE_SOUS_COUCHE": {
        "matiere": "peinture", "ademe": ("Vernis Acrylique", None), "qualite": "proxy",
        "densite": None,
        "reserve": "Aucune masse volumique de peinture dans la source scrapée."},
    "PEINTURE_FINITION": {
        "matiere": "peinture", "ademe": ("Vernis Acrylique", None), "qualite": "proxy",
        "densite": None,
        "reserve": "Aucune masse volumique de peinture dans la source scrapée."},
    "SOL_PREPARATION": {
        "matiere": "ciment", "ademe": ("Ciment Portland", None), "qualite": "exacte",
        "densite": "béton",
        "reserve": "Densité du béton retenue faute de valeur pour le ragréage."},
    "SOL_SOUS_COUCHE": {
        "matiere": "polyéthylène", "ademe": ("Plastique", "PEBD"), "qualite": "exacte",
        "densite": "PEBD", "reserve": ""},
    "SOL_STRATIFIE": {
        "matiere": "bois", "ademe": ("Bois d'oeuvre (construction)", None),
        "qualite": "exacte", "densite": "contreplaqué",
        "reserve": "Le stratifié a une âme en panneau de fibres ; le "
                   "contreplaqué est la densité la plus proche publiée."},
    "SOL_PARQUET": {
        "matiere": "bois", "ademe": ("Bois d'oeuvre (construction)", None),
        "qualite": "exacte", "densite": "chêne", "reserve": ""},
    "SOL_CARRELAGE": {
        "matiere": "grès cérame", "ademe": None, "qualite": "absente",
        "densite": "grès",
        "reserve": "Aucun facteur d'émission céramique dans l'extrait : les "
                   "produits minéraux n'y figurent qu'en ratios monétaires."},
    "PLOMBERIE_ALIMENTATION": {
        "matiere": "multicouche", "ademe": ("Plastique", "PEHD"), "qualite": "proxy",
        "densite": "PEHD",
        "reserve": "Le multicouche est un composite PE-aluminium-PE ; seul le "
                   "polyéthylène est représenté."},
    "PLOMBERIE_EVACUATION": {
        "matiere": "PVC", "ademe": ("Plastique", "PVC"), "qualite": "exacte",
        "densite": "PVC rigide", "reserve": ""},
    "PLOMBERIE_ROBINETTERIE": {
        "matiere": "laiton", "ademe": ("Cuivre", None), "qualite": "proxy",
        "densite": "laiton",
        "reserve": "Le laiton est un alliage cuivre-zinc ; la source ne "
                   "publie de facteur que pour les métaux purs."},
    "ELECTRICITE_CABLE": {
        "matiere": "cuivre", "ademe": ("Cuivre", None), "qualite": "exacte",
        "densite": "cuivre", "reserve": ""},
    "ELECTRICITE_APPAREILLAGE": {
        "matiere": "plastique technique", "ademe": ("Plastique", "PS"),
        "qualite": "proxy", "densite": "ABS",
        "reserve": "L'appareillage est en ABS ou polycarbonate ; le "
                   "polystyrène en est le plus proche publié."},
    "ELECTRICITE_TABLEAU": {
        "matiere": "acier", "ademe": ("Acier ou fer blanc", None), "qualite": "proxy",
        "densite": "acier",
        "reserve": "Un disjoncteur mêle acier, cuivre et plastique ; la "
                   "matière dominante en masse est retenue."},
}

# Catégories de la Base Carbone qui concernent des matériaux. Le reste de
# l'extrait — agro-alimentaire, déchets, réseaux de chaleur — est ramené par la
# recherche plein texte et n'a rien à faire dans un catalogue de chantier.
CATEGORIES_MATERIAUX = {
    "Produits minéraux non métalliques", "Plastiques et produits chimiques",
    "Métaux et produits métalliques", "Autres produits manufacturés", "Bois",
}

UNITES_MASSE = {          # facteur de conversion vers kgCO2e/kg
    "kgCO2e/kg": 1.0,
    "kgCO2e/kg de poids net": 1.0,
    "kgCO2e/tonne": 0.001,
}

UNITES_VENTE = {"m2": "m²", "m²": "m²", "ml": "ml", "u": "u"}


# --- Nettoyage du fichier fournisseur ---------------------------------------

def _nombre(brut: str) -> float | None:
    """« 34,90 » · « 34.90 € » · «  1 234,5  » → un flottant, ou None."""
    if not brut:
        return None
    texte = (brut.replace(" ", "").replace(" ", "")
             .replace(" ", "").replace("€", "").replace(",", "."))
    try:
        return float(texte)
    except ValueError:
        return None


def _date_iso(brut: str) -> str | None:
    """Les deux formats du dump ramenés à un seul : AAAA-MM-JJ."""
    brut = (brut or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", brut):
        return brut
    jour = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", brut)
    return f"{jour[3]}-{jour[2]}-{jour[1]}" if jour else None


def _libelle(brut: str) -> str:
    """Espaces réduits, capitales criardes ramenées à une casse de phrase."""
    texte = re.sub(r"\s+", " ", (brut or "").strip())
    lettres = [c for c in texte if c.isalpha()]
    if lettres and all(c.isupper() for c in lettres):
        texte = texte.capitalize()
    return texte


def nettoyer_produits(lignes: list[dict[str, str]]) -> tuple[list[dict], Counter]:
    """Applique les règles de rejet et de normalisation, puis dédoublonne."""
    rejets: Counter = Counter()
    retenus: dict[str, dict] = {}

    for ligne in lignes:
        reference = (ligne.get("reference") or "").strip()
        if not reference:
            rejets["référence absente"] += 1
            continue
        if (ligne.get("disponibilite") or "").strip() == "ARRET":
            rejets["produit en arrêt de commercialisation"] += 1
            continue
        prix = _nombre(ligne.get("prix_ht", ""))
        if prix is None:
            rejets["prix absent ou illisible"] += 1
            continue
        if prix <= 0:
            rejets["prix négatif ou nul"] += 1
            continue
        unite = UNITES_VENTE.get((ligne.get("unite_vente") or "").strip().lower())
        if unite is None:
            rejets["unité de vente inconnue"] += 1
            continue
        famille = (ligne.get("famille") or "").strip()
        if famille not in CORRESPONDANCES:
            rejets["famille hors périmètre"] += 1
            continue
        date = _date_iso(ligne.get("date_maj", ""))
        if date is None:
            rejets["date de mise à jour illisible"] += 1
            continue

        produit = {
            "reference": reference,
            "libelle": _libelle(ligne.get("libelle", "")),
            "famille": famille,
            "marque": (ligne.get("marque") or "").strip(),
            "unite_vente": unite,
            "contenance": _nombre(ligne.get("contenance", "")),
            "contenance_unite": (ligne.get("contenance_unite") or "").strip() or None,
            "prix_ht": round(prix, 2),
            "taux_promo": round((_nombre(ligne.get("taux_promo", "")) or 0) / 100, 4),
            "ean": (ligne.get("ean") or "").strip() or None,
            "date_maj": date,
        }
        # Doublon de référence : la ligne la plus récente gagne. Sur un export
        # réel, c'est la règle du fournisseur — la dernière mise à jour fait foi.
        ancien = retenus.get(reference)
        if ancien is None:
            retenus[reference] = produit
        else:
            rejets["doublon de référence"] += 1
            if produit["date_maj"] > ancien["date_maj"]:
                retenus[reference] = produit

    return sorted(retenus.values(), key=lambda p: p["reference"]), rejets


# --- Normalisation des facteurs d'émission ----------------------------------

def normaliser_facteurs(lignes: list[dict]) -> tuple[dict[tuple, dict], Counter]:
    """Regroupe par (nom, attribut) et ramène tout en kgCO2e/kg.

    La Base Carbone publie souvent plusieurs valeurs pour un même matériau
    (procédés, taux de recyclage, pays). En retenir une seule serait un choix
    caché : on garde la **médiane** et on publie l'étendue avec elle.
    """
    rejets: Counter = Counter()
    valeurs: dict[tuple, list[float]] = defaultdict(list)

    for ligne in lignes:
        categorie = (ligne.get("Code_de_la_catégorie") or "").split(" > ")
        if len(categorie) < 2 or categorie[1] not in CATEGORIES_MATERIAUX:
            rejets["catégorie hors matériaux"] += 1
            continue
        conversion = UNITES_MASSE.get(ligne.get("Unité_français") or "")
        if conversion is None:
            rejets["unité non massique"] += 1
            continue
        valeur = ligne.get("Total_poste_non_décomposé")
        if not isinstance(valeur, (int, float)):
            rejets["valeur absente"] += 1
            continue
        cle = (ligne.get("Nom_base_français"), ligne.get("Nom_attribut_français"))
        valeurs[cle].append(valeur * conversion)

    facteurs = {
        cle: {
            "facteur_kgco2e_par_kg": round(statistics.median(v), 5),
            "nombre_de_valeurs": len(v),
            "valeur_min": round(min(v), 5),
            "valeur_max": round(max(v), 5),
        }
        for cle, v in valeurs.items()
    }
    return facteurs, rejets


# --- Normalisation des masses volumiques ------------------------------------

_INTERVALLE = re.compile(r"([\d\s  ]+)\s*[–—-]\s*([\d\s  ]+)")


def normaliser_densites(lignes: list[dict]) -> tuple[dict[str, dict], Counter]:
    """« 2 700–2 800 » → 2750,0 · « 2 200 (armé 2 500) » → 2200,0."""
    rejets: Counter = Counter()
    densites: dict[str, dict] = {}

    for ligne in lignes:
        materiau = re.sub(r"\[\d+\]", "", ligne["materiau"]).strip()
        brut = ligne["masse_volumique_brut"]
        intervalle = _INTERVALLE.search(brut)
        if intervalle:
            bas, haut = _nombre(intervalle[1]), _nombre(intervalle[2])
            valeur = (bas + haut) / 2 if bas and haut else None
            etendue = [bas, haut]
        else:
            premier = re.search(r"[\d\s  ]+", brut)
            valeur = _nombre(premier[0]) if premier else None
            etendue = [valeur, valeur]
        if valeur is None:
            rejets["masse volumique illisible"] += 1
            continue
        densites[materiau.lower()] = {
            "masse_volumique_kg_m3": round(valeur, 1),
            "etendue": etendue,
            "famille_source": ligne["famille_source"],
        }
    return densites, rejets


# --- Jointure ---------------------------------------------------------------

def joindre(produits: list[dict], facteurs: dict, densites: dict) -> dict[str, int]:
    """Enrichit chaque produit et rend le compte des enrichissements réussis."""
    compte = Counter()
    for produit in produits:
        regle = CORRESPONDANCES[produit["famille"]]
        produit["matiere"] = regle["matiere"]
        produit["qualite_correspondance"] = regle["qualite"]
        produit["reserve_correspondance"] = regle["reserve"] or None

        facteur = facteurs.get(regle["ademe"]) if regle["ademe"] else None
        produit["facteur_kgco2e_par_kg"] = (
            facteur["facteur_kgco2e_par_kg"] if facteur else None)
        produit["facteur_etendue"] = (
            [facteur["valeur_min"], facteur["valeur_max"]] if facteur else None)
        produit["source_facteur"] = "ADEME Base Carbone" if facteur else None
        compte["facteur trouvé" if facteur else "facteur absent"] += 1

        densite = densites.get((regle["densite"] or "").lower()) if regle["densite"] else None
        produit["masse_volumique_kg_m3"] = (
            densite["masse_volumique_kg_m3"] if densite else None)
        produit["source_densite"] = "Wikipédia (CC BY-SA)" if densite else None
        compte["densité trouvée" if densite else "densité absente"] += 1
    return dict(compte)


def agreger() -> dict:
    fichier = lire_brut("fichier_export_fournisseur")
    api = lire_brut("api_ademe_base_carbone")
    scraping = lire_brut("scraping_masses_volumiques")

    produits, rejets_produits = nettoyer_produits(fichier["lignes"])
    facteurs, rejets_facteurs = normaliser_facteurs(api["lignes"])
    densites, rejets_densites = normaliser_densites(scraping["lignes"])
    enrichissement = joindre(produits, facteurs, densites)

    return {
        "sources": [
            {"role": "fichier", "source": fichier["source"],
             "licence": fichier["licence"], "lignes_brutes": fichier["nombre_de_lignes"]},
            {"role": "api_rest", "source": api["source"],
             "licence": api["licence"], "lignes_brutes": api["nombre_de_lignes"]},
            {"role": "scraping", "source": scraping["source"],
             "licence": scraping["licence"], "lignes_brutes": scraping["nombre_de_lignes"]},
        ],
        "rapport": {
            "produits_retenus": len(produits),
            "rejets_produits": dict(rejets_produits),
            "facteurs_retenus": len(facteurs),
            "rejets_facteurs": dict(rejets_facteurs),
            "densites_retenues": len(densites),
            "rejets_densites": dict(rejets_densites),
            "enrichissement": enrichissement,
        },
        "produits": produits,
    }


def main() -> int:
    try:
        jeu = agreger()
    except FileNotFoundError as erreur:
        print(f"agrégation impossible : {erreur}", file=sys.stderr)
        return 1
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporaire = DESTINATION.with_suffix(".json.tmp")
    temporaire.write_text(json.dumps(jeu, ensure_ascii=False, indent=2), encoding="utf-8")
    temporaire.replace(DESTINATION)

    rapport = jeu["rapport"]
    print(f"{DESTINATION} : {rapport['produits_retenus']} produits")
    for titre, cle in (("rejets produits", "rejets_produits"),
                       ("rejets facteurs", "rejets_facteurs"),
                       ("rejets densités", "rejets_densites")):
        for motif, nombre in sorted(rapport[cle].items()):
            print(f"  {titre} — {motif} : {nombre}")
    for motif, nombre in sorted(rapport["enrichissement"].items()):
        print(f"  enrichissement — {motif} : {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
