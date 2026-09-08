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

import datetime as dt
import json
import os
import re
import uuid
from pathlib import Path

from app.catalogue import Produit
from app.devis import Devis, LigneChiffree
from app.pipeline import Correction, Escalade, LigneEnAttente, Session
from app.profil import Client, Decennale, ProfilArtisan, RegimeTVA

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


def _profil_en_dict(p: ProfilArtisan) -> dict:
    d = p.decennale
    return {
        "raison_sociale": p.raison_sociale, "siret": p.siret, "adresse": p.adresse,
        "rcs": p.rcs, "ape_naf": p.ape_naf,
        "tva_intracommunautaire": p.tva_intracommunautaire,
        "regime_tva": str(p.regime_tva),
        "decennale": {
            "assureur": d.assureur, "numero_contrat": d.numero_contrat,
            "couverture_geographique": d.couverture_geographique,
            # Date sérialisée en ISO : json ne sait pas écrire un datetime.date.
            "valide_jusqu_au": d.valide_jusqu_au.isoformat() if d.valide_jusqu_au else None,
        },
    }


def _profil_depuis_dict(brut: dict) -> ProfilArtisan:
    d = brut.get("decennale", {})
    echeance = d.get("valide_jusqu_au")
    return ProfilArtisan(
        raison_sociale=brut.get("raison_sociale", ""), siret=brut.get("siret", ""),
        adresse=brut.get("adresse", ""), rcs=brut.get("rcs", ""),
        ape_naf=brut.get("ape_naf", ""),
        tva_intracommunautaire=brut.get("tva_intracommunautaire", ""),
        regime_tva=RegimeTVA(brut.get("regime_tva", RegimeTVA.REEL)),
        decennale=Decennale(
            assureur=d.get("assureur", ""), numero_contrat=d.get("numero_contrat", ""),
            couverture_geographique=d.get("couverture_geographique", ""),
            valide_jusqu_au=dt.date.fromisoformat(echeance) if echeance else None,
        ),
    )


def _correction_depuis_dict(brut: dict) -> Correction:
    """Relit une correction. Les projets écrits avant la version 4 n'ont pas le
    triplet : on ne l'invente pas, `app.boucle_qualite` les comptera incomplets."""
    return Correction(
        horodatage=brut.get("horodatage", ""), auteur=brut.get("auteur", "artisan"),
        description=brut.get("description", ""), origine=brut.get("origine", ""),
        entree=brut.get("entree", ""), sortie_modele=brut.get("sortie_modele", ""),
        corrige=brut.get("corrige", ""),
    )


def serialiser_session(session: Session) -> dict:
    return {
        "version": 4,
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
                 "quantite_technique": l.quantite_technique,
                 "unite_technique": l.unite_technique,
                 "chiffree": l.chiffree,
                 "dimension_type": l.dimension_type,
                 "dimension_valeur": l.dimension_valeur}
                for l in session.devis.lignes
            ],
        },
        "tours_clarification": session.tours_clarification,
        "a_confirmer": [{"lot_code": a.lot_code, "dimension_type": a.dimension_type,
                         "dimension_valeur": a.dimension_valeur,
                         "borne_min": a.borne_min, "borne_max": a.borne_max}
                        for a in session.a_confirmer],
        # Version 4 : le triplet du signal qualité (US-25). Sans lui, une
        # correction relue du disque n'est plus exportable.
        "corrections": [{"horodatage": c.horodatage, "auteur": c.auteur,
                         "description": c.description, "origine": c.origine,
                         "entree": c.entree, "sortie_modele": c.sortie_modele,
                         "corrige": c.corrige} for c in session.corrections],
        "escalades": [{"horodatage": e.horodatage, "motif": e.motif,
                       "detail": e.detail} for e in session.escalades],
        "profil": _profil_en_dict(session.profil),
        "client": {"nom": session.client.nom,
                   "adresse_chantier": session.client.adresse_chantier},
        "delai_execution": session.delai_execution,
        "structure_validee": session.structure_validee,
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
            quantite_technique=l.get("quantite_technique", l["quantite_achat"]),
            unite_technique=l.get("unite_technique", ""),
            # Projets écrits avant la version 3 : le devis était chiffré dès
            # l'ajout de la ligne, donc toute ligne relue est chiffrée.
            chiffree=l.get("chiffree", True),
            dimension_type=l.get("dimension_type"),
            dimension_valeur=l.get("dimension_valeur"),
        ))
    return Session(
        historique=brut.get("historique", []),
        devis=devis,
        pieces=brut.get("pieces", []),
        lots_presents=brut.get("lots_presents", []),
        corrections=[_correction_depuis_dict(c) for c in brut.get("corrections", [])],
        escalades=[Escalade(**e) for e in brut.get("escalades", [])],
        tours_clarification=brut.get("tours_clarification", 0),
        a_confirmer=[LigneEnAttente(**a) for a in brut.get("a_confirmer", [])],
        # Les projets écrits en version 1 n'ont pas ces clés : un profil vide
        # est le bon repli, l'export les réclamera au premier essai.
        profil=_profil_depuis_dict(brut.get("profil", {})),
        client=Client(**brut.get("client", {})),
        delai_execution=brut.get("delai_execution", ""),
        # Idem : avant la version 3, un devis qui portait des lignes portait
        # aussi ses prix — le relire comme « structure non validée » masquerait
        # un chiffrage déjà fait.
        structure_validee=brut.get("structure_validee", devis.chiffre),
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
