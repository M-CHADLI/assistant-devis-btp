"""Étape 6 — lecture du catalogue en base, en ligne de commande.

Le contrat de lecture lui-même vit dans `app/catalogue_base.py` : c'est le
produit qui lit sa base, pas l'outillage. Ce module n'est qu'un point d'entrée
en ligne de commande, pour vérifier d'un coup d'œil ce que la chaîne a produit.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.requetes
```
"""
from __future__ import annotations

from app.catalogue_base import (familles_incompletes, ouvrir,
                                synthese_par_famille, tracabilite)


def main() -> int:
    cx = ouvrir()
    try:
        print("Sources")
        for s in tracabilite(cx):
            print(f"  {s['role']:9} {s['nom']} — {s['licence']}"
                  f" ({s['lignes_brutes']} lignes brutes)")
        print("\nSynthèse par famille")
        for f in synthese_par_famille(cx):
            print(f"  {f['code']:26} {f['nombre_de_produits']:2} produits"
                  f"  {f['prix_min']:>8} → {f['prix_max']:>8} €"
                  f"  ({f['qualite_correspondance']})")
        print("\nFamilles incomplètes")
        for f in familles_incompletes(cx):
            manques = [n for n, m in (("facteur", f["facteur_manquant"]),
                                      ("densité", f["densite_manquante"])) if m]
            print(f"  {f['code']:26} {f['qualite_correspondance']:8}"
                  f" manque : {', '.join(manques) or '—'}")
    finally:
        cx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
