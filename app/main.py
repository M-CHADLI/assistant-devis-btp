"""Interface web de la démo — canal web uniquement, un seul interlocuteur :
l'artisan (docs/CADRAGE_MODELE.md §4).

Chaque navigateur travaille sur **son** projet, identifié par un cookie et
persisté sur disque (docs/STORIES.md US-16). Avant, une unique `Session` de
module était partagée par tous les visiteurs et perdue à chaque redémarrage.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.export import generer_docx
from app.persistance import Registre
from app.pipeline import (Session, abandonner_quantite, confirmer_quantite,
                          corriger_ligne, traiter_message)

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
    return {
        "pieces": session.pieces,
        "lignes": [
            {
                "lot_code": l.lot_code,
                "designation": l.produit.designation if l.produit else l.nom_lot,
                "quantite": l.quantite_achat,
                "unite": l.produit.unite_vente if l.produit else "",
                "prix_unitaire_ht": l.prix_unitaire_ht,
                "prix_ht": l.prix_ht,
                "taux_tva": l.taux_tva,
                "origine": l.origine,
            }
            for l in session.devis.lignes
        ],
        "total_ht": session.devis.total_ht,
        "ventilation_tva": session.devis.ventilation_tva,
        "total_tva": session.devis.total_tva,
        "total_ttc": session.devis.total_ttc,
        "acompte_30_pct": session.devis.acompte_30_pct,
        "mentions": sorted(session.devis.mentions),
        # Lignes retenues parce que leur quantité sort des bornes (US-11) :
        # l'artisan doit confirmer ou abandonner avant qu'elles entrent au devis.
        "a_confirmer": [
            {"lot_code": a.lot_code, "dimension_type": a.dimension_type,
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


@app.get("/api/export")
def api_export(request: Request) -> Response:
    _, session = _projet(request)
    contenu = generer_docx(session.devis, session.pieces)
    return Response(
        content=contenu,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=devis.docx"},
    )
