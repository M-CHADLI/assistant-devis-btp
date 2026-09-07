#!/usr/bin/env python3
"""CLI Notion minimal — évite de charger 42 outils MCP dans le contexte.

Jeton : variable d'environnement NOTION_TOKEN (intégration interne Notion).
Version d'API : NOTION_VERSION, par défaut 2022-06-28.

    export NOTION_TOKEN=ntn_xxx
    python tools/notion_cli.py whoami
    python tools/notion_cli.py search "the-project"
    python tools/notion_cli.py db-create --parent <page_id> --schema docs/notion/schema-stories.json
    python tools/notion_cli.py import --db <db_id> --csv docs/notion/stories.csv \
                                      --schema docs/notion/schema-stories.json

La sortie est volontairement compacte (identifiant + titre) : ce CLI est fait pour
être lu par un humain ou par un agent sans saturer son contexte.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.notion.com/v1"


def _appel(methode: str, chemin: str, corps: dict | None = None) -> dict:
    jeton = os.environ.get("NOTION_TOKEN")
    if not jeton:
        sys.exit("NOTION_TOKEN absent de l'environnement.")
    donnees = json.dumps(corps).encode() if corps is not None else None
    requete = urllib.request.Request(
        f"{API}{chemin}",
        data=donnees,
        method=methode,
        headers={
            "Authorization": f"Bearer {jeton}",
            "Notion-Version": os.environ.get("NOTION_VERSION", "2022-06-28"),
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            return json.loads(reponse.read())
    except urllib.error.HTTPError as erreur:
        detail = erreur.read().decode(errors="replace")[:500]
        sys.exit(f"HTTP {erreur.code} sur {methode} {chemin}\n{detail}")


def _titre(objet: dict) -> str:
    """Extrait un titre lisible d'une page ou d'une base, quel que soit son schéma."""
    if objet.get("object") == "database":
        return "".join(f.get("plain_text", "") for f in objet.get("title", [])) or "(sans titre)"
    for valeur in (objet.get("properties") or {}).values():
        if valeur.get("type") == "title":
            return "".join(f.get("plain_text", "") for f in valeur["title"]) or "(sans titre)"
    return "(sans titre)"


def _valeur(type_propriete: str, brut: str) -> dict | None:
    """Convertit une cellule CSV en valeur de propriété Notion."""
    brut = brut.strip()
    if not brut:
        return None
    if type_propriete == "title":
        return {"title": [{"text": {"content": brut[:2000]}}]}
    if type_propriete == "rich_text":
        return {"rich_text": [{"text": {"content": brut[:2000]}}]}
    if type_propriete == "select":
        return {"select": {"name": brut[:100]}}
    if type_propriete == "multi_select":
        return {"multi_select": [{"name": p.strip()[:100]} for p in brut.split("·") if p.strip()]}
    if type_propriete == "number":
        try:
            return {"number": float(brut.replace(",", "."))}
        except ValueError:
            return None
    if type_propriete == "date":
        return {"date": {"start": brut}}
    if type_propriete == "checkbox":
        return {"checkbox": brut.lower() in {"true", "vrai", "oui", "x", "1"}}
    return {"rich_text": [{"text": {"content": brut[:2000]}}]}


def cmd_whoami(_: argparse.Namespace) -> None:
    moi = _appel("GET", "/users/me")
    print(f"{moi.get('name', '?')} · {moi.get('type', '?')} · {moi.get('id', '?')}")


def cmd_search(args: argparse.Namespace) -> None:
    corps: dict = {"query": args.query, "page_size": args.limite}
    if args.type:
        corps["filter"] = {"property": "object", "value": args.type}
    for objet in _appel("POST", "/search", corps).get("results", []):
        print(f"{objet['object'][:4]:5} {objet['id']}  {_titre(objet)}")


def cmd_children(args: argparse.Namespace) -> None:
    resultat = _appel("GET", f"/blocks/{args.page}/children?page_size=100")
    for bloc in resultat.get("results", []):
        type_bloc = bloc.get("type", "?")
        contenu = bloc.get(type_bloc, {})
        texte = "".join(f.get("plain_text", "") for f in contenu.get("rich_text", []))
        if type_bloc == "child_page":
            texte = contenu.get("title", "")
        elif type_bloc == "child_database":
            texte = contenu.get("title", "")
        print(f"{type_bloc:18} {bloc['id']}  {texte[:70]}")


def cmd_db_create(args: argparse.Namespace) -> None:
    schema = json.loads(open(args.schema, encoding="utf-8").read())
    corps = {
        "parent": {"type": "page_id", "page_id": args.parent},
        "title": [{"text": {"content": schema["titre"]}}],
        "properties": schema["proprietes"],
    }
    if schema.get("description"):
        corps["description"] = [{"text": {"content": schema["description"]}}]
    base = _appel("POST", "/databases", corps)
    print(f"base créée : {base['id']}  {schema['titre']}")


def cmd_import(args: argparse.Namespace) -> None:
    schema = json.loads(open(args.schema, encoding="utf-8").read())
    types = {nom: definition_type(d) for nom, d in schema["proprietes"].items()}
    with open(args.csv, encoding="utf-8", newline="") as fichier:
        lignes = list(csv.DictReader(fichier))
    for index, ligne in enumerate(lignes, 1):
        proprietes = {}
        for colonne, brut in ligne.items():
            if colonne not in types:
                continue
            valeur = _valeur(types[colonne], brut or "")
            if valeur is not None:
                proprietes[colonne] = valeur
        if args.simulation:
            print(f"[simulation] {index:3} {list(proprietes)[:3]}")
            continue
        page = _appel(
            "POST", "/pages", {"parent": {"database_id": args.db}, "properties": proprietes}
        )
        print(f"{index:3} créée {page['id']}")
    print(f"{len(lignes)} lignes traitées.")


def definition_type(definition: dict) -> str:
    for cle in definition:
        if cle not in {"name", "description"}:
            return cle
    return "rich_text"


def cmd_raw(args: argparse.Namespace) -> None:
    corps = json.loads(open(args.data, encoding="utf-8").read()) if args.data else None
    print(json.dumps(_appel(args.methode.upper(), args.chemin, corps), ensure_ascii=False)[:4000])


def main() -> None:
    analyseur = argparse.ArgumentParser(description="CLI Notion minimal du projet.")
    sous = analyseur.add_subparsers(dest="commande", required=True)

    sous.add_parser("whoami", help="vérifie le jeton").set_defaults(fonction=cmd_whoami)

    p = sous.add_parser("search", help="cherche pages et bases")
    p.add_argument("query")
    p.add_argument("--type", choices=["page", "database"])
    p.add_argument("--limite", type=int, default=20)
    p.set_defaults(fonction=cmd_search)

    p = sous.add_parser("children", help="liste les blocs enfants d'une page")
    p.add_argument("page")
    p.set_defaults(fonction=cmd_children)

    p = sous.add_parser("db-create", help="crée une base à partir d'un schéma JSON")
    p.add_argument("--parent", required=True, help="identifiant de la page parente")
    p.add_argument("--schema", required=True)
    p.set_defaults(fonction=cmd_db_create)

    p = sous.add_parser("import", help="importe un CSV dans une base existante")
    p.add_argument("--db", required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--simulation", action="store_true", help="n'écrit rien, affiche seulement")
    p.set_defaults(fonction=cmd_import)

    p = sous.add_parser("raw", help="appel brut à l'API")
    p.add_argument("methode")
    p.add_argument("chemin")
    p.add_argument("--data")
    p.set_defaults(fonction=cmd_raw)

    args = analyseur.parse_args()
    args.fonction(args)


if __name__ == "__main__":
    main()
