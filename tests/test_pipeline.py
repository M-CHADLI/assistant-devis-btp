"""Tests du pipeline — routage, budget d'appels modèle, journalisation.

Le modèle n'est jamais appelé pour de vrai ici : on remplace `appeler_modele`
par une fausse fonction qui rend ce qu'on veut. Un test qui dépend d'Ollama
n'est pas un test, c'est une intégration.
"""
from __future__ import annotations

import pytest

from app import pipeline
from app.llm import ModeleInjoignable, SortieModeleInvalide
from app.garde_fous import MESSAGE_HUMAIN
from app.pipeline import MAX_APPELS_MODELE, Session, traiter_message


class FauxModele:
    """Rend les sorties fournies, une par appel, et compte les appels."""

    def __init__(self, *sorties):
        self.sorties = list(sorties)
        self.appels = 0

    def __call__(self, historique, message, timeout=60):
        self.appels += 1
        sortie = self.sorties.pop(0) if self.sorties else self.sorties_par_defaut()
        if isinstance(sortie, Exception):
            raise sortie
        return sortie

    def sorties_par_defaut(self):
        return {"intent": "reponse", "payload": {"texte": "ok"}, "mention": None}


@pytest.fixture
def faux(monkeypatch):
    def _installer(*sorties):
        f = FauxModele(*sorties)
        monkeypatch.setattr(pipeline, "appeler_modele", f)
        return f
    return _installer


def _sortie_devis(lot_code="PEINT_FINITION", valeur=22.0, intent="devis"):
    return {"intent": intent, "mention": None,
            "payload": {"pieces": ["salon"],
                        "lignes": [{"lot_code": lot_code,
                                    "dimension": {"type": "surface", "valeur": valeur}}]}}


# --- T-001 : l'intent "quantitatif" est routé ------------------------------

def test_intent_quantitatif_est_route(faux):
    """Il figure au schéma et au prompt système : le routeur doit le connaître."""
    faux(_sortie_devis(intent="quantitatif"))
    s = Session()
    r = traiter_message(s, "22 m2 de peinture dans le salon")
    assert r.intent == "quantitatif"
    assert len(s.devis.lignes) == 1


def test_intent_inconnu_escalade_et_journalise(faux):
    faux({"intent": "inventé", "payload": {}, "mention": None},
         {"intent": "inventé", "payload": {}, "mention": None})
    s = Session()
    r = traiter_message(s, "salut")
    assert r.intent == "escalade"
    assert [e.motif for e in s.escalades] == ["intent_inconnu", "intent_inconnu"]


# --- T-005 : budget d'appels modèle ----------------------------------------

def test_un_message_ne_coute_jamais_plus_de_deux_appels(faux):
    """Les reprises de app.llm et app.pipeline se composaient : jusqu'à 4 appels."""
    f = faux(SortieModeleInvalide("pas de JSON"), SortieModeleInvalide("toujours pas"))
    s = Session()
    r = traiter_message(s, "je refais le salon")
    assert f.appels == MAX_APPELS_MODELE == 2
    assert r.intent == "escalade"


def test_une_reprise_suffit_quand_le_second_appel_est_bon(faux):
    f = faux(SortieModeleInvalide("pas de JSON"), _sortie_devis())
    s = Session()
    r = traiter_message(s, "22 m2 de peinture")
    assert f.appels == 2
    assert r.intent == "devis"
    assert [e.motif for e in s.escalades] == ["json_invalide"]


# --- T-004 : motifs d'escalade journalisés ---------------------------------

def test_lot_inconnu_journalise_son_motif(faux):
    faux(_sortie_devis(lot_code="LOT_QUI_N_EXISTE_PAS"),
         _sortie_devis(lot_code="LOT_QUI_N_EXISTE_PAS"))
    s = Session()
    traiter_message(s, "pose un truc")
    assert [e.motif for e in s.escalades] == ["lot_inconnu", "lot_inconnu"]
    assert all(e.horodatage for e in s.escalades)


def test_modele_injoignable_ne_reprend_pas(faux):
    """Réessayer un service arrêté ne fait que doubler l'attente."""
    f = faux(ModeleInjoignable("connexion refusée"))
    s = Session()
    r = traiter_message(s, "je refais le salon")
    assert f.appels == 1
    assert r.intent == "indisponible"
    assert s.escalades[0].motif == "modele_injoignable"


def test_entree_vide_rejetee_sans_appel_modele(faux):
    f = faux()
    s = Session()
    r = traiter_message(s, "   ")
    assert f.appels == 0
    assert r.intent == "rejet"
    assert s.escalades[0].motif == "entree_rejetee"


def test_entree_trop_longue_rejetee(faux):
    f = faux()
    s = Session()
    r = traiter_message(s, "a" * (pipeline.LONGUEUR_MAX_ENTREE + 1))
    assert f.appels == 0
    assert r.intent == "rejet"


# --- Idempotence : l'artisan se répète à l'oral ----------------------------

def test_reconfirmation_orale_identique_ne_duplique_pas(faux):
    faux(_sortie_devis(), _sortie_devis())
    s = Session()
    traiter_message(s, "22 m2 de peinture dans le salon")
    traiter_message(s, "donc 22 m2 de peinture dans le salon")
    assert len(s.devis.lignes) == 1


def test_mention_ajoutee_par_le_code_meme_si_le_modele_l_oublie(faux):
    """La sécurité ne repose pas sur la bonne volonté du modèle."""
    faux(_sortie_devis(lot_code="ELEC_TABLEAU", valeur=1.0))
    s = Session()
    r = traiter_message(s, "remplace le tableau électrique")
    assert "forte" in r.mentions
    assert "forte" in s.devis.mentions


# --- US-11 : bornes de plausibilité ---------------------------------------

