# Planning — 4 mois (août → novembre 2026)

> Point de départ : 29/07/2026. Cadrage figé (pivot B2B vocal BTP du 16/08/2026 inclus), aucun
> code écrit.
> Règle qui tient tout le reste : **plus rien n'entre dans le périmètre.**
> Tout ajout se paie sur le mois en cours, jamais sur une marge imaginaire.

## Vue d'ensemble

| Mois | Jalon | Critère de sortie — vérifiable |
|---|---|---|
| **Août** | Référentiel métier v1 | 4 corps de métier (peinture, sols, plomberie, électricité), comblé par le LLM, relu et validé |
| **Septembre** | Dataset v1 + jeu de test gelé | ~2000 exemples, 150-200 tests écrits main |
| **Octobre** | 20b entraîné et mesuré | La preuve chiffrée existe |
| **Novembre** | 120b + démo + soutenance | Parcours chantier voix→devis joué de bout en bout |

---

## Août — le référentiel

Le mois change de nature avec le pivot, mais pas de plafond : le référentiel n'est plus une
collecte systématiquement sourcée (§6 de `docs/CADRAGE_MODELE.md`), c'est un référentiel comblé
par le LLM sur quatre corps de métier, relu et validé plutôt que collecté ligne à ligne.

1. Constituer le référentiel comblé par le LLM pour les quatre corps de métier (peinture, sols,
   plomberie, électricité) : rendements, taux de chute par type de pose, temps de séchage,
   consommables associés.
2. En parallèle, maintenir le scraping des fiches techniques fabricants comme exercice de
   collecte distinct (sert C1, `docs/LIVRABLES.md` — n'alimente plus directement le référentiel
   d'entraînement, cf. `docs/CADRAGE_MODELE.md` §6).
3. Relire et valider le référentiel comblé par le LLM — c'est le nouveau contrôle qualité de ce
   mois, à la place du sourcing ligne à ligne.
4. Figer le format du référentiel et sa version.
5. En parallèle, faire valider les seuils du §4 de `docs/DISPOSITIF_AGENT.md`.

**Sortie :** référentiel v1 versionné, quatre corps de métier. Le plafond de 2-3 semaines tient
toujours — décision assumée du pivot, à surveiller en pratique une fois le travail commencé
(spec, Section 5).

## Septembre — les données

Inchangé dans sa forme. Porte plus loin qu'avant : le référentiel non sourcé systématiquement
rend le jeu de test manuel encore plus central.

1. Écrire le schéma JSON détaillé de chaque `payload`.
2. Écrire **à la main** 150-200 exemples de test, répartis selon les cinq familles du §4.2 du
   dispositif. **Les geler.** Ils ne bougent plus.
3. Construire le pipeline de génération synthétique, adossé au référentiel comblé par le LLM.
4. Générer ~2000 exemples, dont ~72 % avec `reasoning`, `mention` répartie en transverse
   (~15 % simple, ~5 % forte) — les cas plomberie/électricité rendent les exemples `mention
   forte` réels, pas hypothétiques.
5. Relire un échantillon à la main. C'est le seul contrôle honnête.

**Sortie :** dataset v1 + jeu de test gelé, dans deux fichiers distincts qui ne se croisent
jamais.

## Octobre — la preuve

Inchangé pour l'essentiel. Le code déterministe à écrire perd la brique facture (retirée du
produit, `docs/CADRAGE_MODELE.md` §4) — légèrement allégé.

1. Mesurer le **20b brut** sur le jeu de test, avec un prompt système sérieux (schéma décrit +
   exemple few-shot). C'est la baseline ; la sous-prompter invaliderait tout.
2. LoRA sur le 20b via Unsloth. Itérer : c'est là que le dataset se corrige.
3. Remesurer. Les 8 métriques du §4.3 du dispositif, la n° 1 étant le taux de JSON valide — voir
   `docs/CADRAGE_MODELE.md` §7 pour ce qu'elle démontre désormais.
4. Écrire le code déterministe : requêtes référentiel/catalogue, calculs, devis, injection des
   prix. Le modèle ne calcule rien. Pas de brique facture.

**Sortie :** un tableau brut vs fine-tuné. Si l'écart n'est pas là, il reste un mois — c'est
précisément pour ça que ce jalon est en octobre et pas en novembre.

## Novembre — la démo

Simplifié par le pivot : l'interface à deux sessions simultanées disparaît. Une seule interface
(artisan, capture vocale + validation + export) à faire tenir.

1. LoRA sur le **120b** (65 Go, Unsloth). Démo, pas preuve.
2. Interface web, **une seule session** : capture vocale, reformulation, validation artisan,
   export Word.
3. Répéter le parcours chantier continu multi-corps de métier (peinture, sols, plomberie,
   électricité) en entier, plusieurs fois, avec une **correction artisan provoquée
   volontairement** sur un des corps de métier (démontre le signal qualité en direct) — y compris
   les cas `mention forte`, gpt-oss ayant des refus pré-entraînés qui ressortent en démo.
4. Supports de soutenance, avec l'argumentaire recentré sur fiabilité du format et qualité de
   structuration vocal → devis (`docs/CADRAGE_MODELE.md` §7).

**Sortie :** parcours voix → devis joué sans filet, côté artisan uniquement.

---

## Marges et points de rupture

- **Le mois d'octobre est la vraie marge.** Si le référentiel glisse en septembre, le dataset
  glisse en octobre et il ne reste plus rien pour itérer.
- **Si le calendrier dérape**, ce qui saute dans l'ordre : le 120b, puis le second cercle. Le
  repli « interface à une seule fenêtre » de l'ancien cadrage n'existe plus — il n'y a plus de
  session client à replier, puisqu'il n'y en a qu'une. Au-delà du 120b et du second cercle,
  **rien** n'est négociable : ni le jeu de test, ni le référentiel, ni le devis vocal sur les
  quatre corps de métier.
- **Ce qui n'est pas dans ce planning n'est pas dans le projet.**
