"""Orchestrateur — enchaîne les étapes de docs/DISPOSITIF_AGENT.md §1.

Le modèle décrit (clarifie, décompose, quantifie, propose des consommables) ;
le code calcule (app.devis) et contrôle (schéma, lot_code connu, bornes). Toute
correction de l'artisan est journalisée comme signal qualité (§1.4, §5.2).
"""
from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.devis import (Devis, LotInconnu, ajouter_consommables, ajouter_ligne,
                       chiffrer, consommables_par_defaut)
from app.garde_fous import (MESSAGE_HUMAIN, MESSAGE_INJECTION, demande_un_humain,
                            detecter_hors_perimetre, detecter_injection,
                            message_hors_perimetre, neutraliser,
                            reste_du_chantier)
from app.llm import MODEL_NAME, ModeleInjoignable, SortieModeleInvalide, appeler_modele
from app.observabilite import JOURNAL
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
                # | "injection_neutralisee" | "hors_perimetre"
    detail: str


@dataclass
class Correction:
    """Une correction d'artisan, gardée sous une forme réutilisable (US-25).

    `description` reste le texte lisible à l'écran ; le triplet
    `entree` / `sortie_modele` / `corrige` est ce qui fait d'une correction un
    candidat d'entraînement (docs/DISPOSITIF_AGENT.md §5.2). Les trois champs
    sont optionnels parce que les projets écrits avant la version 4 du format
    n'en ont pas : `app.boucle_qualite` les compte comme incomplets plutôt que
    de les exporter amputés."""
    horodatage: str
    auteur: str  # "artisan"
    description: str
    origine: str = ""  # "transcription" | "quantite_hors_bornes" | "ligne_devis"
    entree: str = ""  # ce que l'artisan a fourni
    sortie_modele: str = ""  # ce que la chaîne a produit
    corrige: str = ""  # ce que l'artisan a retenu


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
    # HITL-2 (docs/STORIES.md US-12) : tant que l'artisan n'a pas validé la
    # structure, aucun prix n'est calculé — donc aucun ne peut fuiter vers le
    # navigateur. On valide ce qui est stable avant d'y accrocher ce qui est
    # volatil (docs/DISPOSITIF_AGENT.md §1.4).
    structure_validee: bool = False
    # Compteur de reprises du dernier tour — sert au journal (§4.3), pas à la
    # logique métier : il n'est donc pas persisté.
    reprises_du_tour: int = 0


@dataclass
class ResultatTour:
    intent: str
    messages_assistant: list[str]
    mentions: list[str]
    devis: Devis
    consommables_suggeres: dict[str, list[str]]
    # Messages de garde-fou (périmètre, injection) : ils sont déjà en tête de
    # messages_assistant, listés à part pour que l'interface les annonce en
    # role="alert" sans avoir à reconnaître leur texte (docs/STORIES.md US-20).
    cadrages: list[str] = field(default_factory=list)


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
            ajouter_ligne(session.devis, ligne.lot_code, ligne.dimension.type,
                          ligne.dimension.valeur,
                          chiffrer_maintenant=session.structure_validee)
            deja_presentes.add(cle)
            lignes_nouvelles += 1
            if ligne.lot_code not in session.lots_presents:
                session.lots_presents.append(ligne.lot_code)
            if ligne.lot_code in MENTIONS and MENTIONS[ligne.lot_code] not in mentions:
                mentions.append(MENTIONS[ligne.lot_code])
        if lignes_nouvelles and session.structure_validee:
            messages.append(
                f"{lignes_nouvelles} ligne(s) ajoutée(s) au devis "
                f"(total HT provisoire : {session.devis.total_ht} €)."
            )
        elif lignes_nouvelles:
            # Avant HITL-2, on ne dit pas de montant — pas même « provisoire ».
            messages.append(
                f"{lignes_nouvelles} ligne(s) ajoutée(s) à la structure du devis. "
                "Relis les lots et les quantités : le chiffrage viendra après ta "
                "validation."
            )
        elif p.lignes:
            messages.append("Déjà pris en compte dans le devis en cours.")
        consommables_suggeres = consommables_par_defaut(session.lots_presents)

    elif intent == "consommables":
        p = PayloadConsommables.model_validate(payload)
        if p.lot_code not in REFERENTIEL:
            raise LotInconnu(f"lot_code inconnu : {p.lot_code!r}")
        ajouter_consommables(session.devis, p.lot_code, p.items,
                             chiffrer_maintenant=session.structure_validee)
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
    """Un tour complet : garde-fous, appel modèle, routage.

    Les garde-fous passent **avant** le modèle (docs/DISPOSITIF_AGENT.md §3.1) :
    une consigne injectée ne doit pas atteindre le prompt sans être vue, et une
    demande hors périmètre ne doit pas coûter un appel pour rien.
    """
    rejet = _valider_entree(texte_utilisateur)
    if rejet:
        _journaliser_escalade(session, "entree_rejetee", rejet)
        return ResultatTour("rejet", [rejet], [], session.devis, {})

    cadrages: list[str] = []
    texte_modele = texte_utilisateur

    debut = time.monotonic()

    # HITL-4, la soupape tirée par l'artisan (US-21, §1.4). Avant tout appel
    # modèle : demander un humain et recevoir une réponse générée serait
    # exactement le contraire de ce qui est demandé. Le devis n'est pas touché —
    # le conseiller reprend là où l'artisan en est.
    if demande_un_humain(texte_utilisateur):
        _journaliser_escalade(session, "demande_explicite", texte_utilisateur[:200])
        JOURNAL.enregistrer("escalade", motif="demande_explicite")
        _journaliser_tour(session, "escalade", debut)
        return ResultatTour("escalade", [MESSAGE_HUMAIN], [], session.devis, {})

    injections = detecter_injection(texte_utilisateur)
    if injections:
        # Journaliser d'abord : c'est la trace qui rend l'attaque mesurable.
        _journaliser_escalade(session, "injection_neutralisee", ",".join(injections))
        JOURNAL.enregistrer("injection_neutralisee", motifs=injections)
        cadrages.append(MESSAGE_INJECTION)
        texte_modele = neutraliser(texte_utilisateur)

    domaines = detecter_hors_perimetre(texte_utilisateur)
    if domaines:
        _journaliser_escalade(session, "hors_perimetre", ",".join(domaines))
        JOURNAL.enregistrer("hors_perimetre", domaines=domaines)
        cadrages.extend(message_hors_perimetre(d) for d in domaines)
        if not reste_du_chantier(texte_utilisateur):
            # Rien d'autre à traiter : on nomme la limite au lieu d'improviser.
            _journaliser_tour(session, "hors_perimetre", debut)
            return ResultatTour("hors_perimetre", cadrages, [], session.devis, {},
                                cadrages=list(cadrages))

    resultat = _tour_modele(session, texte_modele)
    resultat.messages_assistant = cadrages + resultat.messages_assistant
    resultat.cadrages = list(cadrages)
    _journaliser_tour(session, resultat.intent, debut, session.reprises_du_tour)
    return resultat


