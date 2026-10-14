"""Journal applicatif et agrégation des métriques (docs/produit/DISPOSITIF_AGENT.md §4.3).

« Une application qui définit ses métriques sans les mesurer ne les respecte
pas : elle les espère » (docs/produit/STORIES.md US-24). Ce module écrit une ligne JSON
par événement et sait relire ce journal pour en tirer les seuils du §4.3.

Trois partis pris :

- **Le journal ne doit jamais casser un tour.** Toute écriture est protégée :
  un disque plein dégrade l'observabilité, pas le produit.
- **Format JSONL, un fichier**, relisible à l'œil et sans dépendance — même
  raison que pour `app/persistance.py`.
- **On ne mesure que ce qu'on observe vraiment.** Les métriques 2, 3, 4 et 5
  demandent un jeu d'essai annoté à la main ; elles sont déclarées « non
  mesurée » plutôt qu'approchées par un chiffre flatteur.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

RACINE_DONNEES = Path(
    os.environ.get("BTP_DONNEES") or Path(__file__).resolve().parent.parent / "donnees"
)

# Recopiés du §4.3 sans réinterprétation. `sens` dit dans quel sens comparer.
@dataclass(frozen=True)
class Seuil:
    numero: int
    libelle: str
    seuil: float | None
    unite: str
    sens: str  # "min" (≥), "max" (≤)
    mesurable_en_production: bool


SEUILS: tuple[Seuil, ...] = (
    Seuil(1, "Taux de JSON valide", 98.0, "%", "min", True),
    Seuil(2, "Exactitude des quantités", 90.0, "%", "min", False),
    Seuil(3, "Complétude des lots", 85.0, "%", "min", False),
    Seuil(4, "Rappel des consommables", 80.0, "%", "min", False),
    Seuil(5, "Justesse de la mention", 95.0, "%", "min", False),
    Seuil(6, "Détection hors périmètre", 95.0, "%", "min", False),
    Seuil(7, "Prix ou référence inventés", 0.0, "occurrences", "max", True),
    Seuil(8, "Latence d'un devis (p95)", 30.0, "s", "max", True),
)

NON_MESUREE = (
    "non mesurée en exploitation — demande le jeu d'essai annoté à la main"
)


class Journal:
    """Écrit un événement par ligne dans `journal.jsonl`."""

    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = Path(chemin) if chemin else RACINE_DONNEES / "journal.jsonl"

    def enregistrer(self, evenement: str, **champs: object) -> None:
        ligne = {"horodatage": dt.datetime.now().isoformat(timespec="seconds"),
                 "evenement": evenement, **champs}
        try:
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
            with self.chemin.open("a", encoding="utf-8") as f:
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
        except OSError:
            # Observabilité dégradée, produit intact : c'est le bon arbitrage.
            pass

    def evenements(self, limite: int = 10_000) -> list[dict]:
        try:
            lignes = self.chemin.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return []
        retenus: list[dict] = []
        for ligne in lignes[-limite:]:
            try:
                retenus.append(json.loads(ligne))
            except json.JSONDecodeError:
                continue  # ligne tronquée par un arrêt brutal : on l'ignore
        return retenus


def _p95(valeurs: list[float]) -> float | None:
    """p95 par rang, sans interpolation — assumé, et suffisant à cette échelle."""
    if not valeurs:
        return None
    ordonnees = sorted(valeurs)
    rang = max(0, min(len(ordonnees) - 1, round(0.95 * len(ordonnees)) - 1))
    return ordonnees[rang]


def _statut(seuil: Seuil, valeur: float | None) -> str:
    if valeur is None:
        return "non mesuré"
    if seuil.seuil is None:
        return "sans seuil"
    respecte = valeur >= seuil.seuil if seuil.sens == "min" else valeur <= seuil.seuil
    return "conforme" if respecte else "sous le seuil"


def agreger(journal: Journal) -> dict:
    """Relit le journal et rend l'état des métriques, mesurables ou non."""
    evenements = journal.evenements()
    appels = [e for e in evenements if e.get("evenement") == "appel_modele"]
    tours = [e for e in evenements if e.get("evenement") == "tour"]

    valides = sum(1 for a in appels if a.get("valide"))
    taux_json = round(100.0 * valides / len(appels), 1) if appels else None
    p95_ms = _p95([float(t["latence_ms"]) for t in tours if "latence_ms" in t])
    p95_s = round(p95_ms / 1000.0, 2) if p95_ms is not None else None
    # Métrique 7 : structurelle. Le schéma de sortie ne porte ni prix ni
    # référence produit (app/schema.py) — le modèle n'a pas de champ où en
    # inventer. Ce qu'on compte ici, ce sont les tentatives détectées.
    prix_inventes = sum(1 for e in evenements if e.get("evenement") == "prix_invente")

    valeurs: dict[int, float | None] = {1: taux_json, 7: float(prix_inventes), 8: p95_s}
    lignes = []
    for seuil in SEUILS:
        valeur = valeurs.get(seuil.numero)
        lignes.append({
            "numero": seuil.numero,
            "libelle": seuil.libelle,
            "seuil": seuil.seuil,
            "unite": seuil.unite,
            "sens": seuil.sens,
            "valeur": valeur,
            "statut": _statut(seuil, valeur) if seuil.mesurable_en_production else "non mesuré",
            "commentaire": "" if seuil.mesurable_en_production else NON_MESUREE,
        })

    return {
        "metriques": lignes,
        "volumes": {
            "appels_modele": len(appels),
            "tours": len(tours),
            "reprises": sum(int(t.get("reprises", 0)) for t in tours),
            "hors_perimetre": sum(1 for e in evenements
                                  if e.get("evenement") == "hors_perimetre"),
            "injections_neutralisees": sum(1 for e in evenements
                                           if e.get("evenement") == "injection_neutralisee"),
            "corrections_artisan": sum(1 for e in evenements
                                       if e.get("evenement") == "correction_artisan"),
        },
        "modeles_vus": sorted({str(a.get("modele")) for a in appels if a.get("modele")}),
        "depuis": evenements[0]["horodatage"] if evenements else None,
        "jusqu_a": evenements[-1]["horodatage"] if evenements else None,
    }


JOURNAL = Journal()
