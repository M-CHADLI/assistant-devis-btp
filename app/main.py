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
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.api_schema import (Erreur401, Erreur404, Erreur409, MetriquesSortie,
                            ProfilSortie, ReponseDevis, ReponseRelecture,
                            ReponseTour, ReponseTourTranscrit, SessionOuverte)
from app.authentification import (DUREE_JETON_S, MESSAGE_REFUS, NOM_COOKIE,
                                  Configuration, Refus, phrase_correcte)
from app.export import MentionsIncompletes, generer_docx
from app.observabilite import JOURNAL, agreger
from app.persistance import Registre
from app.pipeline import (Session, abandonner_quantite, confirmer_quantite,
                          corriger_ligne, traiter_message, valider_structure,
                          valider_transcription)
from app.profil import Client, RegimeTVA, champs_manquants
from app.referentiel import REFERENTIEL
from app.transcription import relire

app = FastAPI(
    title="Démo — Assistant chantier BTP vocal",
    version="0.1.0",
    description=(
        "API de l'assistant de devis pour artisans du bâtiment. Le modèle "
        "décrit, le code calcule : aucun prix ne vient du LLM. Tant que "
        "l'artisan n'a pas validé la structure du devis (HITL-2), les réponses "
        "ne portent **aucune clé de prix** — voir `docs/STORIES.md` US-12."
    ),
)

REGISTRE = Registre()

# --------------------------------------------------------------------------
# Authentification (docs/STORIES.md US-23)
# --------------------------------------------------------------------------

AUTH = Configuration()

if AUTH.phrase_engendree:
    # Aucune phrase configurée : on en tire une et on l'affiche ici, une fois.
    # Elle ne va ni au disque, ni au journal, ni au dépôt — et il n'existe aucun
    # « mode sans authentification » à activer par erreur à sa place.
    print("\n  Authentification — phrase de passe de cette session :\n"
          f"      {AUTH.phrase_engendree}\n"
          "  (tirée au hasard car BTP_MOT_DE_PASSE est absent ; elle change à "
          "chaque redémarrage)\n", flush=True)

# Les deux seules portes ouvertes : la page d'accueil, qui doit pouvoir afficher
# le formulaire, et l'ouverture de session elle-même. Tout le reste est fermé —
# y compris `/docs` et `/openapi.json`, qui décrivent l'API.
CHEMINS_LIBRES = frozenset({"/", "/api/session"})


@app.middleware("http")
async def exiger_authentification(request: Request, call_next):
    """Contrôle d'accès **avant** toute recherche de ressource (OWASP A01).

    Un filtre par liste blanche, pas par liste noire : un endpoint ajouté demain
    est protégé sans que personne n'y pense. C'est la propriété qui compte, et
    un test la vérifie route par route."""
    if request.url.path not in CHEMINS_LIBRES:
        try:
            AUTH.verifier(request.cookies.get(NOM_COOKIE))
        except Refus:
            # Message unique : jeton absent, périmé, falsifié ou projet inexistant
            # se ressemblent de l'extérieur — rien ne fuit sur ce qui existe.
            return JSONResponse(status_code=401, content={"detail": MESSAGE_REFUS})
    return await call_next(request)


class OuvertureSession(BaseModel):
    phrase: str


@app.post("/api/session", response_model=SessionOuverte, tags=["Accès"],
          summary="Ouvrir une session avec la phrase de passe",
          responses={401: {"model": Erreur401, "description": "phrase incorrecte"},
                     429: {"model": Erreur401,
                           "description": "trop de tentatives, réessayer plus tard"}})
def api_session(ouverture: OuvertureSession, request: Request,
                response: Response) -> dict:
    """Échange la phrase de passe contre un jeton signé, à durée de vie bornée.

    La phrase n'est comparée qu'à son empreinte scrypt, en temps constant, et
    n'est jamais journalisée (docs/STORIES.md US-23)."""
    origine = request.client.host if request.client else "inconnu"
    if not AUTH.tentative_permise(origine):
        raise HTTPException(status_code=429,
                            detail="trop de tentatives — réessaie dans quelques minutes")
    if not phrase_correcte(ouverture.phrase, AUTH.empreinte):
        AUTH.enregistrer_echec(origine)
        raise HTTPException(status_code=401, detail=MESSAGE_REFUS)
    AUTH.oublier(origine)
    response.set_cookie(NOM_COOKIE, AUTH.emettre(), httponly=True,
                        samesite="strict", max_age=DUREE_JETON_S,
                        secure=request.url.scheme == "https")
    return {"ouverte": True, "duree_s": DUREE_JETON_S}


@app.delete("/api/session", response_model=SessionOuverte, tags=["Accès"],
            summary="Fermer la session")
def api_session_fermer(response: Response) -> dict:
    response.delete_cookie(NOM_COOKIE, httponly=True, samesite="strict")
    return {"ouverte": False, "duree_s": 0}

