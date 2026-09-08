# -*- coding: utf-8 -*-
"""Tests du module ``tools/notion_cli.py``.

Ce fichier vérifie la conformité entre les CSV de Notion et leurs schémas JSON
associés ainsi que le comportement de quelques fonctions utilitaires du
module.

Les exigences proviennent du cahier des charges :

* chaque colonne du CSV doit exister dans ``proprietes`` du schéma,
* chaque propriété du schéma doit avoir une colonne correspondante,
* un seul champ de type ``title`` doit être présent dans chaque schéma,
* les valeurs ``select`` du CSV doivent être déclarées dans le schéma,
* ``definition_type`` doit renvoyer la clé de type en ignorant ``name`` et
  ``description`` ; lorsqu'aucune clé ne correspond, il renvoie ``"rich_text"``,
* ``_valeur`` doit convertir correctement les différentes typologies,
* le CSV ``stories.csv`` doit contenir exactement 28 lignes de données.

Les tests sont écrits en français et utilisent le style présent dans les
autres fichiers de tests du projet.
"""

from __future__ import annotations

import csv
import json
import importlib.util
from pathlib import Path
from typing import Any, Dict

import pytest

# ---------------------------------------------------------------------------
# Chargement du module ``tools/notion_cli.py`` sans package ``tools``
# ---------------------------------------------------------------------------

MODULE_PATH = Path(__file__).parents[1] / "tools" / "notion_cli.py"
spec = importlib.util.spec_from_file_location("notion_cli", MODULE_PATH)
assert spec is not None, "Impossible de créer le spec du module notion_cli"
notion_cli = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(notion_cli)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# Données de test – couples CSV / schéma
# ---------------------------------------------------------------------------

