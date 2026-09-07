"""Registre de projets — un devis par projet, isolé et persisté sur disque.

Avant : `SESSION = Session()` au niveau du module `app.main`. Tous les visiteurs
partageaient le même devis, et un redémarrage d'uvicorn le perdait. C'est
acceptable pour une démo jouée seul, pas pour un artisan qui dicte un chantier
le matin et le rouvre l'après-midi (docs/STORIES.md US-16).

Le stockage est volontairement du **JSON à plat sur disque** : pas de base de
données à ce stade du projet, et un fichier lisible à l'œil vaut mieux qu'un
schéma qu'il faudrait migrer à chaque évolution du devis.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from app.catalogue import Produit
from app.devis import Devis, LigneChiffree
from app.pipeline import Correction, Escalade, Session

# Chemin absolu par défaut, dérivé de l'emplacement du paquet : l'application
# doit démarrer depuis n'importe quel répertoire courant.
RACINE_DONNEES = Path(
    os.environ.get("BTP_DONNEES") or Path(__file__).resolve().parent.parent / "donnees"
)

# Un identifiant de projet finit en nom de fichier : liste blanche stricte, pour
# qu'aucune entrée ne puisse remonter l'arborescence (docs/STORIES.md US-20).
MOTIF_ID = re.compile(r"^[a-z0-9]{8,32}$")


class ProjetIntrouvable(Exception):
    pass


def nouvel_identifiant() -> str:
    return uuid.uuid4().hex[:16]


def _chemin(projet_id: str, racine: Path | None = None) -> Path:
    if not MOTIF_ID.match(projet_id):
        raise ValueError(f"identifiant de projet invalide : {projet_id!r}")
    return (racine or RACINE_DONNEES) / f"{projet_id}.json"


# --------------------------------------------------------------------------
# Sérialisation — explicite plutôt que dataclasses.asdict(), pour que l'ajout
# d'un champ au devis soit un choix conscient et non une migration silencieuse.
# --------------------------------------------------------------------------

def _produit_en_dict(p: Produit | None) -> dict | None:
    if p is None:
        return None
    return {"reference": p.reference, "designation": p.designation,
            "categorie": p.categorie, "unite_vente": p.unite_vente,
            "prix_unitaire_ht": p.prix_unitaire_ht, "promo_pct": p.promo_pct,
            "contenance": p.contenance}


def serialiser_session(session: Session) -> dict:
    return {
        "version": 1,
        "historique": session.historique,
        "pieces": session.pieces,
        "lots_presents": session.lots_presents,
        "devis": {
            "mentions": sorted(session.devis.mentions),
            "lignes": [
                {"lot_code": l.lot_code, "nom_lot": l.nom_lot,
                 "produit": _produit_en_dict(l.produit),
                 "quantite_achat": l.quantite_achat,
                 "prix_unitaire_ht": l.prix_unitaire_ht, "prix_ht": l.prix_ht,
                 "taux_tva": l.taux_tva, "origine": l.origine,
                 "dimension_type": l.dimension_type,
                 "dimension_valeur": l.dimension_valeur}
                for l in session.devis.lignes
            ],
        },
        "corrections": [{"horodatage": c.horodatage, "auteur": c.auteur,
                         "description": c.description} for c in session.corrections],
        "escalades": [{"horodatage": e.horodatage, "motif": e.motif,
                       "detail": e.detail} for e in session.escalades],
    }


def deserialiser_session(brut: dict) -> Session:
    devis = Devis(mentions=set(brut.get("devis", {}).get("mentions", [])))
    for l in brut.get("devis", {}).get("lignes", []):
        produit = Produit(**l["produit"]) if l.get("produit") else None
        devis.lignes.append(LigneChiffree(
            lot_code=l["lot_code"], nom_lot=l["nom_lot"], produit=produit,
            quantite_achat=l["quantite_achat"],
            prix_unitaire_ht=l["prix_unitaire_ht"], prix_ht=l["prix_ht"],
            taux_tva=l["taux_tva"], origine=l.get("origine", "modèle"),
            dimension_type=l.get("dimension_type"),
            dimension_valeur=l.get("dimension_valeur"),
        ))
    return Session(
        historique=brut.get("historique", []),
        devis=devis,
        pieces=brut.get("pieces", []),
        lots_presents=brut.get("lots_presents", []),
        corrections=[Correction(**c) for c in brut.get("corrections", [])],
        escalades=[Escalade(**e) for e in brut.get("escalades", [])],
    )


# --------------------------------------------------------------------------
# Registre
# --------------------------------------------------------------------------

class Registre:
    """Cache mémoire + miroir disque. Le cache évite de relire le fichier à
    chaque tour ; le disque survit au redémarrage."""

    def __init__(self, racine: Path | None = None) -> None:
        self.racine = Path(racine) if racine else RACINE_DONNEES
        self._cache: dict[str, Session] = {}

    def creer(self) -> tuple[str, Session]:
        projet_id = nouvel_identifiant()
        session = Session()
        self._cache[projet_id] = session
        self.enregistrer(projet_id, session)
        return projet_id, session

    def obtenir(self, projet_id: str) -> Session:
        if projet_id in self._cache:
            return self._cache[projet_id]
        chemin = _chemin(projet_id, self.racine)
        if not chemin.exists():
            raise ProjetIntrouvable(projet_id)
        session = deserialiser_session(json.loads(chemin.read_text(encoding="utf-8")))
        self._cache[projet_id] = session
        return session

    def obtenir_ou_creer(self, projet_id: str | None) -> tuple[str, Session]:
        if projet_id:
            try:
                return projet_id, self.obtenir(projet_id)
            except (ProjetIntrouvable, ValueError):
                pass  # identifiant périmé ou forgé : on repart d'un projet neuf
        return self.creer()

    def enregistrer(self, projet_id: str, session: Session) -> None:
        chemin = _chemin(projet_id, self.racine)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        # Écriture atomique : un devis à moitié écrit serait illisible au
        # rechargement, et le montage OneDrive rend les écritures partielles
        # plausibles (voir CLAUDE.md).
        provisoire = chemin.with_suffix(".json.tmp")
        provisoire.write_text(
            json.dumps(serialiser_session(session), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        provisoire.replace(chemin)
        self._cache[projet_id] = session

    def reinitialiser(self, projet_id: str) -> Session:
        session = Session()
        self.enregistrer(projet_id, session)
        return session

    def lister(self) -> list[str]:
        if not self.racine.exists():
            return []
        return sorted(f.stem for f in self.racine.glob("*.json"))
