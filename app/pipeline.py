"""Orchestrateur — enchaîne les étapes de docs/DISPOSITIF_AGENT.md §1.

Le modèle décrit (clarifie, décompose, quantifie, propose des consommables) ;
le code calcule (app.devis) et contrôle (schéma, lot_code connu, bornes). Toute
correction de l'artisan est journalisée comme signal qualité (§1.4, §5.2).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.devis import Devis, LotInconnu, ajouter_consommables, ajouter_ligne, consommables_par_defaut
from app.llm import ModeleInjoignable, SortieModeleInvalide, appeler_modele
from app.profil import Client, ProfilArtisan
from app.referentiel import REFERENTIEL, MENTIONS, bornes, est_plausible
from app.schema import PayloadClarification, PayloadConsommables, PayloadDevis, PayloadReponse

LONGUEUR_MAX_ENTREE = 2000

# Budget d'appels modèle pour UN message utilisateur : 1 essai + 1 reprise.
# Le pipeline est le seul à reprendre — app.llm n'a plus de boucle interne, sans
# quoi les deux se composaient et un message coûtait jusqu'à 4 appels
# (docs/DISPOSITIF_AGENT.md §1.3 et §4.3, objectif de latence p95 < 30 s).
MAX_APPELS_MODELE = 2

# HITL-1 : au-delà de trois tours de clarification, on arrête d'interroger et
# on pose des hypothèses par défaut *explicites* (docs/DISPOSITIF_AGENT.md §1.4,
# docs/STORIES.md US-07). Un agent qui questionne sans fin est un agent qui ne
# sait pas décider — sur un chantier, c'est intenable.
MAX_TOURS_CLARIFICATION = 3

HYPOTHESES_PAR_DEFAUT = [
    "logement achevé depuis plus de deux ans, donc TVA à 10 %",
    "hauteur sous plafond de 2,50 m",
    "supports sains, sans reprise lourde",
    "les surfaces que tu m'as données sont des surfaces à traiter, pas au sol",
]


@dataclass
class Escalade:
    """Trace d'un échec de tour. Le motif est un code stable, exploitable en
    agrégat (docs/DISPOSITIF_AGENT.md §5.2) ; le détail sert au débogage."""
    horodatage: str
    motif: str  # "entree_rejetee" | "json_invalide" | "schema_invalide"
                # | "lot_inconnu" | "intent_inconnu" | "modele_injoignable"
    detail: str


@dataclass
class Correction:
    horodatage: str
    auteur: str  # "artisan"
    description: str


@dataclass
class LigneEnAttente:
    """Ligne mise en attente parce que sa quantité sort des bornes (US-11).

    On ne rejette pas : l'artisan fait autorité, il peut confirmer."""
    lot_code: str
    dimension_type: str
    dimension_valeur: float
    borne_min: float
    borne_max: float


@dataclass
class Session:
    historique: list[dict] = field(default_factory=list)
    devis: Devis = field(default_factory=Devis)
    pieces: list[str] = field(default_factory=list)
    lots_presents: list[str] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)
    escalades: list[Escalade] = field(default_factory=list)
    tours_clarification: int = 0
    a_confirmer: list[LigneEnAttente] = field(default_factory=list)
    # Mentions légales du devis : déclarées une fois, reportées sur chaque
    # export (docs/STORIES.md US-02 et US-15). Le modèle n'y touche jamais.
    profil: ProfilArtisan = field(default_factory=ProfilArtisan)
    client: Client = field(default_factory=Client)
    delai_execution: str = ""


@dataclass
class ResultatTour:
    intent: str
    messages_assistant: list[str]
    mentions: list[str]
    devis: Devis
    consommables_suggeres: dict[str, list[str]]


def _valider_entree(texte: str) -> str | None:
    """Contrôle d'entrée (docs/DISPOSITIF_AGENT.md §3.1). Renvoie un message
    de rejet si l'entrée est irrecevable, None si elle est acceptée."""
    if not texte or not texte.strip():
        return "Message vide — décris ton chantier pour que je puisse t'aider."
    if len(texte) > LONGUEUR_MAX_ENTREE:
        return "Message trop long — peux-tu le découper en plusieurs messages ?"
    return None


