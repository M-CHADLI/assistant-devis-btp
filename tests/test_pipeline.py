"""Tests du pipeline — routage, budget d'appels modèle, journalisation.

Le modèle n'est jamais appelé pour de vrai ici : on remplace `appeler_modele`
par une fausse fonction qui rend ce qu'on veut. Un test qui dépend d'Ollama
n'est pas un test, c'est une intégration.
"""
from __future__ import annotations

import pytest

from app import pipeline
from app.llm import ModeleInjoignable, SortieModeleInvalide
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