def _journaliser_tour(session: Session, intent: str, debut: float,
                      reprises: int = 0) -> None:
    """Un tour = un message de l'artisan, quelle qu'en soit l'issue. C'est
    l'unité que mesure la latence p95 du §4.3, pas l'appel modèle isolé."""
    JOURNAL.enregistrer("tour", intent=intent, reprises=reprises,
                        latence_ms=round((time.monotonic() - debut) * 1000))


def _tour_modele(session: Session, message_utilisateur: str) -> ResultatTour:
    """Appel modèle avec une reprise, puis escalade (§1.3)."""
    message_suivant = message_utilisateur
    session.reprises_du_tour = 0
    for tentative in range(MAX_APPELS_MODELE):
        derniere_chance = tentative == MAX_APPELS_MODELE - 1
        session.reprises_du_tour = tentative
        depart_appel = time.monotonic()

        def _tracer(valide: bool, motif: str = "") -> None:
            JOURNAL.enregistrer("appel_modele", valide=valide, motif=motif,
                                modele=MODEL_NAME, tentative=tentative,
                                latence_ms=round((time.monotonic() - depart_appel) * 1000))

        try:
            sortie = appeler_modele(session.historique, message_suivant)
        except ModeleInjoignable as exc:
            # Une reprise n'a aucune chance d'aboutir : on sort tout de suite.
            _journaliser_escalade(session, "modele_injoignable", exc)
            _tracer(False, "modele_injoignable")
            return ResultatTour("indisponible", [MESSAGE_INDISPONIBLE], [], session.devis, {})
        except SortieModeleInvalide as exc:
            _journaliser_escalade(session, "json_invalide", exc)
            _tracer(False, "json_invalide")
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
            _tracer(True, intent)
            return ResultatTour(intent, messages, mentions, session.devis, consommables_suggeres)
        except (ValidationError, LotInconnu, ValueError) as exc:
            _journaliser_escalade(session, _motif(exc), exc)
            _tracer(False, _motif(exc))
            if derniere_chance:
                break
            message_suivant = (
                "Ta réponse précédente ne respectait pas le schéma attendu "
                f"({exc}). Corrige-la et réponds uniquement avec un JSON conforme."
            )

    return ResultatTour("escalade", [MESSAGE_ESCALADE], [], session.devis, {})


def valider_structure(session: Session) -> bool:
    """HITL-2 — l'artisan valide lots et quantités ; **alors** on chiffre.

    Valider un devis déjà chiffré, c'est valider un prix ; valider un devis nu,
    c'est valider le métier (docs/DISPOSITIF_AGENT.md §1.4). L'artisan valide
    seul : depuis le pivot, le client n'a plus de rôle actif ici.
    """
    if not session.devis.lignes:
        return False
    session.structure_validee = True
    chiffrer(session.devis)
    return True


