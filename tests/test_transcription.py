"""US-05 — HITL-0 : relecture de la dictée avant tout traitement.

Deux choses sont vérifiées ici : que rien ne part en aval sans validation, et
que la reformulation ne peut pas déformer un chiffre sans être écartée.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import requests

from app import transcription
from app.pipeline import Session, valider_transcription
from app.transcription import ALERTE_CHIFFRES, chiffres_preserves, relire


@pytest.fixture
def modele_muet(monkeypatch):
    """Par défaut, aucun test ne parle au vrai modèle."""
    def refuser(*_a, **_k):
        raise AssertionError("appel modèle non attendu")
    monkeypatch.setattr(transcription, "_appeler_reformulateur", refuser)


def repondre(monkeypatch, texte):
    monkeypatch.setattr(transcription, "_appeler_reformulateur",
                        lambda brut, timeout: texte)


# --- La frontière modèle prompté / modèle fine-tuné -------------------------

def test_la_relecture_n_utilise_pas_le_modele_du_pipeline():
    """Critère US-05 : la frontière doit être vérifiable dans le code."""
    source = Path(transcription.__file__).read_text(encoding="utf-8")
    imports = [l for l in source.splitlines()
               if l.startswith(("import ", "from ")) and "app.llm" in l]
    assert imports == [], f"la relecture importe le modèle du pipeline : {imports}"
    code = [l for l in source.splitlines() if not l.lstrip().startswith("#")]
    assert not any("appeler_modele(" in l for l in code)
    assert transcription.MODELE_PROMPTE  # nommé pour ce qu'il est


# --- Le garde-fou sur les chiffres ------------------------------------------

@pytest.mark.parametrize("brut, propose, preserve", [
    ("22 m² au sol", "J'ai 22 m2 au sol.", True),
    ("22 m² au sol", "2 m² au sol.", False),          # le cas du scénario 2
    ("22,0 m linéaires", "22 m linéaires", True),     # même nombre écrit autrement
    ("3 portes", "30 portes", False),
    ("le salon fait 22 m² et 2,5 m sous plafond",
     "Le salon fait 22 m², 2,5 m sous plafond.", True),
])
def test_les_chiffres_et_unites_sont_compares(brut, propose, preserve):
    assert chiffres_preserves(brut, propose) is preserve


def test_une_reformulation_qui_change_un_chiffre_est_jetee(monkeypatch):
    repondre(monkeypatch, "Je refais le salon, 2 m² au sol.")
    lecture = relire("je refais le salon 22 m2 au sol")
    assert lecture.propose == "je refais le salon 22 m2 au sol"  # le brut, intact
    assert lecture.reformule is False
    assert lecture.alerte == ALERTE_CHIFFRES


def test_une_reformulation_honnete_est_proposee(monkeypatch):
    repondre(monkeypatch, "Je refais le salon : 22 m² au sol.")
    lecture = relire("euh je refais le salon 22 m2 au sol")
    assert lecture.propose == "Je refais le salon : 22 m² au sol."
    assert lecture.reformule is True
    assert lecture.alerte == ""


# --- Cas dégradés -----------------------------------------------------------

def test_le_modele_injoignable_ne_bloque_pas_la_dictee(monkeypatch):
    def tomber(brut, timeout):
        raise requests.ConnectionError("Ollama arrêté")
    monkeypatch.setattr(transcription, "_appeler_reformulateur", tomber)

    lecture = relire("22 m2 de peinture")
    assert lecture.propose == "22 m2 de peinture"
    assert lecture.reformule is False
    assert "indisponible" in lecture.alerte


def test_une_dictee_vide_ne_declenche_aucun_appel(modele_muet):
    lecture = relire("   ")
    assert lecture.propose == ""


# --- Journalisation du signal qualité ---------------------------------------

def test_une_correction_de_transcription_est_journalisee():
    session = Session()
    retenu = valider_transcription(session, "2 m² au sol", "22 m² au sol")
    assert retenu == "22 m² au sol"
    assert len(session.corrections) == 1
    trace = session.corrections[0]
    assert trace.auteur == "artisan"
    assert "2 m² au sol" in trace.description and "22 m² au sol" in trace.description
    assert trace.horodatage


def test_une_validation_sans_changement_ne_journalise_rien():
    session = Session()
    valider_transcription(session, "22 m² au sol", "  22 m² au sol  ")
    assert session.corrections == []
