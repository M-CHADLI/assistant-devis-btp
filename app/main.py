"""Interface web de la démo — canal web uniquement, un seul interlocuteur :
l'artisan (docs/CADRAGE_MODELE.md §4).

Chaque navigateur travaille sur **son** projet, identifié par un cookie et
persisté sur disque (docs/STORIES.md US-16). Avant, une unique `Session` de
module était partagée par tous les visiteurs et perdue à chaque redémarrage.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.api_schema import (DepotGabaritSortie, Erreur401, Erreur404,
                            Erreur409, Erreur422Gabarit, Erreur422Siret,
                            Erreur503, FamilleIncomplete, FamilleSynthese,
                            MetriquesSortie, ProduitCatalogue, ProfilSortie,
                            RechercheSiretSortie, ReponseDevis,
                            ReponseDuplication,
                            ReponseRelecture, ReponseTour, ReponseTourTranscrit,
                            SessionOuverte, SourceDonnees)
from app import catalogue_base
from app.authentification import (DUREE_JETON_S, MESSAGE_REFUS, NOM_COOKIE,
                                  Configuration, Refus, phrase_correcte)
from app.export import MentionsIncompletes, generer_docx
from app.observabilite import JOURNAL, agreger
from app.persistance import Registre
from app.pipeline import (Session, abandonner_quantite, confirmer_quantite,
                          corriger_ligne, traiter_message, valider_structure,
                          valider_transcription)
from app.annuaire import (Indisponible, SiretInvalide, normaliser_siret,
                          rechercher)
from app.gabarit import (DepotInvalide, Gabarit, PasUnDevis)
from app.gabarit import Indisponible as GabaritIndisponible
from app.gabarit import extraire as extraire_gabarit
from app.profil import (CHAMPS_PREREMPLISSABLES, ORIGINE_ANNUAIRE,
                        ORIGINE_ARTISAN, Client, RegimeTVA,
                        champs_manquants)
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
            ligne["remise_pct"] = round(
                (l.produit.promo_pct if l.produit else 0.0) * 100, 2)
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
        # Lignes retenues avant d'entrer au devis : quantité hors bornes
        # (US-11) ou contradiction entre deux dictées (US-06). Dans les deux cas
        # l'artisan tranche ; `motif` dit laquelle des deux questions lui poser.
        "a_confirmer": [
            {"lot_code": a.lot_code,
             # Le nom métier, pas le code : l'artisan arbitre sur « Peinture de
             # finition », pas sur PEINT_FINITION.
             "lot_nom": REFERENTIEL[a.lot_code].nom if a.lot_code in REFERENTIEL else a.lot_code,
             "dimension_type": a.dimension_type,
             "dimension_valeur": a.dimension_valeur,
             "borne_min": a.borne_min, "borne_max": a.borne_max,
             "motif": a.motif, "valeur_existante": a.valeur_existante}
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


@app.post("/api/projet/dupliquer", response_model=ReponseDuplication,
          tags=["Devis"],
          summary="Repartir de ce devis pour un chantier voisin")
def api_dupliquer(request: Request, response: Response) -> dict:
    """Ouvre un nouveau projet à partir du courant (US-17).

    La copie reprend la structure et laisse les prix : le catalogue est
    volatil, la structure ne l'est pas. Elle repart donc non chiffrée et à
    revalider — les surfaces vont changer, c'est le but de la duplication.

    Corrections et escalades ne suivent pas : elles appartiennent à
    l'historique de l'autre chantier.
    """
    source_id, _ = _projet(request)
    projet_id, session = REGISTRE.dupliquer(source_id)
    JOURNAL.enregistrer("projet_duplique", lignes=len(session.devis.lignes))
    # Le navigateur bascule sur le nouveau projet : c'est celui qu'on édite.
    _poser_cookie(response, projet_id)
    return {
        "projet_id": projet_id,
        "devis": _serialiser_devis(session),
        "numero_devis": session.numero_devis,
        "date_emission": session.date_emission,
        "source_projet_id": source_id,
        "repris": ["vos mentions légales", "le client et l'adresse du chantier",
                   "le délai d'exécution", "les pièces",
                   "les lots et les quantités"],
        "non_repris": ["les prix, à recalculer sur le catalogue du jour",
                       "la validation de structure, à refaire",
                       "les corrections et les escalades du chantier d'origine",
                       "l'historique des dictées"],
    }


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
        "origines": {c: p.origine_de(c) for c in CHAMPS_PREREMPLISSABLES},
        "gabarit": _serialiser_gabarit(p.gabarit),
    }


def _serialiser_gabarit(gabarit: Gabarit) -> dict:
    """Ce que le front a le droit de savoir de la mise en page.

    Les libellés sont calculés par `Gabarit.libelle`, donc pris dans le
    vocabulaire d'`app/gabarit.py` : rien du document déposé ne remonte au
    navigateur, pas plus qu'il n'est descendu au disque.
    """
    ordre = gabarit.ordre()
    return {
        "par_defaut": gabarit.par_defaut,
        "blocs": list(ordre),
        "libelles": {bloc: gabarit.libelle(bloc) for bloc in ordre},
    }


# --------------------------------------------------------------------------
# Jeu de données catalogue (docs/CHAINE_DONNEES.md, référentiel C5)
# --------------------------------------------------------------------------
#
# Ces cinq points de terminaison exposent le jeu de données produit par la
# chaîne, en lecture seule et derrière la même authentification que le reste.
# Ils ne servent pas le moteur de devis — celui-ci garde son catalogue de
# démonstration — mais mettent le jeu à disposition d'un tiers, ce qui est
# exactement ce que le jeu de données est fait pour.
#
# La connexion est ouverte par requête plutôt que gardée en module : SQLite
# n'aime pas qu'une connexion traverse des fils d'exécution, et FastAPI en
# utilise plusieurs pour les fonctions synchrones.


def _base():
    """Ouvre la base, ou refuse proprement si elle n'a pas été construite."""
    try:
        return catalogue_base.ouvrir()
    except FileNotFoundError as absente:
        raise HTTPException(status_code=503, detail=str(absente)) from absente