def _derniere_dictee(session: Session) -> str:
    """Le dernier message de l'artisan — l'« entrée d'origine » d'une correction
    portée sur ce que le modèle en a fait (US-25)."""
    for tour in reversed(session.historique):
        if tour.get("role") == "user":
            return str(tour.get("content", ""))
    return ""


def valider_transcription(session: Session, propose: str, corrige: str,
                          brut: str = "") -> str:
    """HITL-0 : l'artisan relit sa dictée et la valide (docs/STORIES.md US-05).

    Rien ne s'exécute avant cet appel — c'est ici que le pipeline démarre. Si
    l'artisan a corrigé le texte, l'écart est journalisé au même titre qu'une
    correction de devis : c'est le **premier point de capture du signal qualité**
    (docs/DISPOSITIF_AGENT.md §5.2), celui qui dit ce que la chaîne dictée +
    reformulation a mal entendu.

    `brut` est la dictée avant remise en forme. Quand l'appelant ne la fournit
    pas, la proposition en tient lieu : c'est moins précis, mais le triplet reste
    complet et le candidat exportable (US-25).
    """
    retenu = (corrige or "").strip()
    propose_net = (propose or "").strip()
    if retenu != propose_net:
        session.corrections.append(Correction(
            horodatage=dt.datetime.now().isoformat(timespec="seconds"),
            auteur="artisan",
            description=(f"transcription corrigée avant traitement : "
                         f"« {propose_net[:200]} » → « {retenu[:200]} »"),
            origine="transcription",
            entree=(brut or "").strip() or propose_net,
            sortie_modele=propose_net,
            corrige=retenu,
        ))
        JOURNAL.enregistrer("correction_artisan", origine="transcription")
    return retenu


def confirmer_quantite(session: Session, index: int) -> bool:
    """L'artisan confirme une quantité hors bornes. Il fait autorité (CLAUDE.md) :
    on l'applique sans discuter, et on garde la trace que la borne a été franchie."""
    if not (0 <= index < len(session.a_confirmer)):
        return False
    attente = session.a_confirmer.pop(index)
    ajouter_ligne(session.devis, attente.lot_code, attente.dimension_type,
                  attente.dimension_valeur,
                  chiffrer_maintenant=session.structure_validee)
    if attente.lot_code not in session.lots_presents:
        session.lots_presents.append(attente.lot_code)
    if attente.lot_code in MENTIONS:
        session.devis.mentions.add(MENTIONS[attente.lot_code])
    mesure = (f"{attente.lot_code} : {attente.dimension_valeur} "
              f"{attente.dimension_type}")
    session.corrections.append(Correction(
        horodatage=dt.datetime.now().isoformat(timespec="seconds"),
        auteur="artisan",
        description=(f"quantité hors bornes confirmée : {attente.dimension_valeur} "
                     f"{attente.dimension_type} sur {attente.lot_code} "
                     f"(bornes {attente.borne_min}–{attente.borne_max})"),
        origine="quantite_hors_bornes",
        entree=_derniere_dictee(session),
        sortie_modele=mesure,
        # L'artisan confirme : la sortie du modèle est la version retenue. Le
        # signal ne porte donc pas sur le modèle mais sur les bornes du
        # référentiel, qui ont crié à tort — c'est `origine` qui le dit.
        corrige=mesure,
    ))
    JOURNAL.enregistrer("correction_artisan", origine="quantite_hors_bornes",
                        lot_code=attente.lot_code)
    return True


def abandonner_quantite(session: Session, index: int) -> bool:
    """L'artisan reconnaît une erreur de dictée : on jette la ligne en attente."""
    if not (0 <= index < len(session.a_confirmer)):
        return False
    session.a_confirmer.pop(index)
    return True


def corriger_ligne(session: Session, index_ligne: int, description: str) -> None:
    """HITL-2 : l'artisan corrige. Appliqué sans discussion, journalisé (§5.2)."""
    retiree = ""
    if 0 <= index_ligne < len(session.devis.lignes):
        ligne = session.devis.lignes.pop(index_ligne)
        # Ce qu'on garde de la ligne : ce que le modèle a décrit, jamais son
        # prix — le prix vient du catalogue, pas du modèle (CLAUDE.md).
        retiree = (f"{ligne.lot_code} : {ligne.nom_lot} — "
                   f"{ligne.quantite_technique} {ligne.unite_technique}".strip())
    session.corrections.append(
        Correction(horodatage=dt.datetime.now().isoformat(timespec="seconds"),
                   auteur="artisan", description=description,
                   origine="ligne_devis",
                   entree=_derniere_dictee(session),
                   sortie_modele=retiree,
                   corrige=description.strip())
    )
    JOURNAL.enregistrer("correction_artisan", origine="ligne_devis")
