# Planning — 4 mois (août → novembre 2026)

> Point de départ : 29/07/2026. Cadrage figé, aucun code écrit.
> Règle qui tient tout le reste : **plus rien n'entre dans le périmètre.**
> Tout ajout se paie sur le mois en cours, jamais sur une marge imaginaire.

## Vue d'ensemble

| Mois | Jalon | Critère de sortie — vérifiable |
|---|---|---|
| **Août** | Référentiel métier v1 | 20-30 matériaux, chaque valeur sourcée |
| **Septembre** | Dataset v1 + jeu de test gelé | ~2000 exemples, 150-200 tests écrits main |
| **Octobre** | 20b entraîné et mesuré | La preuve chiffrée existe |
| **Novembre** | 120b + démo + soutenance | Parcours salon joué de bout en bout |

---

## Août — le référentiel

Le mois le plus ingrat et le plus décisif : sans lui, le dataset apprend des
valeurs plausibles et fausses (§6 de `docs/CADRAGE_MODELE.md`).

1. Arrêter la liste des fabricants (peinture, sous-couche, enduit, stratifié,
   sous-couche de sol, barres de seuil) et récupérer les fiches techniques.
2. Extraire : rendements, taux de chute par type de pose, temps de séchage,
   consommables associés. **Une ligne = une valeur = une source.**
3. Figer le format du référentiel et sa version.
4. En parallèle, faire valider les seuils du §4 de `docs/DISPOSITIF_AGENT.md`.

**Sortie :** référentiel v1 versionné. Trancher aussi la voix (oui/non) — elle
n'impacte pas le modèle, mais elle impacte la démo, et on ne décide pas ça en
novembre.

## Septembre — les données

1. Écrire le schéma JSON détaillé de chaque `payload`.
2. Écrire **à la main** 150-200 exemples de test, répartis selon les cinq
   familles du §4.2 du dispositif. **Les geler.** Ils ne bougent plus.
3. Construire le pipeline de génération synthétique, adossé au référentiel.
4. Générer ~2000 exemples, dont ~72 % avec `reasoning`, `mention` répartie en
   transverse (~15 % simple, ~5 % forte).
5. Relire un échantillon à la main. C'est le seul contrôle honnête.

**Sortie :** dataset v1 + jeu de test gelé, dans deux fichiers distincts qui ne
se croisent jamais.

## Octobre — la preuve

1. Mesurer le **20b brut** sur le jeu de test, avec un prompt système sérieux
   (schéma décrit + exemple few-shot). C'est la baseline ; la sous-prompter
   invaliderait tout.
2. LoRA sur le 20b via Unsloth. Itérer : c'est là que le dataset se corrige.
3. Remesurer. Les 8 métriques du §4.3 du dispositif, la n° 1 étant le taux de
   JSON valide.
4. Écrire le code déterministe : requêtes catalogue, calculs, devis, injection
   des prix. Le modèle ne calcule rien.

**Sortie :** un tableau brut vs fine-tuné. Si l'écart n'est pas là, il reste un
mois — c'est précisément pour ça que ce jalon est en octobre et pas en novembre.

## Novembre — la démo

1. LoRA sur le **120b** (65 Go, Unsloth). Démo, pas preuve.
2. Interface web, deux sessions simultanées (client / artisan).
3. Répéter le parcours salon en entier, plusieurs fois, y compris les cas
   `mention forte` — gpt-oss a des refus pré-entraînés qui ressortent en démo.
4. Supports de soutenance.

**Sortie :** parcours joué sans filet.

---

## Marges et points de rupture

- **Le mois d'octobre est la vraie marge.** Si le référentiel glisse en
  septembre, le dataset glisse en octobre et il ne reste plus rien pour itérer.
- **Si le calendrier dérape**, ce qui saute dans l'ordre : le 120b, puis le
  second cercle, puis l'interface à deux sessions (démontrable en une seule
  fenêtre). **Jamais** le jeu de test ni le référentiel.
- **Ce qui n'est pas dans ce planning n'est pas dans le projet.**