def _router(session: Session, sortie: dict) -> tuple[str, list[str], list[str], dict[str, list[str]]]:
    """Route une sortie modèle déjà parsée en JSON vers le bon traitement.

    Peut lever ValidationError ou LotInconnu — l'appelant décide de reprendre
    ou d'escalader (docs/DISPOSITIF_AGENT.md §1.3 : « Reprise, puis escalade »).
    """
    intent = sortie.get("intent")
    payload = sortie.get("payload", {})
    mention = sortie.get("mention")
    mentions: list[str] = [mention] if mention else []
    messages: list[str] = []
    consommables_suggeres: dict[str, list[str]] = {}

    if intent == "clarification":
        p = PayloadClarification.model_validate(payload)
        session.tours_clarification += 1
        if session.tours_clarification > MAX_TOURS_CLARIFICATION:
            # On a assez questionné : on annonce ce qu'on suppose, et on avance.
            messages.append(
                "Je ne te pose plus de questions. Je pars sur ces hypothèses, "
                "dis-moi si l'une est fausse :"
            )
            messages.extend(f"— {h}" for h in HYPOTHESES_PAR_DEFAUT)
            intent = "hypotheses"
        else:
            messages.extend(p.questions)

    elif intent in ("devis", "lots", "quantitatif"):
        p = PayloadDevis.model_validate(payload)
        for ligne in p.lignes:
            if ligne.lot_code not in REFERENTIEL:
                raise LotInconnu(f"lot_code inconnu : {ligne.lot_code!r}")
        session.pieces.extend(x for x in p.pieces if x not in session.pieces)
        deja_presentes = {
            (l.lot_code, l.dimension_type, l.dimension_valeur) for l in session.devis.lignes
        }
        lignes_nouvelles = 0
        for ligne in p.lignes:
            cle = (ligne.lot_code, ligne.dimension.type, ligne.dimension.valeur)
            if cle in deja_presentes:
                continue  # reconfirmation orale identique — idempotent, pas un doublon
            if not est_plausible(ligne.lot_code, ligne.dimension.type, ligne.dimension.valeur):
                mini, maxi = bornes(ligne.lot_code, ligne.dimension.type)
                session.a_confirmer.append(LigneEnAttente(
                    ligne.lot_code, ligne.dimension.type, ligne.dimension.valeur, mini, maxi))
                messages.append(
                    f"{ligne.dimension.valeur} {ligne.dimension.type} pour "
                    f"« {REFERENTIEL[ligne.lot_code].nom} », c'est hors de ce que je vois "
                    f"habituellement ({mini} à {maxi}). Je ne l'ajoute pas tant que tu ne "
                    "me l'as pas confirmé — dictée mal comprise, ou chantier vraiment de "
                    "cette taille ?"
                )
                continue
            ajouter_ligne(session.devis, ligne.lot_code, ligne.dimension.type, ligne.dimension.valeur)
            deja_presentes.add(cle)
            lignes_nouvelles += 1
            if ligne.lot_code not in session.lots_presents:
                session.lots_presents.append(ligne.lot_code)
            if ligne.lot_code in MENTIONS and MENTIONS[ligne.lot_code] not in mentions:
                mentions.append(MENTIONS[ligne.lot_code])
        if lignes_nouvelles:
            messages.append(
                f"{lignes_nouvelles} ligne(s) ajoutée(s) au devis "
                f"(total HT provisoire : {session.devis.total_ht} €)."
            )
        elif p.lignes:
            messages.append("Déjà pris en compte dans le devis en cours.")
        consommables_suggeres = consommables_par_defaut(session.lots_presents)

    elif intent == "consommables":
        p = PayloadConsommables.model_validate(payload)
        if p.lot_code not in REFERENTIEL:
            raise LotInconnu(f"lot_code inconnu : {p.lot_code!r}")
        ajouter_consommables(session.devis, p.lot_code, p.items)
        messages.append(f"Consommables ajoutés pour {REFERENTIEL[p.lot_code].nom} : "
                         + ", ".join(p.items))

    elif intent == "reponse":
        p = PayloadReponse.model_validate(payload)
        messages.append(p.texte)

    else:
        raise ValueError(f"intent inconnu du routeur : {intent!r}")

    if mention == "forte":
        messages.append("⚠️ Ce point relève d'un domaine réglementé — je t'informe, "
                         "mais fais valider par un professionnel avant travaux.")
    elif mention == "simple":
        messages.append("Point de vigilance : à vérifier avant de te lancer.")

    return intent, messages, mentions, consommables_suggeres


def _journaliser_escalade(session: Session, motif: str, detail: object) -> None:
    """Toute sortie non retenue laisse une trace (docs/DISPOSITIF_AGENT.md §2.4).

    Sans motif explicite, on sait qu'un tour a échoué mais pas *pourquoi* — donc
    on ne peut pas décider quoi corriger dans le dataset."""
    session.escalades.append(Escalade(
        horodatage=dt.datetime.now().isoformat(timespec="seconds"),
        motif=motif,
        detail=str(detail)[:500],
    ))


def _motif(exc: Exception) -> str:
    if isinstance(exc, LotInconnu):
        return "lot_inconnu"
    if isinstance(exc, ValidationError):
        return "schema_invalide"
    return "intent_inconnu"


MESSAGE_ESCALADE = (
    "Je n'arrive pas à structurer ta demande de façon fiable après une reprise. "
    "Peux-tu reformuler plus simplement, ou un conseiller humain peut prendre le relais."
)
MESSAGE_INDISPONIBLE = (
    "Le moteur d'analyse ne répond pas pour l'instant. Ton devis en cours est "
    "conservé — réessaie dans un instant, ou reprends la saisie à la main."
)


