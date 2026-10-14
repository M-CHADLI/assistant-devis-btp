---
description: Séance de veille C6 — balaye les sources, prémâche 3-5 candidats, puis écrit dans Notion les items tranchés
---

# Séance de veille C6

Déroule une séance de veille hebdomadaire. Le dispositif complet est dans
`veille/DISPOSITIF.md` — le relire si un doute apparaît.

## Règle de rédaction

Le **verdict** et le champ **« ce que ça change pour le projet »** s'écrivent avec les
mots de l'utilisateur. Ce sont les deux champs qui portent le jugement métier ; une
formulation générique les vide de leur sens.

Tu peux proposer une hypothèse d'impact — clairement étiquetée comme hypothèse — mais
elle est validée, corrigée ou rejetée par l'utilisateur avant d'être consignée. Si sa
formulation est confuse, lui renvoyer une reformulation à valider ; ne pas y substituer
la tienne en silence.

## Étape 1 — Balayer les sources

Six sources. Les cinq premières ont un flux, la dernière non.

| Source | À récupérer |
|---|---|
| Unsloth — releases | `https://github.com/unslothai/unsloth/releases.atom` |
| PEFT — releases | `https://github.com/huggingface/peft/releases.atom` |
| arXiv — MoE (cs.LG) | `https://export.arxiv.org/api/query?search_query=abs:%22mixture+of+experts%22+AND+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=10` |
| HuggingFace — blog | `https://huggingface.co/blog/feed.xml` |
| Ahead of AI | `https://magazine.sebastianraschka.com/feed` |
| **unsloth.ai/blog** | `https://unsloth.ai/blog` — **pas de flux, la source la plus dense** |

Récupérations **en parallèle**. Ne rien lire en profondeur : c'est un balayage.

**Filtrer sur la date** : ne considérer que ce qui est postérieur à la dernière séance
tenue. Une source silencieuse depuis la dernière fois est un résultat, pas un échec —
le dire.

## Étape 2 — Se situer

Avant de proposer quoi que ce soit, interroger Notion :

- Base **Séances de veille** — `collection://a9e2e8a5-2903-4b43-b12b-3a4c99e0a882`
  → date de la dernière séance tenue, séances planifiées non tenues
- Base **Items de veille** — `collection://c0a967a4-8161-48e3-9c45-07c00267be52`
  → items déjà consignés (**ne jamais proposer un doublon**)
  → items au verdict `À surveiller` et leur compteur `Reconductions`

## Étape 3 — Prémâcher 3 à 5 candidats, pas plus

Le filtre n'est **pas** « est-ce intéressant » mais **« est-ce que ça change une décision
du projet »**. Face au doute, écarter : six items médiocres coûtent plus cher que deux
qui comptent.

**Zéro candidat est un résultat valide et fréquent.** Le dire franchement plutôt que de
remplir. Une semaine creuse consignée vaut mieux qu'un item gonflé.

Présenter chaque candidat dans ce format compact, et pas un autre — **une ligne par
bloc**, pas un paragraphe :

```
n. <titre> — source, date
   QUOI       ce que c'est, en clair
   PRÉREQUIS  le concept à connaître pour comprendre
   IMPACT ?   hypothèse : quel document ou jalon serait touché
```

Le bloc `PRÉREQUIS` est celui qui fait apprendre — ne jamais le sauter, même quand
l'item paraît simple. Le bloc `IMPACT ?` est **toujours une hypothèse**, jamais une
conclusion, et nomme précisément la cible : `docs/produit/CADRAGE_MODELE.md` §4, le mois
d'octobre…

Le développement (les trois lignes détaillées) va dans le **corps de l'item** au moment
de l'écriture, pas dans la présentation en session.

Rappeler ensuite les items `À surveiller` à reconduire, avec leur compteur.
**Règle des deux reconductions** : à la deuxième reconduction sans suite, le verdict
bascule en `Sans effet` — le signaler, ne pas laisser traîner.

## Étape 4 — Recueillir les arbitrages

Pour chaque candidat retenu :

- le **verdict**, parmi exactement quatre : `Sans effet`, `À surveiller`,
  `Impacte le projet`, `Impacte le planning`
- **ce que ça change**, avec ses mots

## Étape 5 — Écrire dans Notion

Créer d'abord la **séance**, puis les **items** rattachés.

**Séance** (`collection://a9e2e8a5-2903-4b43-b12b-3a4c99e0a882`) :

| Propriété | Valeur |
|---|---|
| `Séance` | `Séance du AAAA-MM-JJ` |
| `Date` | la date du jour |
| `Statut` | `Tenue` |
| `Durée (min)` | la durée réelle, demandée à l'utilisateur |
| `Sources balayées` | les sources effectivement parcourues |
| `Compétence` | `https://app.notion.com/p/3c148e2936d081a3bc89f5b59d4c8d32` |

Dans le **corps** de la séance : volume balayé, décisions sorties, reconductions
traitées. Si rien n'a été retenu, écrire la ligne
*« Rien qui change une décision du projet cette semaine. »*

**Items** (`collection://c0a967a4-8161-48e3-9c45-07c00267be52`) — un par item retenu :
`Item`, `Séance` (relation), `Verdict`, `Lien`, `Source`, `Type`, `Thème`,
`Suite donnée`.

Dans le **corps** de chaque item : les blocs ① et ②, puis ce que ça change dans les
mots de l'utilisateur.

Ne pas toucher aux compteurs `Nb items retenus` et `Nb séances` : ce sont des rollups,
ils se calculent seuls.

## Étape 6 — Répercuter les suites

Selon les verdicts prononcés :

- `Impacte le projet` → proposer une question ouverte dans `docs/DECISIONS.md` (section « Questions ouvertes », idées non
  arbitrées), qui suivra le cycle normal
- `Impacte le planning` → proposer une ligne dans `PLANNING.md`, en rappelant que tout
  ajout se paie sur le mois en cours
- `À surveiller` → incrémenter `Reconductions` sur l'item existant s'il s'agit d'une
  reconduction

Proposer, ne pas écrire d'office : ces deux fichiers sont versionnés et engagent le
cadrage.

## Divergence connue, à ne pas résoudre en silence

`veille/DISPOSITIF.md` prévoit les comptes rendus dans `veille/seances/*.md`, alors que
la trace vit désormais dans Notion. **Non tranché.** Si l'utilisateur veut les deux, le
faire ; sinon lui rappeler une fois que `DISPOSITIF.md` mérite une mise à jour, et
passer à la suite.