COUPLES = [
    (
        Path("docs/notion/stories.csv"),
        Path("docs/notion/schema-stories.json"),
    ),
    (
        Path("docs/notion/sprints.csv"),
        Path("docs/notion/schema-sprints.json"),
    ),
    (
        Path("docs/notion/taches.csv"),
        Path("docs/notion/schema-taches.json"),
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def charger_csv(path: Path) -> list[dict[str, str]]:
    """Lit un CSV et renvoie la liste des lignes sous forme de dictionnaires.

    Les valeurs sont conservées telles‑quelles (pas de conversion de type).
    """
    with path.open(encoding="utf-8", newline="") as f:
        lecteur = csv.DictReader(f)
        return list(lecteur)


def charger_schema(path: Path) -> dict[str, Any]:
    """Charge le fichier JSON de schéma et renvoie le dictionnaire complet."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# 1. Aucune colonne orpheline
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("csv_path, schema_path", COUPLES)
def test_aucune_colonne_orpheline(csv_path: Path, schema_path: Path) -> None:
    """Toutes les colonnes du CSV existent dans le dictionnaire ``proprietes`` du schéma."""
    csv_abs = Path(__file__).parents[1] / csv_path
    schema_abs = Path(__file__).parents[1] / schema_path

    lignes = charger_csv(csv_abs)
    if not lignes:
        pytest.fail(f"Le CSV {csv_path} ne contient aucune donnée.")
    entetes = lignes[0].keys()
    schema = charger_schema(schema_abs)
    proprietes = schema.get("proprietes", {})

    colonnes_orphelines = [c for c in entetes if c not in proprietes]
    assert not colonnes_orphelines, (
        f"Colonnes orphelines dans {csv_path} : {', '.join(colonnes_orphelines)}"
    )

# ---------------------------------------------------------------------------
# 2. Aucune propriété sans colonne
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("csv_path, schema_path", COUPLES)
def test_aucune_propriete_sans_colonne(csv_path: Path, schema_path: Path) -> None:
    """Chaque propriété du schéma possède une colonne correspondante dans le CSV."""
    csv_abs = Path(__file__).parents[1] / csv_path
    schema_abs = Path(__file__).parents[1] / schema_path

    lignes = charger_csv(csv_abs)
    entetes = lignes[0].keys() if lignes else []
    schema = charger_schema(schema_abs)
    proprietes = schema.get("proprietes", {})

    proprietes_sans_colonne = [p for p in proprietes if p not in entetes]
    assert not proprietes_sans_colonne, (
        f"Propriétés non présentes dans {csv_path} : {', '.join(proprietes_sans_colonne)}"
    )

# ---------------------------------------------------------------------------
# 3. Unicité du champ ``title``
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("unused, schema_path", COUPLES)
def test_unique_title(unused: Path, schema_path: Path) -> None:
    """Chaque schéma ne doit contenir qu'une seule propriété de type ``title``."""
    schema_abs = Path(__file__).parents[1] / schema_path
    schema = charger_schema(schema_abs)
    proprietes = schema.get("proprietes", {})

    titres = [
        nom for nom, definition in proprietes.items()
        if notion_cli.definition_type(definition) == "title"
    ]
    assert len(titres) == 1, (
        f"Le schéma {schema_path} contient {len(titres)} propriétés de type 'title' : {', '.join(titres)}"
    )

# ---------------------------------------------------------------------------
# 4. Valeurs ``select`` et ``multi_select`` déclarées dans le schéma
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("csv_path, schema_path", COUPLES)
def test_select_valeurs_declarees(csv_path: Path, schema_path: Path) -> None:
    """Chaque valeur non vide d'une colonne ``select`` ou ``multi_select`` doit appartenir aux options du schéma.

    Pour ``multi_select`` les valeurs sont séparées par le séparateur ``·`` et les espaces sont rognés.
    Les propriétés sans liste d'options sont ignorées.
    """
    csv_abs = Path(__file__).parents[1] / csv_path
    schema_abs = Path(__file__).parents[1] / schema_path

    lignes = charger_csv(csv_abs)
    schema = charger_schema(schema_abs)
    proprietes = schema.get("proprietes", {})

    # Recueillir les colonnes de type select ou multi_select avec leurs options
    select_options: dict[str, set[str]] = {}
    for nom, definition in proprietes.items():
        typ = notion_cli.definition_type(definition)
        if typ == "select":
            opts = definition.get("select", {}).get("options", [])
            if opts:
                select_options[nom] = {opt.get("name") for opt in opts}
        elif typ == "multi_select":
            opts = definition.get("multi_select", {}).get("options", [])
            if opts:
                select_options[nom] = {opt.get("name") for opt in opts}

    for num, ligne in enumerate(lignes, start=2):  # start=2 pour refléter le numéro de ligne réel
        for col, valeur in ligne.items():
            if col not in select_options:
                continue
            valeur = valeur.strip()
            if not valeur:
                continue
            typ = notion_cli.definition_type(proprietes[col])
            if typ == "select":
                # valeur unique
                if valeur not in select_options[col]:
                    pytest.fail(
                        f"Valeur inconnue '{valeur}' pour la colonne select '{col}' "
                        f"dans {csv_path} (ligne {num})"
                    )
            elif typ == "multi_select":
                # découper sur le séparateur ·
                fragments = [frag.strip() for frag in valeur.split("·") if frag.strip()]
                for frag in fragments:
                    if frag not in select_options[col]:
                        pytest.fail(
                            f"Valeur inconnue '{frag}' pour la colonne multi_select '{col}' "
                            f"dans {csv_path} (ligne {num})"
                        )

# ---------------------------------------------------------------------------
# 5. Fonction ``definition_type``
# ---------------------------------------------------------------------------

def test_definition_type_comportement() -> None:
    """Vérifie les cas d'usage de ``definition_type``.

    - ignore les clés ``name`` et ``description``
    - renvoie ``rich_text`` lorsqu'aucune autre clé n'est présente
    """
    # Cas standard
    definition = {"title": {}, "name": "Quelque chose"}
    assert notion_cli.definition_type(definition) == "title"

    # Ignorer name / description
    definition = {"name": "x", "description": "y", "number": {"format": "number"}}
    assert notion_cli.definition_type(definition) == "number"

    # Aucun type déclaré → fallback rich_text
    definition = {"name": "x", "description": "y"}
    assert notion_cli.definition_type(definition) == "rich_text"

# ---------------------------------------------------------------------------
# 6. Fonction ``_valeur`` – tests unitaires pour chaque branche
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "type_prop, brut, attendu",
    [
        ("title", "", None),
        ("title", "   ", None),
        ("title", "Mon titre", {"title": [{"text": {"content": "Mon titre"}}]}),
        ("rich_text", "Texte", {"rich_text": [{"text": {"content": "Texte"}}]}),
        ("select", "Option", {"select": {"name": "Option"}}),
        ("multi_select", "A·B· C ", {"multi_select": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}),
        ("number", "3,5", {"number": 3.5}),
        ("number", "abc", None),
        ("date", "2026-09-08", {"date": {"start": "2026-09-08"}}),
        ("checkbox", "true", {"checkbox": True}),
        ("checkbox", "FAUX", {"checkbox": False}),
        ("checkbox", "Oui", {"checkbox": True}),
        ("inconnu", "Quelque chose", {"rich_text": [{"text": {"content": "Quelque chose"}}]}),
        # tests de troncature des champs texte et select
        ("title", "a" * 2500, {"title": [{"text": {"content": "a" * 2000}}]}),
        ("rich_text", "a" * 2500, {"rich_text": [{"text": {"content": "a" * 2000}}]}),
        ("select", "a" * 150, {"select": {"name": "a" * 100}}),
    ],
)
def test_valeur_branches(type_prop: str, brut: str, attendu: Any) -> None:
    """Teste la conversion d'une cellule CSV selon le type de propriété Notion.

    La fonction ``_valeur`` doit respecter les règles décrites dans le cahier des
    charges.
    """
    resultat = notion_cli._valeur(type_prop, brut)
    assert resultat == attendu

# ---------------------------------------------------------------------------
# 7. Nombre de lignes dans ``stories.csv``
# ---------------------------------------------------------------------------

def test_stories_nombre_lignes() -> None:
    """Le fichier ``stories.csv`` doit contenir exactement 28 lignes de données.

    Le compte exclut l'en‑tête.
    """
    csv_path = Path(__file__).parents[1] / "docs/notion/stories.csv"
    lignes = charger_csv(csv_path)
    assert len(lignes) == 28, f"stories.csv contient {len(lignes)} lignes, attendu 28"

# ---------------------------------------------------------------------------
# 8. Ce que le contrôle des options ne couvre PAS
# ---------------------------------------------------------------------------

# Une propriété « select » ou « multi_select » sans liste « options » ne peut
# pas être contrôlée : il n'y a rien à quoi comparer. Notion crée alors les
# options à la volée pendant l'import, ce qui est un comportement légitime —
# mais un test qui saute en silence ressemble, dans une sortie verte, à un test
# qui a vérifié. C'est exactement ce que ce projet refuse ailleurs.
#
# Constaté le 08/09/2026 par mutation : injecter « C99-inventee » dans la
# colonne Compétences de stories.csv ne fait échouer aucun des 30 tests.
# Ce n'est pas un défaut du test précédent, c'est l'absence d'options dans le
# schéma. La liste ci-dessous nomme cette absence pour qu'elle reste un choix
# visible et non un angle mort.
SANS_OPTIONS_DECLAREES = {
    ("docs/notion/schema-stories.json", "Compétences"),
}


@pytest.mark.parametrize("unused, schema_path", COUPLES)
def test_les_options_absentes_sont_toutes_connues(unused: Path, schema_path: Path) -> None:
    """Aucune propriété à choix ne perd son contrôle sans que ce soit déclaré ici.

    Le jour où une propriété « select » ou « multi_select » perd ses options —
    ou en gagne — ce test le dit. Il ne juge pas : il empêche seulement qu'un
    contrôle cesse de mordre sans que personne le remarque.
    """
    schema = charger_schema(Path(__file__).parents[1] / schema_path)

    constatees = {
        (str(schema_path), nom)
        for nom, definition in schema.get("proprietes", {}).items()
        if notion_cli.definition_type(definition) in ("select", "multi_select")
        and not definition.get(notion_cli.definition_type(definition), {}).get("options")
    }
    attendues = {couple for couple in SANS_OPTIONS_DECLAREES if couple[0] == str(schema_path)}

    nouvelles = constatees - attendues
    assert not nouvelles, (
        f"Propriété(s) à choix devenues incontrôlables sans être déclarées : "
        f"{sorted(n for _, n in nouvelles)}. "
        "Soit leur donner des « options » dans le schéma, soit les ajouter à "
        "SANS_OPTIONS_DECLAREES en sachant que plus rien ne les vérifie."
    )

    disparues = attendues - constatees
    assert not disparues, (
        f"Propriété(s) déclarées sans options mais qui en ont désormais : "
        f"{sorted(n for _, n in disparues)}. Les retirer de SANS_OPTIONS_DECLAREES : "
        "elles sont contrôlées, la dispense n'a plus lieu d'être."
    )


# ---------------------------------------------------------------------------
# Fin du fichier de tests
# ---------------------------------------------------------------------------
