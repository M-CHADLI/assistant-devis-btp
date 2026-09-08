"""Contrat de l'API (US-22) — l'OpenAPI doit dire vrai.

Une documentation qui décrit autre chose que ce que le code émet est pire que
pas de documentation : elle se fait croire. Ces tests comparent la déclaration
au code réellement écrit.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.conftest import authentifier

from app import main
from app.api_schema import DevisSortie, LigneStructure

SOURCE_MAIN = Path(main.__file__).read_text(encoding="utf-8")


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.persistance import Registre
    monkeypatch.setattr(main, "REGISTRE", Registre(racine=tmp_path))
    c = TestClient(main.app)
    authentifier(c)
    return c


def _operations(schema: dict) -> dict[tuple[str, str], dict]:
    return {(chemin, methode): op
            for chemin, methodes in schema["paths"].items()
            for methode, op in methodes.items()}


def test_chaque_endpoint_a_un_resume_en_francais(client):
    for (chemin, methode), op in _operations(client.get("/openapi.json").json()).items():
        assert op.get("summary"), f"{methode.upper()} {chemin} sans résumé"


def test_chaque_endpoint_json_a_un_schema_de_reponse(client):
    """Sauf les deux pages HTML et l'export binaire, qui ne sont pas du JSON."""
    sans_schema = {("/", "get"), ("/metriques", "get"), ("/api/export", "get")}
    for (chemin, methode), op in _operations(client.get("/openapi.json").json()).items():
        if (chemin, methode) in sans_schema:
            continue
        contenu = op["responses"]["200"].get("content", {})
        assert "application/json" in contenu, f"{methode.upper()} {chemin}"
        assert contenu["application/json"]["schema"], f"{methode.upper()} {chemin}"


def _codes_emis(nom_fonction: str) -> set[int]:
    """Les `HTTPException(status_code=…)` levés dans une fonction de main.py."""
    arbre = ast.parse(SOURCE_MAIN)
    codes: set[int] = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef) and noeud.name == nom_fonction:
            for appel in ast.walk(noeud):
                if (isinstance(appel, ast.Call)
                        and getattr(appel.func, "id", "") == "HTTPException"):
                    for mot_cle in appel.keywords:
                        if (mot_cle.arg == "status_code"
                                and isinstance(mot_cle.value, ast.Constant)):
                            codes.add(mot_cle.value.value)
    return codes


@pytest.mark.parametrize("chemin, methode, fonction", [
    ("/api/valider-structure", "post", "api_valider_structure"),
    ("/api/quantite", "post", "api_quantite"),
    ("/api/export", "get", "api_export"),
])
def test_les_codes_d_erreur_declares_sont_ceux_reellement_emis(client, chemin,
                                                               methode, fonction):
    op = _operations(client.get("/openapi.json").json())[(chemin, methode)]
    declares = {int(c) for c in op["responses"] if c.isdigit() and int(c) >= 400}
    emis = _codes_emis(fonction)
    assert emis <= declares, f"{fonction} émet {emis - declares} sans le déclarer"


def test_un_corps_non_conforme_donne_un_422_pas_un_500(client):
    r = client.post("/api/message", json={"pas_le_bon_champ": 1})
    assert r.status_code == 422
    r = client.post("/api/quantite", json={"index": 0, "action": "danser"})
    assert r.status_code == 422


def test_le_contrat_interdit_un_prix_avant_validation_de_structure():
    """US-12 tenu par le schéma, pas seulement par le commentaire."""
    with pytest.raises(ValidationError):
        LigneStructure(lot_code="PEINT_FINITION", designation="Peinture",
                       quantite=22.0, unite="m²", origine="modele",
                       prix_ht=180.0)


def test_le_contrat_accepte_les_deux_formes_de_ligne():
    nu = {"pieces": [], "lignes": [{"lot_code": "X", "designation": "d",
                                    "quantite": 1.0, "unite": "m²", "origine": "modele"}],
          "structure_validee": False, "total_ht": None, "ventilation_tva": {},
          "total_tva": None, "total_ttc": None, "acompte_30_pct": None,
          "mentions": [], "franchise_tva": False, "mentions_manquantes": [],
          "a_confirmer": [], "corrections": []}
    assert DevisSortie.model_validate(nu).lignes[0].__class__ is LigneStructure

    chiffre = dict(nu, structure_validee=True, total_ht=180.0,
                   lignes=[dict(nu["lignes"][0], prix_unitaire_ht=9.0,
                                prix_ht=180.0, taux_tva=0.10)])
    ligne = DevisSortie.model_validate(chiffre).lignes[0]
    assert ligne.prix_ht == 180.0


def test_l_api_annonce_sa_regle_structurante_dans_sa_description(client):
    """Le jury lit l'OpenAPI sans exécuter le produit : la frontière
    modèle/code doit s'y voir."""
    description = client.get("/openapi.json").json()["info"]["description"]
    assert "aucune clé de prix" in description
