"""Interface web de la démo — canal web uniquement, un seul interlocuteur :
l'artisan (docs/CADRAGE_MODELE.md §4).

Chaque navigateur travaille sur **son** projet, identifié par un cookie et
persisté sur disque (docs/STORIES.md US-16). Avant, une unique `Session` de
module était partagée par tous les visiteurs et perdue à chaque redémarrage.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.export import MentionsIncompletes, generer_docx
from app.persistance import Registre
from app.pipeline import (Session, abandonner_quantite, confirmer_quantite,
                          corriger_ligne, traiter_message, valider_structure,
                          valider_transcription)
from app.profil import Client, RegimeTVA, champs_manquants
from app.referentiel import REFERENTIEL
from app.transcription import relire

app = FastAPI(title="Démo — Assistant chantier BTP vocal")

REGISTRE = Registre()

# Chemin absolu dérivé du paquet : uvicorn doit pouvoir être lancé depuis
# n'importe quel répertoire courant sans casser la page d'accueil.
INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"

COOKIE_PROJET = "projet_id"
DUREE_COOKIE = 60 * 60 * 24 * 30  # 30 jours


def _projet(request: Request) -> tuple[str, Session]:
    """Résout le projet du visiteur, ou en ouvre un neuf."""
    return REGISTRE.obtenir_ou_creer(request.cookies.get(COOKIE_PROJET))


def _poser_cookie(response: Response, projet_id: str) -> None:
    response.set_cookie(COOKIE_PROJET, projet_id, max_age=DUREE_COOKIE,
                        httponly=True, samesite="lax")


def _serialiser_devis(session: Session) -> dict:
    """Sérialise le devis pour le navigateur.

    Avant HITL-2 (docs/STORIES.md US-12), **aucune clé de prix n'existe dans la
    réponse** : ni prix unitaire, ni total, ni ventilation. Ce n'est pas un
    masquage d'affichage — rien n'a été calculé côté serveur non plus.
    """
    validee = session.structure_validee
    lignes = []
    for l in session.devis.lignes:
        ligne = {
            "lot_code": l.lot_code,
            "designation": l.produit.designation if l.produit else l.nom_lot,
            "quantite": l.quantite_achat if validee else l.quantite_technique,
            "unite": (l.produit.unite_vente if l.produit else "") if validee
                     else l.unite_technique,
            "origine": l.origine,
        }
        if validee:
            ligne["prix_unitaire_ht"] = l.prix_unitaire_ht
            ligne["prix_ht"] = l.prix_ht
            ligne["taux_tva"] = l.taux_tva
        lignes.append(ligne)

    montants: dict = {
        "total_ht": None, "ventilation_tva": {}, "total_tva": None,
        "total_ttc": None, "acompte_30_pct": None,
    }
    if validee:
        montants = {
            "total_ht": session.devis.total_ht,
            "ventilation_tva": session.devis.ventilation_tva,
            "total_tva": session.devis.total_tva,
            "total_ttc": session.devis.total_ttc,
            "acompte_30_pct": session.devis.acompte_30_pct,
        }

    return {
        "pieces": session.pieces,
        "lignes": lignes,
        "structure_validee": validee,
        **montants,
        "mentions": sorted(session.devis.mentions),
        # En franchise (art. 293 B), le front masque tout ce qui touche à la
        # TVA : un devis d'auto-entrepreneur qui en affiche une est faux.
        "franchise_tva": session.profil.en_franchise,
        # Ce qui manque encore pour que l'export soit légalement recevable.
        "mentions_manquantes": champs_manquants(
            session.profil, session.client, session.delai_execution),
        # Lignes retenues parce que leur quantité sort des bornes (US-11) :
        # l'artisan doit confirmer ou abandonner avant qu'elles entrent au devis.
        "a_confirmer": [
            {"lot_code": a.lot_code,
             # Le nom métier, pas le code : l'artisan arbitre sur « Peinture de
             # finition », pas sur PEINT_FINITION.
             "lot_nom": REFERENTIEL[a.lot_code].nom if a.lot_code in REFERENTIEL else a.lot_code,
             "dimension_type": a.dimension_type,
             "dimension_valeur": a.dimension_valeur,
             "borne_min": a.borne_min, "borne_max": a.borne_max}
            for a in session.a_confirmer
        ],
        "corrections": [
            {"horodatage": c.horodatage, "auteur": c.auteur, "description": c.description}
            for c in session.corrections
        ],
    }


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


class MessageEntrant(BaseModel):
    texte: str


@app.get("/api/devis")
def api_devis(request: Request, response: Response) -> dict:
    """Resynchronise l'interface avec l'état serveur — utile après un simple
    rechargement de page, sans perdre le devis en cours."""
    projet_id, session = _projet(request)
    _poser_cookie(response, projet_id)
    return {"projet_id": projet_id, "devis": _serialiser_devis(session)}


@app.post("/api/message")
def api_message(msg: MessageEntrant, request: Request, response: Response) -> dict:
    projet_id, session = _projet(request)
    resultat = traiter_message(session, msg.texte)
    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return {
        "projet_id": projet_id,
        "intent": resultat.intent,
        "messages": resultat.messages_assistant,
        "mentions": resultat.mentions,
        "consommables_suggeres": resultat.consommables_suggeres,
        "cadrages": resultat.cadrages,
        "devis": _serialiser_devis(session),
    }


@app.post("/api/valider-structure")
def api_valider_structure(request: Request, response: Response) -> dict:
    """HITL-2 — l'artisan valide lots et quantités ; le chiffrage suit."""
    projet_id, session = _projet(request)
    applique = valider_structure(session)
    if not applique:
        raise HTTPException(status_code=409,
                            detail="il n'y a rien à valider : la structure est vide")
    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return {"projet_id": projet_id, "devis": _serialiser_devis(session)}