def traiter_message(session: Session, texte_utilisateur: str) -> ResultatTour:
    rejet = _valider_entree(texte_utilisateur)
    if rejet:
        _journaliser_escalade(session, "entree_rejetee", rejet)
        return ResultatTour("rejet", [rejet], [], session.devis, {})

    message_suivant = texte_utilisateur
    for tentative in range(MAX_APPELS_MODELE):
        derniere_chance = tentative == MAX_APPELS_MODELE - 1

        try:
            sortie = appeler_modele(session.historique, message_suivant)
        except ModeleInjoignable as exc:
            # Une reprise n'a aucune chance d'aboutir : on sort tout de suite.
            _journaliser_escalade(session, "modele_injoignable", exc)
            return ResultatTour("indisponible", [MESSAGE_INDISPONIBLE], [], session.devis, {})
        except SortieModeleInvalide as exc:
            _journaliser_escalade(session, "json_invalide", exc)
            if derniere_chance:
                break
            message_suivant = (
                "Ta réponse n'était pas un JSON valide. Réponds uniquement avec "
                "l'objet JSON attendu, sans aucun texte autour."
            )
            continue

        session.historique.append({"role": "user", "content": message_suivant})
        session.historique.append({"role": "assistant", "content": str(sortie)})
        session.historique = session.historique[-10:]  # mémoire de tour glissante (§2.2)

        try:
            intent, messages, mentions, consommables_suggeres = _router(session, sortie)
            return ResultatTour(intent, messages, mentions, session.devis, consommables_suggeres)
        except (ValidationError, LotInconnu, ValueError) as exc:
            _journaliser_escalade(session, _motif(exc), exc)
            if derniere_chance:
                break
            message_suivant = (
                "Ta réponse précédente ne respectait pas le schéma attendu "
                f"({exc}). Corrige-la et réponds uniquement avec un JSON conforme."
            )

    return ResultatTour("escalade", [MESSAGE_ESCALADE], [], session.devis, {})


def valider_transcription(session: Session, propose: str, corrige: str) -> str:
    """HITL-0 : l'artisan relit sa dictée et la valide (docs/STORIES.md US-05).

    Rien ne s'exécute avant cet appel — c'est ici que le pipeline démarre. Si
    l'artisan a corrigé le texte, l'écart est journalisé au même titre qu'une
    correction de devis : c'est le **premier point de capture du signal qualité**
    (docs/DISPOSITIF_AGENT.md §5.2), celui qui dit ce que la chaîne dictée +
    reformulation a mal entendu.
    """
    retenu = (corrige or "").strip()
    if retenu != (propose or "").strip():
        session.corrections.append(Correction(
            horodatage=dt.datetime.now().isoformat(timespec="seconds"),
            auteur="artisan",
            description=(f"transcription corrigée avant traitement : "
                         f"« {(propose or '').strip()[:200]} » → « {retenu[:200]} »"),
        ))
    return retenu


def confirmer_quantite(session: Session, index: int) -> bool:
    """L'artisan confirme une quantité hors bornes. Il fait autorité (CLAUDE.md) :
    on l'applique sans discuter, et on garde la trace que la borne a été franchie."""
    if not (0 <= index < len(session.a_confirmer)):
        return False
    attente = session.a_confirmer.pop(index)
    ajouter_ligne(session.devis, attente.lot_code, attente.dimension_type,
                  attente.dimension_valeur)
    if attente.lot_code not in session.lots_presents:
        session.lots_presents.append(attente.lot_code)
    if attente.lot_code in MENTIONS:
        session.devis.mentions.add(MENTIONS[attente.lot_code])
    session.corrections.append(Correction(
        horodatage=dt.datetime.now().isoformat(timespec="seconds"),
        auteur="artisan",
        description=(f"quantité hors bornes confirmée : {attente.dimension_valeur} "
                     f"{attente.dimension_type} sur {attente.lot_code} "
                     f"(bornes {attente.borne_min}–{attente.borne_max})"),
    ))
    return True


def abandonner_quantite(session: Session, index: int) -> bool:
    """L'artisan reconnaît une erreur de dictée : on jette la ligne en attente."""
    if not (0 <= index < len(session.a_confirmer)):
        return False
    session.a_confirmer.pop(index)
    return True


def corriger_ligne(session: Session, index_ligne: int, description: str) -> None:
    """HITL-2 : l'artisan corrige. Appliqué sans discussion, journalisé (§5.2)."""
    if 0 <= index_ligne < len(session.devis.lignes):
        session.devis.lignes.pop(index_ligne)
    session.corrections.append(
        Correction(horodatage=dt.datetime.now().isoformat(timespec="seconds"),
                   auteur="artisan", description=description)
    )