# Chemin absolu dérivé du paquet : uvicorn doit pouvoir être lancé depuis
# n'importe quel répertoire courant sans casser la page d'accueil.
INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"
METRIQUES_HTML = Path(__file__).resolve().parent / "static" / "metriques.html"

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
            {"horodatage": c.horodatage, "auteur": c.auteur,
             "description": c.description, "origine": c.origine}
            for c in session.corrections
        ],
    }


@app.get("/", response_class=HTMLResponse, summary="Page de l'assistant",
         tags=["Interface"])
def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


@app.get("/metriques", response_class=HTMLResponse, tags=["Interface"],
         summary="Tableau de bord d'exploitation (docs/STORIES.md US-24)")
def page_metriques() -> HTMLResponse:
    """Lit le journal applicatif : reste consultable modèle arrêté."""
    return HTMLResponse(METRIQUES_HTML.read_text(encoding="utf-8"))


@app.get("/api/metriques", response_model=MetriquesSortie, tags=["Exploitation"],
         summary="Métriques du §4.3 agrégées depuis le journal applicatif")
def api_metriques() -> dict:
    return agreger(JOURNAL)


class MessageEntrant(BaseModel):
    texte: str


@app.get("/api/devis", response_model=ReponseDevis, tags=["Devis"],
         summary="État du devis du projet courant")
def api_devis(request: Request, response: Response) -> dict:
    """Resynchronise l'interface avec l'état serveur — utile après un simple
    rechargement de page, sans perdre le devis en cours."""
    projet_id, session = _projet(request)
    _poser_cookie(response, projet_id)
    return {"projet_id": projet_id, "devis": _serialiser_devis(session)}


@app.post("/api/message", response_model=ReponseTour, tags=["Dialogue"],
          summary="Traiter un message de l'artisan (un tour complet)")
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


@app.post("/api/valider-structure", response_model=ReponseDevis, tags=["Devis"],
          summary="HITL-2 — valider la structure, puis chiffrer",
          responses={409: {"model": Erreur409,
                           "description": "structure vide : rien à valider"}})
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
    # La dictée avant remise en forme : c'est l'« entrée d'origine » du triplet
    # exporté au réentraînement (docs/STORIES.md US-25).
    brut: str = ""
    texte: str


@app.post("/api/transcription", response_model=ReponseRelecture, tags=["Dictée"],
          summary="HITL-0 — remettre la dictée en forme, sans rien déclencher")
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


@app.post("/api/transcription/valider", response_model=ReponseTourTranscrit,
          tags=["Dictée"],
          summary="Valider la dictée relue et lancer le traitement")
def api_transcription_valider(validee: TranscriptionValidee, request: Request,
                              response: Response) -> dict:
    """L'artisan a relu : on journalise ce qu'il a corrigé, puis on traite."""
    projet_id, session = _projet(request)
    texte = valider_transcription(session, validee.propose, validee.texte,
                                  brut=validee.brut)
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


@app.post("/api/corriger", response_model=ReponseDevis, tags=["Devis"],
          summary="Corriger une ligne — la correction de l'artisan fait autorité")
def api_corriger(corr: CorrectionEntrante, request: Request, response: Response) -> dict:
    projet_id, session = _projet(request)
    corriger_ligne(session, corr.index, corr.description)
    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return {"projet_id": projet_id, "devis": _serialiser_devis(session)}


class ArbitrageQuantite(BaseModel):
    index: int
    action: str  # "confirmer" | "abandonner"


@app.post("/api/quantite", response_model=ReponseDevis, tags=["Devis"],
          summary="Confirmer ou abandonner une quantité hors bornes (US-11)",
          responses={404: {"model": Erreur404,
                           "description": "aucune ligne en attente à cet index"},
                     422: {"description": "action inconnue : confirmer | abandonner"}})
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


@app.post("/api/reset", response_model=ReponseDevis, tags=["Devis"],
          summary="Vider le projet courant")
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


@app.get("/api/profil", response_model=ProfilSortie, tags=["Profil"],
         summary="Lire les mentions légales déclarées par l'artisan")
def api_profil_lire(request: Request, response: Response) -> dict:
    projet_id, session = _projet(request)
    _poser_cookie(response, projet_id)
    return _serialiser_profil(session)


@app.post("/api/profil", response_model=ProfilSortie, tags=["Profil"],
          summary="Déclarer régime de TVA, décennale et coordonnées (US-02)")
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


@app.get("/api/export", tags=["Devis"],
         summary="Exporter le devis en .docx, mentions obligatoires comprises",
         response_class=Response,
         responses={200: {"content": {"application/vnd.openxmlformats-officedocument"
                                      ".wordprocessingml.document": {}},
                          "description": "le devis au format .docx"},
                    409: {"model": Erreur409,
                          "description": "structure non validée, ou mentions "
                                         "obligatoires incomplètes"}})
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