@app.get("/api/catalogue/sources", response_model=list[SourceDonnees],
         tags=["Jeu de données"],
         summary="Provenance et licence de chaque lot de données",
         responses={503: {"model": Erreur503, "description": "base non construite"}})
def api_catalogue_sources() -> list[dict]:
    """La traçabilité du jeu : trois sources, trois licences.

    Exposée en premier et sans condition : un jeu de données dont on ignore
    la provenance ne peut être réutilisé par personne."""
    cx = _base()
    try:
        return catalogue_base.tracabilite(cx)
    finally:
        cx.close()


@app.get("/api/catalogue/familles", response_model=list[FamilleSynthese],
         tags=["Jeu de données"],
         summary="Familles de produits, effectifs et fourchettes de prix",
         responses={503: {"model": Erreur503, "description": "base non construite"}})
def api_catalogue_familles() -> list[dict]:
    """Une ligne par famille, y compris celles qui n'ont aucun produit — sinon
    un trou de catalogue resterait invisible."""
    cx = _base()
    try:
        return catalogue_base.synthese_par_famille(cx)
    finally:
        cx.close()


@app.get("/api/catalogue/familles/{code}/produits",
         response_model=list[ProduitCatalogue], tags=["Jeu de données"],
         summary="Les produits d'une famille, du moins cher au plus cher",
         responses={404: {"model": Erreur404, "description": "famille inconnue"},
                    503: {"model": Erreur503, "description": "base non construite"}})
def api_catalogue_produits(code: str) -> list[dict]:
    """Classé sur le prix **remisé**, jamais sur le prix affiché.

    Une famille inconnue est un 404, pas une liste vide : le client doit
    pouvoir distinguer « cette famille n'existe pas » de « elle est vide »."""
    cx = _base()
    try:
        connues = {f["code"] for f in catalogue_base.synthese_par_famille(cx)}
        if code not in connues:
            raise HTTPException(status_code=404, detail=f"famille inconnue : {code}")
        return catalogue_base.produits_de_famille(cx, code)
    finally:
        cx.close()


@app.get("/api/catalogue/produits/{reference}", response_model=ProduitCatalogue,
         tags=["Jeu de données"], summary="Un produit par sa référence",
         responses={404: {"model": Erreur404, "description": "référence inconnue"},
                    503: {"model": Erreur503, "description": "base non construite"}})
def api_catalogue_produit(reference: str) -> dict:
    cx = _base()
    try:
        produit = catalogue_base.produit(cx, reference)
        if produit is None:
            raise HTTPException(status_code=404,
                                detail=f"référence inconnue : {reference}")
        return produit
    finally:
        cx.close()


@app.get("/api/catalogue/manques", response_model=list[FamilleIncomplete],
         tags=["Jeu de données"],
         summary="Ce que l'enrichissement n'a pas su remplir, et pourquoi",
         responses={503: {"model": Erreur503, "description": "base non construite"}})
