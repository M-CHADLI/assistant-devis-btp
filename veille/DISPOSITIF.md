# Dispositif de veille — C6

> Ce fichier décrit **le rituel**, pas ses résultats. Les résultats sont les
> livrables de synthèse rangés à côté.
>
> Raison d'être : `docs/pilotage/COUVERTURE_RNCP.md` §E2 constate que la veille existante porte
> sur « IA et marché du travail », thématique que le référentiel n'accepte pas —
> C6 exige **un outil ou une réglementation mobilisée dans le projet**.

## Thématique retenue

**Unsloth et le fine-tuning de modèles MoE.**

C'est l'outil central du projet : `CLAUDE.md` pose Unsloth (LoRA) comme la
chaîne de fine-tuning, et gpt-oss-20b/120b comme des MoE quantifiés FP4. Une
évolution d'Unsloth ou de l'état de l'art LoRA/MoE change directement le mois
d'octobre.

Thématique **écartée** : devis BTP et TVA travaux. Sujet réel et déjà travaillé
(`docs/produit/CADRAGE_MODELE.md` §6), mais trop stable pour alimenter une séance
hebdomadaire pendant quatre mois. Il reste traité comme référentiel métier, pas
comme veille.

## Sources

Toutes les URL ci-dessous ont été **vérifiées actives** le 31/07/2026, et
revérifiées le 08/09/2026. Le fichier `sources.opml` les importe d'un coup dans
n'importe quel lecteur RSS.

> **Correction du 08/09/2026.** Le dépôt `unslothai/unsloth` héberge désormais
> l'**application de bureau** Unsloth, et ses releases GitHub (`v0.1.80x-beta`)
> ne disent rien des versions de la bibliothèque Python, publiées sur PyPI sous
> une numérotation distincte (`2026.9.2` au 08/09). Surveiller le seul flux
> GitHub revenait à croire suivre l'outil sans le suivre. Un sixième flux, celui
> de PyPI, a été ajouté ; le flux GitHub est conservé, l'application embarquant
> le moteur d'entraînement. Détail dans `seances/2026-09-08.md`, item 1.

| Source | Flux | Rôle | Rythme observé |
|---|---|---|---|
| **Unsloth — bibliothèque (PyPI)** | `pypi.org/rss/project/unsloth/releases.xml` | L'outil lui-même, celui qu'on installe. Priorité 1 | Soutenu |
| **Unsloth — releases GitHub** | `github.com/unslothai/unsloth/releases.atom` | L'application de bureau. **Ne porte pas** le changelog de la bibliothèque | Soutenu |
| **PEFT — releases** | `github.com/huggingface/peft/releases.atom` | L'état de l'art LoRA en pratique | Soutenu |
| **arXiv — MoE (cs.LG)** | requête Atom `export.arxiv.org/api/query` | La recherche MoE, triée par date | Quotidien, bruyant |
| **Hugging Face — blog** | `huggingface.co/blog/feed.xml` | Écosystème, modèles ouverts | Quotidien, large |
| **Ahead of AI** (S. Raschka) | `magazine.sebastianraschka.com/feed` | Mise en perspective | Irrégulier |

**Deux sources n'ont pas de flux et sont assumées comme telles :**

- **`unsloth.ai/blog`** — aucun flux RSS/Atom exposé (vérifié). C'est pourtant la
  source la plus dense : « Unsloth joins PyTorch ecosystem » (mai 2026),
  « Unsloth for AMD » (juillet 2026) n'apparaissent pas dans les releases GitHub.
  **À ouvrir à la main en début de chaque séance.** Une minute, pas plus.
- **`unslothai/unsloth-zoo`** — le flux existe mais est **vide** (aucune
  release publiée). Écarté tant qu'il le reste.

## Accessibilité des sources, et recoupement

Le référentiel demande deux choses au **choix** des sources, pas seulement à
leur contenu : privilégier celles qui respectent les normes d'accessibilité, et
confirmer ailleurs l'information retenue. Les deux se traitent ici.

### Le format du flux est la première mesure d'accessibilité

C'est le point que le projet contrôle vraiment. Une source consommée **par flux
Atom ou RSS** arrive comme du texte structuré : titre, date, corps. Pas de mise
en page dépendant du JavaScript, pas d'information portée par la seule couleur,
pas de navigation à la souris. Le même contenu se lit dans un lecteur d'écran,
dans un terminal, ou dans un lecteur RSS réglé à la taille de police voulue.

C'est pourquoi **cinq des six sources sont suivies par flux** et non par visite
du site. Ce n'était pas d'abord un choix d'accessibilité — c'était un choix de
rythme — mais il en produit l'effet, et il est conservé pour les deux raisons.

Le corollaire est la seule source sans flux, `unsloth.ai/blog`, ouverte à la
main en début de séance. C'est là que l'accessibilité dépend entièrement de
l'éditeur, et le dispositif l'assume comme un point faible plutôt que de le
taire.

### Ce que publient les éditeurs

Relevé le 08/09/2026, en lisant ce que chaque éditeur publie — pas en auditant
les sites, ce que ce projet n'a pas les moyens de faire.

