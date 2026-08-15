# Dispositif de veille — C6

> Ce fichier décrit **le rituel**, pas ses résultats. Les résultats sont les
> livrables de synthèse rangés à côté.
>
> Raison d'être : `docs/LIVRABLES.md` §E2 constate que la veille existante porte
> sur « IA et marché du travail », thématique que le référentiel n'accepte pas —
> C6 exige **un outil ou une réglementation mobilisée dans le projet**.

## Thématique retenue

**Unsloth et le fine-tuning de modèles MoE.**

C'est l'outil central du projet : `CLAUDE.md` pose Unsloth (LoRA) comme la
chaîne de fine-tuning, et gpt-oss-20b/120b comme des MoE quantifiés FP4. Une
évolution d'Unsloth ou de l'état de l'art LoRA/MoE change directement le mois
d'octobre.

Thématique **écartée** : devis BTP et TVA travaux. Sujet réel et déjà travaillé
(`docs/CADRAGE_MODELE.md` §6), mais trop stable pour alimenter une séance
hebdomadaire pendant quatre mois. Il reste traité comme référentiel métier, pas
comme veille.

## Sources

Toutes les URL ci-dessous ont été **vérifiées actives** le 31/07/2026. Le
fichier `sources.opml` les importe d'un coup dans n'importe quel lecteur RSS.

| Source | Flux | Rôle | Rythme observé |
|---|---|---|---|
| **Unsloth — releases** | `github.com/unslothai/unsloth/releases.atom` | L'outil lui-même. Priorité 1 | Soutenu |
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

## Le rituel

**Une heure, chaque vendredi matin.** C6 exige une récurrence planifiée d'au
moins une heure hebdomadaire, et surtout **la trace** de cette récurrence — pas
seulement le résultat final.

Déroulé, dans cet ordre :

1. **Ouvrir `unsloth.ai/blog`** (la source sans flux) — 1 min.
2. **Balayer le lecteur RSS**, ne rien lire encore — 5 min.
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
| **Impacte le projet** | Une note dans `docs/NOTES.md`, qui suivra le cycle normal d'arbitrage |
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
  (`docs/LIVRABLES.md` §E2). C'est un document distinct, pas une sortie de la
  veille : pourquoi fine-tuner gpt-oss plutôt qu'appeler une API généraliste,
  avec les services écartés et le motif de chaque exclusion.
- **C8 — paramétrer un service IA préexistant.** L'API OCR du §6 du cadrage.
  À documenter comme telle : accès, configuration, monitorage, dépendances.