def api_catalogue_manques() -> list[dict]:
    """Le point d'honnêteté du jeu de données.

    Aucune source publique ne donne la masse volumique d'une peinture, et la
    Base Carbone ne publie les produits céramiques qu'en ratios monétaires.
    Ces trous sont exposés ici, avec leur motif, plutôt que comblés par des
    valeurs plausibles qu'on ne pourrait plus distinguer de mesures."""
    cx = _base()
    try:
        familles = catalogue_base.familles_incompletes(cx)
        for famille in familles:      # SQLite rend les booléens en entiers
            famille["facteur_manquant"] = bool(famille["facteur_manquant"])
            famille["densite_manquante"] = bool(famille["densite_manquante"])
        return familles
    finally:
        cx.close()


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
    avant = {c: getattr(p, c) for c in CHAMPS_PREREMPLISSABLES}
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
    # Ce que l'artisan enregistre lui-même lui appartient — sauf s'il a laissé
    # tel quel ce que l'annuaire avait proposé : dans ce cas la valeur garde son
    # origine, et une nouvelle recherche pourra la corriger. Accepter sans
    # relire n'est pas décider.
    for champ in CHAMPS_PREREMPLISSABLES:
        valeur = getattr(p, champ)
        if p.origine_de(champ) == ORIGINE_ANNUAIRE and valeur == avant.get(champ):
            continue
        p.origines[champ] = ORIGINE_ARTISAN
    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return _serialiser_profil(session)


class RechercheSiret(BaseModel):
    siret: str = ""


@app.post("/api/profil/siret", response_model=RechercheSiretSortie,
          tags=["Profil"],
          responses={422: {"model": Erreur422Siret,
                           "description": "SIRET mal formé, aucun appel émis"}},
          summary="Pré-remplir les mentions légales à partir du SIRET (US-01)")
def api_profil_siret(entrant: RechercheSiret, request: Request,
                     response: Response) -> dict:
    """US-01 — ce n'est pas une brique d'IA : une clé de contrôle et un appel HTTP.

    Deux règles gouvernent cette route, et elles sont dans cet ordre :

    1. **Un SIRET mal formé ne coûte pas un appel réseau.** La validation est
       locale et lève un 422 avant que quoi que ce soit ne sorte de la machine.
    2. **L'indisponibilité n'est pas une erreur.** Clé absente, annuaire muet,
       SIRET inconnu : la réponse reste un 200 qui bascule en saisie manuelle
       et dit pourquoi. Rendre un 5xx ici, ce serait faire échouer une
       inscription parce qu'un tiers est en panne.
    """
    projet_id, session = _projet(request)
    try:
        siret = normaliser_siret(entrant.siret)
    except SiretInvalide as erreur:
        raise HTTPException(status_code=422,
                            detail=str(erreur)) from None

    resultat = rechercher(siret)
    profil = session.profil

    if isinstance(resultat, Indisponible):
        # Le SIRET, lui, est valide et vient d'être saisi : le retenir évite de
        # le faire retaper dans le formulaire manuel.
        profil.siret = siret
        profil.origines["siret"] = ORIGINE_ARTISAN
        REGISTRE.enregistrer(projet_id, session)
        _poser_cookie(response, projet_id)
        return {"origine": "saisie_manuelle", "motif": resultat.motif,
                "explication": resultat.explication,
                "champs": {"siret": siret}, "champs_conserves": [],
                "profil": _serialiser_profil(session)}

    proposes = resultat.champs()
    conserves: list[str] = []
    for champ, valeur in proposes.items():
        # Le SIRET n'est pas pré-rempli : c'est l'artisan qui vient de le
        # taper. Le faire passer pour une donnée d'annuaire le rendrait
        # écrasable par une recherche suivante, ce qui n'a aucun sens.
        if champ == "siret":
            continue
        if profil.fait_autorite(champ):
            conserves.append(champ)
            continue
        if not valeur:
            continue
        setattr(profil, champ, valeur)
        profil.origines[champ] = ORIGINE_ANNUAIRE
    profil.siret = siret
    profil.origines["siret"] = ORIGINE_ARTISAN

    manquants = [c for c in CHAMPS_PREREMPLISSABLES
                 if not getattr(profil, c).strip()]
    explication = (
        "Vos informations légales ont été récupérées. Relisez-les : ce que "
        "vous corrigez fait autorité.")
    if manquants:
        explication += (
            f" L'annuaire n'a pas renseigné {len(manquants)} champ"
            f"{'s' if len(manquants) > 1 else ''} — complétez-le"
            f"{'s' if len(manquants) > 1 else ''} à la main.")
    if conserves:
        explication += (
            f" {len(conserves)} champ{'s' if len(conserves) > 1 else ''} que "
            f"vous aviez saisi{'s' if len(conserves) > 1 else ''} "
            f"{'ont' if len(conserves) > 1 else 'a'} été conservé"
            f"{'s' if len(conserves) > 1 else ''}.")

    REGISTRE.enregistrer(projet_id, session)
    _poser_cookie(response, projet_id)
    return {"origine": "annuaire", "motif": None, "explication": explication,
            "champs": proposes, "champs_conserves": conserves,
            "profil": _serialiser_profil(session)}