| Éditeur | Ce qui est publié | Standard nommé |
|---|---|---|
| GitHub (Unsloth, PEFT) | Programme d'accessibilité, **rapports de conformité** publiés, système de composants accessibles par défaut, documentation d'usage au lecteur d'écran | Rapports de conformité publiés, standard à lire rapport par rapport |
| Substack (Ahead of AI) | Déclaration d'accessibilité, canal de signalement | **WCAG 2.1**, sans niveau de conformité annoncé |
| arXiv | Engagement écrit et adresse de signalement (`accessibility@arxiv.org`) | Aucun standard nommé |
| PyPI | Aucun lien d'accessibilité trouvé depuis la page d'accueil | Aucun |
| Hugging Face | Aucun lien d'accessibilité trouvé depuis la page d'accueil | Aucun |

**Ce que ce tableau ne dit pas.** Il compare des *déclarations*, pas des sites.
Un éditeur qui publie un rapport de conformité n'est pas nécessairement plus
accessible qu'un éditeur silencieux ; il est seulement vérifiable. Et l'absence
d'un lien en page d'accueil ne prouve pas l'absence de démarche.

**Ce qu'on en fait, concrètement.** Aucune source n'est écartée sur ce critère :
à thématique aussi étroite, l'écarter reviendrait à ne plus suivre l'outil du
projet. Le classement sert ailleurs — **à départager deux sources qui disent la
même chose.** C'est déjà arrivé : entre les notes de version GitHub et la page
PyPI d'un même paquet, le flux GitHub est celui dont l'éditeur publie des
rapports de conformité, et c'est un argument de plus pour le conserver malgré la
correction du 08/09.

### Recouper avant de retenir

Un item n'est retenu qu'après **confirmation par une seconde source
indépendante**, l'annonce de l'éditeur ne comptant pas comme sa propre
confirmation. Un billet de blog qui annonce un gain de performance se confirme
dans les notes de version, le dépôt, ou un article ; pas dans le billet suivant
du même auteur.

La séance du 08/09/2026 en donne le cas d'école, et il est instructif parce que
le recoupement a **infirmé** au lieu de confirmer : le flux GitHub d'Unsloth
donnait l'impression de suivre la bibliothèque Python. La vérification sur PyPI
a montré deux numérotations distinctes et un changelog qui n'est pas là où on le
croyait. Sans recoupement, la veille aurait continué à surveiller le mauvais
flux en toute confiance — c'est exactement le risque que ce critère vise.

## Le rituel

**Une heure, chaque vendredi matin.** C6 exige une récurrence planifiée d'au
moins une heure hebdomadaire, et surtout **la trace** de cette récurrence — pas
seulement le résultat final.

Déroulé, dans cet ordre :

1. **Ouvrir `unsloth.ai/blog`** (la source sans flux) — 1 min.
2. **Balayer le lecteur RSS** (six flux), ne rien lire encore — 5 min.
3. **Retenir 3 à 5 items maximum.** Le filtre n'est pas « est-ce
   intéressant » mais **« est-ce que ça change une décision du projet »**.
4. **Lire et consigner** chaque item retenu dans une entrée de séance — 40 min.
5. **Trancher** : chaque item retenu sort avec un verdict explicite (voir
   ci-dessous). Un item sans verdict n'a pas été traité — 10 min.

**Règle qui tient le reste : zéro item retenu est un résultat valide**, et il
s'écrit. Une semaine creuse consignée vaut mieux qu'un item gonflé pour
remplir la page.

## Verdicts possibles

Chaque item retenu sort avec **exactement un** de ces quatre verdicts :

| Verdict | Ce que ça déclenche |
|---|---|
| **Sans effet** | Consigné, rien d'autre. Le cas majoritaire, et c'est normal |
| **À surveiller** | Reconduit à la séance suivante. Deux reconductions sans suite → devient « sans effet » |
| **Impacte le projet** | Une question ouverte dans `docs/DECISIONS.md`, qui suivra le cycle normal d'arbitrage |
| **Impacte le planning** | Remonte dans `PLANNING.md`. Rappel : tout ajout se paie sur le mois en cours |

## Format des livrables

Deux niveaux, à ne pas confondre :

- **L'entrée de séance** — le compte rendu hebdomadaire. Court, daté, factuel.
  C'est la trace du rituel, et c'est elle que C6 réclame. Gabarit :
  `GABARIT-SEANCE.md`.
- **La synthèse de soutenance** — le support HTML (slides + script oral), au
  format des livrables déjà présents dans ce dossier. Construite *à partir* des
  entrées de séance, en fin de parcours. Pas avant : il n'y aurait rien à
  synthétiser.

## Ce que ce dispositif ne couvre pas

À traiter séparément, pour ne pas laisser croire que E2 est bouclé :

- **C7 — benchmark de services IA préexistants.** N'existe nulle part
  (`docs/pilotage/COUVERTURE_RNCP.md` §E2). C'est un document distinct, pas une sortie de la
  veille : pourquoi fine-tuner gpt-oss plutôt qu'appeler une API généraliste,
  avec les services écartés et le motif de chaque exclusion.
- **C8 — paramétrer un service IA préexistant.** L'API OCR du §6 du cadrage.
  À documenter comme telle : accès, configuration, monitorage, dépendances.
