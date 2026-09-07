# Accessibilité des documents livrés

> **Pourquoi ce document existe.** Le référentiel réclame un « format qui
> respecte les recommandations d'accessibilité » dans **huit** compétences —
> C6-39, C8-57, C9-66, C11-85, C12-93, C13-101, C18-137, C20-151 — et il parle
> à chaque fois des **documents livrés**, pas de l'interface. L'interface, elle,
> a son standard : le RGAA 4.1, appliqué dans `docs/STORIES.md`.
>
> Une exigence répétée huit fois se traite une fois. Voici la règle du projet,
> écrite une seule fois, à laquelle chaque document renvoie.

## Le standard retenu

**RGAA 4.1**, transposition française de WCAG 2.1 niveau AA, complété par les
recommandations d'**Atalan – AcceDe** pour les documents bureautiques.

Le référentiel cite l'association Valentin Haüy, Atalan – AcceDe et Microsoft
comme exemples. Atalan est retenu parce que ses guides portent précisément sur
les documents (Word, PDF), là où les autres visent surtout le web ou un outil
propriétaire. Et le RGAA parce que c'est déjà le standard de l'interface : un
seul référentiel pour tout le projet, plutôt qu'un par surface.

## Les règles, pour les documents Markdown

Le dossier est rédigé en Markdown versionné. Neuf règles suffisent à le rendre
conforme, et elles se vérifient à l'œil.

| # | Règle | Pourquoi |
|---|---|---|
| 1 | **Un seul titre de niveau 1** par document, en tête. | C'est le titre du document. Deux `#` cassent la structure annoncée au lecteur d'écran. |
| 2 | **Pas de saut de niveau** : jamais un `###` directement sous un `#`. | La hiérarchie est le principal moyen de navigation d'un lecteur d'écran. |
| 3 | **Tout tableau a une ligne d'en-tête**, et ne sert qu'à des données. | Un tableau détourné pour la mise en page se lit cellule par cellule, sans ordre. |
| 4 | **Liens explicites** : jamais « ici », « ce lien », « voir ». | Les liens d'un document sont souvent listés hors contexte ; « ici » n'y veut rien dire. |
| 5 | **Aucune information portée par la seule couleur** — ni par le seul gras, ni par le seul emoji. | Un statut ✅ est toujours accompagné du mot ou d'une colonne de constat. C'est la règle appliquée dans `docs/AUDIT_JURY.md`. |
| 6 | **Toute image a une alternative textuelle** qui décrit l'information, pas le fichier. | Une image sans alternative est une information perdue. |
| 7 | **Les schémas ASCII sont précédés d'une phrase** qui dit ce qu'ils montrent. | Un art ASCII est illisible en synthèse vocale ; la phrase porte l'information, le schéma l'illustre. |
| 8 | **Les blocs de code portent leur langage** (` ```bash `, ` ```json `). | Cela permet la coloration syntaxique et signale la nature du bloc. |
| 9 | **Les abréviations sont développées à leur première occurrence.** | RGAA, HITL, MoE, DFD : le lecteur ne devine pas. |

## Ce qui vaut pour les livrables exportés

Les cinq livrables se présentent en PDF ou en document bureautique. Trois
exigences s'ajoutent alors, qui n'ont pas d'équivalent en Markdown :

- **Le PDF doit être balisé** (*tagged PDF*) : export depuis un traitement de
  texte avec les styles de titre, jamais une impression d'images de pages.
- **La langue du document doit être déclarée** (français) dans les propriétés.
- **L'ordre de lecture doit suivre l'ordre visuel** — à vérifier sur les pages
  à colonnes ou à encadrés.

Le devis `.docx` produit par `app/export.py` relève de la même règle : ses
titres passent par `add_heading`, ce qui produit de vrais styles Word et donc un
PDF balisé à l'export. Le tableau des postes a bien une ligne d'en-tête.

## Ce qui n'est pas conforme aujourd'hui

Écrit pour être corrigé, pas pour être caché.

- Les quatre supports HTML de veille de la thématique précédente
  (« IA et marché de l'emploi ») n'ont jamais été audités. Ils ne sont pas
  reconduits, donc non corrigés — mais s'ils sont montrés, ils comptent.
- Aucun livrable n'a encore été exporté en PDF : les trois exigences
  ci-dessus ne sont pour l'instant qu'une intention.
- `archive/renoassistant/` contient des images de user story sans alternative
  textuelle. Le dossier a une valeur historique et n'est pas livré ; s'il
  devait l'être, il faudrait les décrire.

## Comment le vérifier

Trois des neuf règles se contrôlent mécaniquement :

```bash
# Règle 1 — un seul titre de niveau 1 par document
for f in docs/*.md; do
  n=$(grep -c '^# ' "$f")
  [ "$n" -ne 1 ] && echo "$f : $n titres de niveau 1"
done

# Règle 2 — aucun saut de niveau dans la hiérarchie
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python - <<'PY'
import pathlib, re
for f in sorted(pathlib.Path("docs").glob("*.md")):
    prec = 0
    for i, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"^(#{1,6}) ", ligne)
        if not m:
            continue
        n = len(m.group(1))
        if prec and n > prec + 1:
            print(f"{f}:{i} saut de niveau {prec} vers {n}")
        prec = n
PY

# Règle 4 — liens dont le libellé ne dit rien
grep -rniE '\[(ici|ce lien|voir|cliquez[^]]*)\]\(' docs/ || echo "aucun lien non explicite"
```

Les six autres se lisent. Elles sont courtes exprès.
