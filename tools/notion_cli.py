#!/usr/bin/env python3
"""CLI Notion minimal — évite de charger 42 outils MCP dans le contexte.

Jeton : variable d'environnement NOTION_TOKEN (intégration interne Notion).
Version d'API : NOTION_VERSION, par défaut 2022-06-28.

    export NOTION_TOKEN=ntn_xxx
    python tools/notion_cli.py diagnostic          # pourquoi ça ne marche pas
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
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.notion.com/v1"

# Le jeton est cherché dans l'environnement, puis dans le .env du dépôt (qui
# est ignoré par git). Il n'est jamais affiché, jamais journalisé.
FICHIER_ENV = Path(__file__).resolve().parent.parent / ".env"


MODE_D_EMPLOI_JETON = (
    "  1. Crée une intégration interne sur https://www.notion.so/my-integrations\n"
    "  2. Copie le « Internal Integration Secret » (il commence par ntn_)\n"
    "  3. Ajoute la ligne suivante au fichier .env du dépôt (déjà ignoré par git) :\n"
    "       NOTION_TOKEN=ntn_...\n"
    "  4. Dans Notion, ouvre la page racine du projet → menu ⋯ → « Connexions »\n"
    "     → ajoute ton intégration. Sans ce partage, l'API ne voit rien."
)


def _empreinte(secret: str) -> str:
    """Douze caractères de sha256 : de quoi comparer deux jetons sans en montrer un."""
    return hashlib.sha256(secret.encode()).hexdigest()[:12]


def _jeton_optionnel() -> tuple[str, str] | None:
    """Rend (jeton, origine), ou None — sans jamais interrompre le programme.

    Chercher le jeton et décider de s'arrêter sont deux gestes distincts : le
    diagnostic a besoin de constater l'absence, pas de mourir dessus.
    """
    jeton = os.environ.get("NOTION_TOKEN")
    if jeton and jeton.strip():
        return jeton.strip().strip('"').strip("'"), "variable d'environnement"
    if FICHIER_ENV.exists():
        for ligne in FICHIER_ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
            ligne = ligne.strip()
            # tolère « NOTION_TOKEN=... », « export NOTION_TOKEN=... » et
            # « setx NOTION_TOKEN "..." » (le .env de ce poste mélange les formats)
            for prefixe in ("export ", "setx "):
                if ligne.startswith(prefixe):
                    ligne = ligne[len(prefixe):]
            if ligne.startswith("NOTION_TOKEN"):
                valeur = ligne[len("NOTION_TOKEN"):].lstrip("= ").strip()
                valeur = valeur.strip('"').strip("'")
                if valeur:
                    return valeur, f"fichier {FICHIER_ENV.name}"
    return None


def _jeton() -> str:
    trouve = _jeton_optionnel()
    if trouve is None:
        sys.exit("NOTION_TOKEN introuvable.\n" + MODE_D_EMPLOI_JETON)
    return trouve[0]


def _appel_brut(methode: str, chemin: str, corps: dict | None = None) -> tuple[int, dict]:
    """Appelle l'API et rend (code HTTP, corps décodé), sans jamais s'arrêter.

    Les erreurs de Notion sont porteuses de sens — `unauthorized`,
    `restricted_resource`, `object_not_found` ne se corrigent pas du même
    geste. Les faire disparaître dans un `sys.exit` jette le seul indice utile,
    et c'est ce qui rendait le diagnostic pénible.

    Code 0 : la requête n'a pas atteint Notion (réseau, DNS, proxy). Ce n'est
    pas une réponse de l'API et il ne faut pas la lire comme telle.
    """
    jeton = _jeton()
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
            return reponse.status, json.loads(reponse.read())
    except urllib.error.HTTPError as erreur:
        brut = erreur.read().decode(errors="replace")
        try:
            return erreur.code, json.loads(brut)
        except json.JSONDecodeError:
            return erreur.code, {"message": brut[:500]}
    except urllib.error.URLError as erreur:
        return 0, {"code": "reseau_indisponible", "message": str(erreur.reason)}


def _appel(methode: str, chemin: str, corps: dict | None = None) -> dict:
    """Variante qui s'arrête sur erreur, pour les commandes d'usage courant."""
    code, reponse = _appel_brut(methode, chemin, corps)
    if code != 200:
        detail = json.dumps(reponse, ensure_ascii=False)[:500]
        sys.exit(f"HTTP {code} sur {methode} {chemin}\n{detail}")
    return reponse


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


def cmd_diagnostic(args: argparse.Namespace) -> None:
    """Répond à « pourquoi ça ne marche pas » en séparant les causes.

    Le piège que cette commande existe pour lever : une intégration
    parfaitement valide dont on a oublié de partager la page rend une liste
    **vide**, pas une erreur. Sans ce déroulé, « mauvais jeton » et « page non
    partagée » produisent la même sortie muette, alors qu'ils ne se corrigent
    pas du même geste.

    Chaque échec s'arrête sur le geste exact qui le lève, et un seul.
    """
    # 1 — Le jeton est-il là, et d'où vient-il ?
    trouve = _jeton_optionnel()
    if trouve is None:
        print("✗ jeton      NOTION_TOKEN introuvable")
        print()
        print("Ce qui manque, et rien d'autre :")
        print(MODE_D_EMPLOI_JETON)
        sys.exit(1)
    jeton, origine = trouve
    if jeton.startswith("ntn_"):
        forme = "préfixe ntn_, intégration interne"
    elif jeton.startswith("secret_"):
        forme = "préfixe secret_, ancien format toujours accepté"
    else:
        forme = "préfixe inattendu — vérifier que la copie est complète"
    print(f"✓ jeton      {origine} · empreinte {_empreinte(jeton)} · {forme}")

    # 2 — Notion l'accepte-t-il ?
    code, moi = _appel_brut("GET", "/users/me")
    if code == 0:
        print(f"✗ réseau     {moi.get('message')}")
        print()
        print("La requête n'a pas atteint Notion. Rien ne peut être conclu sur le jeton.")
        sys.exit(1)
    if code == 401:
        print("✗ identité   401 — Notion refuse le jeton")
        print()
        print("Causes qui donnent toutes ce 401 : secret révoqué, tronqué à la")
        print("copie, ou appartenant à un autre espace de travail.")
        print("Geste : régénère le secret sur https://www.notion.so/my-integrations,")
        print("        puis remplace la ligne NOTION_TOKEN du .env.")
        sys.exit(1)
    if code != 200:
        print(f"✗ identité   HTTP {code} — {moi.get('code')} · {moi.get('message')}")
        sys.exit(1)
    espace = (moi.get("bot") or {}).get("workspace_name") or "(espace non communiqué)"
    print(f"✓ identité   {moi.get('name') or '(sans nom)'} · {moi.get('type')} · « {espace} »")

    # 3 — Le point décisif. La documentation de /search est explicite : sans
    #     paramètre « query », la réponse contient TOUT ce qui est partagé avec
    #     l'intégration. Le paramètre est donc omis, pas envoyé vide — une
    #     chaîne vide reste une requête, et ne porte pas la même promesse.
    #     Zéro résultat ne dit alors plus « rien ne correspond » mais « rien ne
    #     m'est partagé » : l'API ne rend aucune erreur dans ce cas.
    code, resultat = _appel_brut("POST", "/search", {"page_size": 100})
    if code != 200:
        print(f"✗ partage    HTTP {code} — {resultat.get('code')} · {resultat.get('message')}")
        sys.exit(1)
    partages = resultat.get("results", [])
    pages = [o for o in partages if o.get("object") == "page"]
    # Selon Notion-Version, une base se présente comme « database » (2022-06-28,
    # le défaut de ce CLI) ou comme « data_source » (versions récentes).
    bases = [o for o in partages if o.get("object") in ("database", "data_source")]
    if not partages:
        print("✗ partage    l'intégration ne voit aucune page et aucune base")
        print()
        print("Le jeton est bon : c'est le partage qui manque. Notion ne rend pas")
        print("d'erreur dans ce cas, seulement une liste vide — d'où cette commande.")
        print("Geste : dans Notion, ouvre la page racine du projet → menu ⋯ →")
        print("        « Connexions » → ajoute ton intégration. Les sous-pages")
        print("        héritent du partage : partager la racine suffit.")
        sys.exit(1)
    print(f"✓ partage    {len(pages)} page(s) et {len(bases)} base(s) visibles")
    for objet in partages[:15]:
        print(f"             {objet['object'][:4]:5} {objet['id']}  {_titre(objet)}")
    if len(partages) > 15:
        print(f"             … et {len(partages) - 15} autre(s)")

    # 4 — La page visée nommément, si elle a été donnée.
    manques: list[str] = []
    if args.page:
        code, page = _appel_brut("GET", f"/pages/{args.page}")
        if code == 200:
            print(f"✓ page       accessible — {_titre(page)}")
        elif code in (400, 404):
            print(f"✗ page       HTTP {code} — {page.get('code')} · {page.get('message')}")
            print("             Notion rend le même code pour « identifiant inconnu »")
            print("             et « page non partagée » : vérifier les deux.")
            manques.append("la page visée")
        else:
            print(f"✗ page       HTTP {code} — {page.get('code')} · {page.get('message')}")
            manques.append("la page visée")

    print()
    if manques:
        print("Diagnostic : jeton et partage bons, mais " + " et ".join(manques) + " échoue.")
        sys.exit(1)
    print("Diagnostic : la connexion est utilisable.")
    print("Le droit d'écriture, lui, ne se lit pas — l'API ne publie pas les")
    print("capacités d'une intégration. Un db-create refusé rendra 403")
    print("« restricted_resource » ; cela se corrige en cochant « Insert content »")
    print("sur l'intégration, puis en repartageant la page.")


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

    p = sous.add_parser(
        "diagnostic",
        help="dit pourquoi la connexion ne marche pas, et quel geste la répare",
    )
    p.add_argument("--page", help="identifiant d'une page dont on veut vérifier l'accès")
    p.set_defaults(fonction=cmd_diagnostic)

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