def test_quantite_invraisemblable_n_est_pas_ajoutee(faux):
    """« 220 m² » pour « 22 m² » : une dictée avale un point décimal."""
    faux(_sortie_devis(valeur=2200.0))
    s = Session()
    r = traiter_message(s, "deux mille deux cents metres carres de peinture")
    assert s.devis.lignes == []
    assert len(s.a_confirmer) == 1
    assert s.a_confirmer[0].dimension_valeur == 2200.0
    assert any("confirmé" in m for m in r.messages_assistant)


def test_quantite_plausible_passe_sans_friction(faux):
    faux(_sortie_devis(valeur=22.0))
    s = Session()
    traiter_message(s, "22 m2 de peinture")
    assert len(s.devis.lignes) == 1
    assert s.a_confirmer == []


def test_l_artisan_peut_confirmer_une_quantite_hors_bornes(faux):
    """L'artisan fait autorité : sa confirmation s'applique sans discussion."""
    faux(_sortie_devis(valeur=2200.0))
    s = Session()
    traiter_message(s, "un très grand chantier")
    assert pipeline.confirmer_quantite(s, 0) is True
    assert len(s.devis.lignes) == 1
    assert s.a_confirmer == []
    assert "hors bornes confirmée" in s.corrections[0].description


def test_l_artisan_peut_abandonner_une_quantite_hors_bornes(faux):
    faux(_sortie_devis(valeur=2200.0))
    s = Session()
    traiter_message(s, "erreur de dictée")
    assert pipeline.abandonner_quantite(s, 0) is True
    assert s.devis.lignes == []
    assert s.a_confirmer == []


def test_confirmer_un_index_inexistant_ne_plante_pas(faux):
    s = Session()
    assert pipeline.confirmer_quantite(s, 0) is False
    assert pipeline.abandonner_quantite(s, 3) is False


def test_une_quantite_confirmee_n_est_pas_redemandee_au_tour_suivant(faux):
    """Critère US-11 : reconfirmer serait traiter l'artisan comme non fiable."""
    faux(_sortie_devis(valeur=2200.0), _sortie_devis(valeur=2200.0))
    s = Session()
    traiter_message(s, "un très grand chantier")
    pipeline.confirmer_quantite(s, 0)
    traiter_message(s, "je redis : deux mille deux cents mètres carrés")
    assert s.a_confirmer == [], "la quantité déjà confirmée ne repasse pas en attente"
    assert len(s.devis.lignes) == 1, "et elle n'est pas ajoutée deux fois"


def test_borne_serree_sur_le_tableau_electrique(faux):
    """Un logement a un tableau, deux au plus — pas douze."""
    faux(_sortie_devis(lot_code="ELEC_TABLEAU", valeur=12.0))
    s = Session()
    traiter_message(s, "douze tableaux électriques")
    assert s.devis.lignes == []
    assert s.a_confirmer[0].borne_max == 3.0


# --- US-07 : plafond de clarification (HITL-1) -----------------------------

def _sortie_clarification():
    return {"intent": "clarification", "mention": None,
            "payload": {"questions": ["Quelle surface ?"]}}


def test_trois_tours_de_clarification_sont_permis(faux):
    faux(*[_sortie_clarification()] * 3)
    s = Session()
    for _ in range(3):
        r = traiter_message(s, "je veux refaire une pièce")
        assert r.intent == "clarification"
    assert s.tours_clarification == 3


def test_au_quatrieme_tour_l_agent_pose_des_hypotheses_au_lieu_de_questionner(faux):
    """Un agent qui questionne sans fin est un agent qui ne sait pas décider."""
    faux(*[_sortie_clarification()] * 4)
    s = Session()
    for _ in range(3):
        traiter_message(s, "je veux refaire une pièce")
    r = traiter_message(s, "je ne sais pas")
    assert r.intent == "hypotheses"
    assert "Quelle surface ?" not in r.messages_assistant
    assert any("TVA à 10" in m for m in r.messages_assistant)
    assert len(r.messages_assistant) == 1 + len(pipeline.HYPOTHESES_PAR_DEFAUT)


def test_le_compteur_de_clarification_ne_bouge_pas_sur_un_devis(faux):
    faux(_sortie_devis())
    s = Session()
    traiter_message(s, "22 m2 de peinture")
    assert s.tours_clarification == 0


# --- US-21 : l'artisan tire lui-même la soupape ----------------------------

def test_la_demande_d_humain_court_circuite_le_modele(faux):
    """Répondre à « je veux un humain » par du texte généré serait exactement
    le contraire de ce qui est demandé : le modèle n'est pas appelé."""
    f = faux()
    s = Session()
    r = traiter_message(s, "je veux parler à un humain")
    assert r.intent == "escalade"
    assert f.appels == 0
    assert r.messages_assistant == [MESSAGE_HUMAIN]


def test_l_escalade_demandee_est_journalisee_avec_son_motif(faux):
    faux()
    s = Session()
    traiter_message(s, "passe-moi un conseiller")
    assert [e.motif for e in s.escalades] == ["demande_explicite"]
    assert s.escalades[0].horodatage


def test_l_escalade_demandee_conserve_le_devis_en_cours(faux):
    """Scénario 3 : le conseiller reprend là où l'artisan en est, il ne repart
    pas de zéro."""
    faux(_sortie_devis())
    s = Session()
    traiter_message(s, "je refais le salon, 22 m2 de peinture")
    avant = list(s.devis.lignes)
    assert avant, "le tour de mise en place doit produire au moins une ligne"
    r = traiter_message(s, "bon, passe-moi un humain")
    assert r.intent == "escalade"
    assert list(r.devis.lignes) == avant
    assert list(s.devis.lignes) == avant