@app.post("/api/profil/gabarit", response_model=DepotGabaritSortie,
          tags=["Profil"],
          responses={422: {"model": Erreur422Gabarit,
                           "description": "Dépôt refusé, aucun octet n'est "
                                          "sorti de la machine"}},
          summary="Reprendre la mise en page d'un ancien devis (US-03)")
async def api_profil_gabarit_deposer(request: Request, response: Response,
                                     fichier: UploadFile = File(...)) -> dict:
    """Le fichier part chez un service d'OCR, jamais au modèle.

    Trois issues, et **aucune n'est un échec de l'application** : un gabarit,
    un motif de repli sur la mise en page par défaut, ou un 422 quand le
    dépôt se refuse sans même sortir de la machine.
    """
    projet_id, session = _projet(request)
    octets = await fichier.read()
    try:
        resultat = extraire_gabarit(octets)
    except DepotInvalide as exc:
        # 422 et non 400 : la requête est bien formée, c'est son contenu qui
        # ne peut pas être traité. Rien n'a été transmis à un tiers.
        JOURNAL.enregistrer("gabarit_refuse", projet=projet_id, motif="depot")
        raise HTTPException(status_code=422, detail={
            "detail": str(exc), "champ": "fichier"}) from exc
    except PasUnDevis as exc:
        # 200 : le document a bien été lu, il n'est simplement pas un devis.
        # Répondre une erreur ferait croire à une panne du produit.
        JOURNAL.enregistrer("gabarit_refuse", projet=projet_id,
                            motif="pas_un_devis")
        _poser_cookie(response, projet_id)
        return {"origine": "defaut", "motif": "pas_un_devis",
                "explication": exc.explication,
                "gabarit": _serialiser_gabarit(session.profil.gabarit)}

    if isinstance(resultat, GabaritIndisponible):
        # Le motif seul est journalisé : ni le nom du fichier, ni son contenu,
        # ni la clé. Un journal qui porterait le nom du client d'un ancien
        # devis serait un traitement de données personnelles non déclaré.
        JOURNAL.enregistrer("gabarit_indisponible", projet=projet_id,
                            motif=resultat.motif)
        _poser_cookie(response, projet_id)
        return {"origine": "defaut", "motif": resultat.motif,
                "explication": resultat.explication,
                "gabarit": _serialiser_gabarit(session.profil.gabarit)}

    session.profil.gabarit = resultat
    REGISTRE.enregistrer(projet_id, session)
    JOURNAL.enregistrer("gabarit_retenu", projet=projet_id,
                        blocs=len(resultat.blocs))
    _poser_cookie(response, projet_id)
    titres = ", ".join(resultat.libelle(b) for b in resultat.blocs)
    return {
        "origine": "devis_depose", "motif": None,
        "explication": (
            f"Mise en page reprise de votre devis : {titres}. Les sections "
            f"que votre devis ne portait pas restent ajoutées à la fin — un "
            f"devis amputé d'une mention obligatoire n'est plus opposable. "
            f"Vous pouvez revenir à la mise en page par défaut à tout moment."),
        "gabarit": _serialiser_gabarit(resultat),
    }


@app.delete("/api/profil/gabarit", response_model=DepotGabaritSortie,
            tags=["Profil"],
            summary="Revenir à la mise en page par défaut (US-03)")
def api_profil_gabarit_oublier(request: Request, response: Response) -> dict:
    """La mémoire utilisateur est révocable (`docs/DISPOSITIF_AGENT.md` §2.2).

    Révoquer réussit même s'il n'y avait rien à révoquer : demander l'oubli et
    s'entendre répondre 404 serait une réponse absurde à une demande légitime.
    """
    projet_id, session = _projet(request)
    session.profil.gabarit = Gabarit()
    REGISTRE.enregistrer(projet_id, session)
    JOURNAL.enregistrer("gabarit_oublie", projet=projet_id)
    _poser_cookie(response, projet_id)
    return {
        "origine": "defaut", "motif": None,
        "explication": "Vos devis reprennent la mise en page par défaut, "
                       "qui est complète et conforme.",
        "gabarit": _serialiser_gabarit(session.profil.gabarit),
    }


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
        contenu = generer_docx(
            session.devis, session.pieces, session.profil, session.client,
            session.delai_execution,
            # L'identité est celle du projet, fixée à son ouverture : un devis
            # réexporté doit être le même document (US-17).
            aujourd_hui=(dt.date.fromisoformat(session.date_emission)
                         if session.date_emission else None),
            gabarit=session.profil.gabarit,
            numero_devis=session.numero_devis)
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
