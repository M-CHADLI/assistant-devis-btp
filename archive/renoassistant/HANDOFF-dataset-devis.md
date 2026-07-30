# HANDOFF — Dataset devis français (bricolage) — ARCHIVÉ

> **Statut : archivé le 29/07/2026.** Ce document décrivait un projet d'*extraction
> structurée* sur devis (texte/image → JSON), distinct du projet en cours.
>
> **Son contenu métier a été absorbé** dans `CADRAGE_MODELE.md` §6 (« Contenu
> réglementaire du référentiel ») : TVA à trois taux et ses pièges, mentions
> obligatoires BTP, cas auto-entrepreneur, unités du secteur.
>
> **Ce qui n'a pas été repris** : les pistes de datasets HuggingFace, le corpus
> Lucie, la stratégie de génération synthétique de devis, les pièges DuckDB.
> L'extraction ne fait plus partie du fine-tuning — elle passe par une API OCR
> externe, occasionnellement, à l'inscription d'un artisan.
>
> Conservé pour trace de la recherche réglementaire.

Contexte repris d'une session de recherche du 29/07/2026.

## Objectif

Constituer un dataset pour entraîner un LLM à l'extraction structurée sur des
**devis français du secteur bricolage / travaux** (texte ou image → JSON).

## Pistes explorées — verdicts

| Piste | Verdict | Détail |
|---|---|---|
| `OpenLLM-France/Lucie-Training-Dataset` | **ABANDONNÉE** | Scan SQL du subset LEGI : 5 résultats. Corpus généraliste, aucun devis réel. Un devis est un document privé, absent des crawls web et du corpus législatif. |
| `GokulRajaR/invoice-ocr-json` | **UTILE (calibration)** | 5 189 factures EN, images + JSON. Sert à calibrer les mises en page plausibles, pas de traduction massive prévue. |
| `manuelaschrittwieser/invoice-extraction-dataset-v2` | Secondaire | 601 ex. texte→JSON, format instruction-tuning. |
| DECP / BOAMP (data.gouv.fr) | **À EXPLOITER** | Marchés publics FR : montants réels, libellés de prestations, SIRET, noms d'entreprises. Sert à peupler les générateurs avec du vocabulaire authentique. |
| Lucie (LEGI / OpenData) | Usage résiduel | Correct pour du *continued pretraining* français juridico-commercial. Pas pour l'extraction. |

## Décision structurante

**La génération synthétique devient la voie principale**, pas un complément.

Justification : contrôle total de la distribution (secteurs, montants, mises en
page, cas limites), vérité terrain gratuite (le JSON est généré avant le texte),
volume illimité. Pour de l'extraction structurée, un synthétique bien conçu bat
un réel mal annoté.

Domaine ciblé : **bricolage / travaux** (peinture, plomberie, électricité,
menuiserie, carrelage, plâtrerie, isolation, sols).

## Spécificités métier à encoder

Le domaine est fortement codifié — c'est ce qui rend le synthétique crédible.

**TVA à trois taux** (le point technique central du secteur) :
- 20 % — neuf, logement < 2 ans, agrandissement, gros équipements
- 10 % — amélioration / entretien / aménagement, logement achevé > 2 ans
- 5,5 % — rénovation énergétique et travaux induits, logement > 2 ans

Pièges à modéliser volontairement : les fournitures **posées par l'entreprise**
suivent le taux réduit, celles achetées séparément par le client sont à 20 % ;
certains gros équipements restent à 20 % même posés. Un devis réaliste mélange
souvent plusieurs taux → la ventilation TVA par taux est un champ à part entière.
*(Détail réglementaire à revérifier avant figeage du générateur.)*

**Mentions obligatoires devis BTP** : n° devis, dates d'émission et de validité,
coordonnées émetteur (SIRET, RCS, APE/NAF, TVA intracom.), **assurance décennale**
(assureur + n° contrat + couverture géographique), client, adresse de chantier
(parfois ≠ adresse client), détail par poste, ventilation TVA, acompte (souvent
30 %), délai d'exécution, mention « Bon pour accord ».

**Cas limite important** : auto-entrepreneur → mention « TVA non applicable,
art. 293 B du CGI », pas de ligne de TVA. Doit figurer dans le dataset.

**Unités** : m², ml, m³, u, h, j, forfait, ens., kg.

**Identifiants** : SIRET/SIREN valides au sens Luhn, TVA intracom. dérivée du
SIREN — pour du réalisme de surface, tout fictif.

## Points ouverts (à trancher avant implémentation)

1. **Texte brut vs image** — détermine l'architecture (LLM texte vs VLM/OCR). Le
   générateur de *contenu* est commun aux deux, donc non bloquant pour démarrer.
2. **Schéma cible** — plat (liste de lignes) ou hiérarchique (lots → lignes) ?
3. **Volume** — plancher utile ~1 000 ; cible raisonnable 5 000–10 000.
4. **Modèle de base** — Mistral-7B envisagé, non arbitré.
5. Ratio synthétique / traduit / réel.

## Pièges techniques rencontrés (DuckDB / HF Data Studio)

À garder si un scan de dataset revient sur la table :

- `LOWER(text) LIKE '%TTC%'` ne matche **jamais**. Utiliser `ILIKE`.
- En DuckDB, `~` = `regexp_full_match` (≠ PostgreSQL). Utiliser `regexp_matches()`
  pour du match partiel.
- `LIKE` est sensible à la casse ; `ILIKE` ne l'est pas.
- `SELECT *, COUNT(*) ... GROUP BY ALL` groupe sur toutes les colonnes → chaque
  groupe = 1 ligne, le compte vaut 1 partout. Utiliser `COUNT(*) OVER ()` ou une
  requête d'agrégation séparée.
- Filtrer sur `source` ne réduit **pas** le volume lu : il faut changer de
  *subset* dans le sélecteur (la vue devient `<config>_train`).
- `'%ht%'` matche à l'intérieur de mots courants → exiger une limite de mot.

## Prochaine étape

Finaliser la **conception** (schéma JSON, taxonomie des prestations, gabarits de
mise en page, stratégie de variation) avant tout code. L'utilisateur a
explicitement demandé de ne pas générer de code à ce stade.

## Fichiers de la session précédente

Dans `/mnt/user-data/outputs/` : analyses HF datasets, index de ressources,
guides SQL Lucie. Les guides Lucie sont conservés pour trace mais la piste est
close ; les requêtes SQL qu'ils contiennent portent les bugs de casse listés
ci-dessus et ne doivent pas être réutilisées telles quelles.