class DicteeEntrante(BaseModel):
    texte: str


class TranscriptionValidee(BaseModel):
    propose: str = ""
    texte: str


@app.post("/api/transcription")
def api_transcription(dictee: DicteeEntrante, request: Request,
                      response: Response) -> dict:
    """HITL-0 — remet la dictée en forme et la rend à relire. **Aucune étape
    aval n'est déclenchée ici** (docs/STORIES.md US-05) : le pipeline ne démarre
    qu'à `/api/transcription/valider`.

    La reformulation passe par `app.transcription`, qui utilise un modèle
    prompté — jamais le modèle du pipeline.
    """
    projet_id, _ = _projet(request)
    lecture = relire(dictee.texte)
    _poser_cookie(response, projet_id)
    return {"projet_id": projet_id, "brut": lecture.brut, "propose": lecture.propose,
            "alerte": lecture.alerte, "reformule": lecture.reformule}


@app.post("/api/transcription/valider")
def api_transcription_valider(validee: TranscriptionValidee, request: Request,
                              response: Response) -> dict:
    """L'artisan a relu : on journalise ce qu'il a corrigé, puis on traite."""
    projet_id, session = _projet(request)
    texte = valider_transcription(session, validee.propose, validee.texte)
    resultat = traiter_message(session, texte)
    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return {
        "projet_id": projet_id,
        "intent": resultat.intent,
        "messages": resultat.messages_assistant,
        "mentions": resultat.mentions,
        "consommables_suggeres": resultat.consommables_suggeres,
        "cadrages": resultat.cadrages,
        "texte_traite": texte,
        "devis": _serialiser_devis(session),
    }


class CorrectionEntrante(BaseModel):
    index: int
    description: str


@app.post("/api/corriger")
def api_corriger(corr: CorrectionEntrante, request: Request, response: Response) -> dict:
    projet_id, session = _projet(request)
    corriger_ligne(session, corr.index, corr.description)
    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return {"projet_id": projet_id, "devis": _serialiser_devis(session)}


class ArbitrageQuantite(BaseModel):
    index: int
    action: str  # "confirmer" | "abandonner"


@app.post("/api/quantite")
def api_quantite(arb: ArbitrageQuantite, request: Request, response: Response) -> dict:
    """US-11 : l'artisan tranche sur une quantité jugée invraisemblable."""
    projet_id, session = _projet(request)
    if arb.action == "confirmer":
        applique = confirmer_quantite(session, arb.index)
    elif arb.action == "abandonner":
        applique = abandonner_quantite(session, arb.index)
    else:
        raise HTTPException(status_code=422, detail="action attendue : confirmer | abandonner")
    if not applique:
        raise HTTPException(status_code=404, detail="aucune ligne en attente à cet index")
    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return {"projet_id": projet_id, "devis": _serialiser_devis(session)}


@app.post("/api/reset")
def api_reset(request: Request, response: Response) -> dict:
    """Vide le projet courant. Le devis précédent n'est pas archivé : c'est un
    geste explicite de l'artisan, pas une perte accidentelle."""
    projet_id, _ = _projet(request)
    session = REGISTRE.reinitialiser(projet_id)
    _poser_cookie(response, projet_id)
    return {"projet_id": projet_id, "devis": _serialiser_devis(session)}


class DecennaleEntrante(BaseModel):
    assureur: str = ""
    numero_contrat: str = ""
    couverture_geographique: str = ""
    valide_jusqu_au: dt.date | None = None


class ProfilEntrant(BaseModel):
    """Les mentions légales, déclarées par l'artisan — jamais par le modèle."""
    raison_sociale: str = ""
    siret: str = ""
    adresse: str = ""
    rcs: str = ""
    ape_naf: str = ""
    tva_intracommunautaire: str = ""
    regime_tva: RegimeTVA = RegimeTVA.REEL
    decennale: DecennaleEntrante = DecennaleEntrante()
    client_nom: str = ""
    client_adresse_chantier: str = ""
    delai_execution: str = ""


def _serialiser_profil(session: Session) -> dict:
    p, d = session.profil, session.profil.decennale
    return {
        "raison_sociale": p.raison_sociale, "siret": p.siret, "adresse": p.adresse,
        "rcs": p.rcs, "ape_naf": p.ape_naf,
        "tva_intracommunautaire": p.tva_intracommunautaire,
        "regime_tva": str(p.regime_tva),
        "decennale": {
            "assureur": d.assureur, "numero_contrat": d.numero_contrat,
            "couverture_geographique": d.couverture_geographique,
            "valide_jusqu_au": d.valide_jusqu_au.isoformat() if d.valide_jusqu_au else None,
        },
        "decennale_perimee": d.perimee(),
        "client_nom": session.client.nom,
        "client_adresse_chantier": session.client.adresse_chantier,
        "delai_execution": session.delai_execution,
        "mentions_manquantes": champs_manquants(
            session.profil, session.client, session.delai_execution),
    }


@app.get("/api/profil")
def api_profil_lire(request: Request, response: Response) -> dict:
    projet_id, session = _projet(request)
    _poser_cookie(response, projet_id)
    return _serialiser_profil(session)


@app.post("/api/profil")
def api_profil_ecrire(entrant: ProfilEntrant, request: Request,
                       response: Response) -> dict:
    """US-02 — le régime de TVA est un attribut du profil, pas une case par devis."""
    projet_id, session = _projet(request)
    p = session.profil
    p.raison_sociale = entrant.raison_sociale
    p.siret = entrant.siret
    p.adresse = entrant.adresse
    p.rcs = entrant.rcs
    p.ape_naf = entrant.ape_naf
    p.tva_intracommunautaire = entrant.tva_intracommunautaire
    p.regime_tva = entrant.regime_tva
    p.decennale.assureur = entrant.decennale.assureur
    p.decennale.numero_contrat = entrant.decennale.numero_contrat
    p.decennale.couverture_geographique = entrant.decennale.couverture_geographique
    p.decennale.valide_jusqu_au = entrant.decennale.valide_jusqu_au
    session.client = Client(nom=entrant.client_nom,
                            adresse_chantier=entrant.client_adresse_chantier)
    session.delai_execution = entrant.delai_execution
    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return _serialiser_profil(session)


@app.get("/api/export")
def api_export(request: Request) -> Response:
    _, session = _projet(request)
    if not session.structure_validee:
        raise HTTPException(status_code=409, detail={
            "code": "structure_non_validee",
            "message": "Valide d'abord la structure du devis : les prix ne sont "
                       "calculés qu'après.",
            "manquantes": [],
        })
    try:
        contenu = generer_docx(session.devis, session.pieces, session.profil,
                               session.client, session.delai_execution)
    except MentionsIncompletes as exc:
        # 409 et non 400 : la requête est correcte, c'est l'état du projet qui
        # ne permet pas encore un document légalement recevable (US-15, dégradé).
        raise HTTPException(status_code=409, detail={
            "code": "mentions_incompletes",
            "message": "Il manque des mentions obligatoires pour émettre ce devis.",
            "manquantes": exc.manquants,
        }) from exc
    return Response(
        content=contenu,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=devis.docx"},
    )
