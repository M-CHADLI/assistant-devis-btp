# Planning — 4 mois (août → novembre 2026)

> Règle qui tient tout le reste : **plus rien n'entre dans le périmètre.**
> Tout ajout se paie sur le mois en cours, jamais sur une marge imaginaire.

## Où on en est — 12/10/2026

Constaté dans le dépôt, sans anticiper :

- **Cadrage figé**, implémentation engagée : API, moteur de devis déterministe, front, chaîne de
  données, chaîne du modèle déclarée, suite de tests (`docs/produit/STORIES.md` porte l'état story par
  story).
- **Baseline mesurée** : `gpt-oss:20b` brut produit du JSON conforme dans 71,4 % des cas
  (`docs/modele/CONCLUSION_POC.md`) — c'est la valeur contre laquelle se mesurera le fine-tuning.
- **Pas encore fait** : le jeu de test de 150-200 exemples écrits à la main et le dataset ne sont
  pas écrits ; la chaîne du modèle n'exécute donc que le test des données, les trois autres
  étapes se déclarent `ignoré` (`docs/modele/CHAINE_MLOPS.md`). Le fine-tuning n'a pas eu lieu.
- **Pas de dépôt Git distant** : les chaînes CI/CD sont écrites mais n'ont jamais tourné.
- **Changement d'infrastructure le 12/10** : plus de DGX Spark. L'application et le modèle
  passent sur GCP (`docs/DECISIONS.md` D-18 à D-21) ; le 120b est suspendu. **Conséquence : aucun modèle
  n'est disponible, le parcours principal ne fonctionne plus** tant que le service de modèle
  n'est pas déployé. La mise en
  production est le sprint 2 (`DOSSIER_SPRINT_1.md` §8).

Le jalon d'octobre (« 20b entraîné et mesuré ») dépend donc du jeu de test, qui n'existe pas
encore : c'est le chemin critique.

## Vue d'ensemble

| Mois | Jalon | Critère de sortie — vérifiable |
|---|---|---|
| **Août** | Référentiel métier v1 | 4 corps de métier (peinture, sols, plomberie, électricité), comblé par le LLM, relu et validé |
| **Septembre** | Dataset v1 + jeu de test gelé | ~2000 exemples, 150-200 tests écrits main |
| **Octobre** | 20b entraîné et mesuré | La preuve chiffrée existe |
| **Novembre** | Démo + soutenance | Parcours chantier voix→devis joué de bout en bout, en production |

---

## Août — le référentiel

1. Constituer le référentiel comblé par le LLM pour les quatre corps de métier : rendements, taux
   de chute par type de pose, temps de séchage, consommables associés.
2. En parallèle, maintenir le scraping des fiches techniques fabricants comme exercice de
   collecte distinct (sert C1, n'alimente pas le référentiel d'entraînement).
3. Relire et valider le référentiel comblé par le LLM — c'est le contrôle qualité du mois.
4. Figer le format du référentiel et sa version.
5. En parallèle, faire valider les seuils du §4 de `docs/produit/DISPOSITIF_AGENT.md`.

**Sortie :** référentiel v1 versionné, quatre corps de métier.

## Septembre — les données

1. Écrire le schéma JSON détaillé de chaque `payload`.
2. Écrire **à la main** 150-200 exemples de test, répartis selon les cinq familles du §4.2 du
   dispositif. **Les geler.** Ils ne bougent plus.
3. Construire le pipeline de génération synthétique, adossé au référentiel.
4. Générer ~2000 exemples, dont ~72 % avec `reasoning`, `mention` répartie en transverse
   (~15 % simple, ~5 % forte).
5. Relire un échantillon à la main. C'est le seul contrôle honnête.
6. Benchmark STT sur un corpus maison : une dizaine de dictées réelles enregistrées par nos soins
   (les WER publiés mesurent des corpus de lecture, pas une dictée de chantier). Voir
   `docs/modele/BENCHMARK_STT.md` §8.

**Sortie :** dataset v1 + jeu de test gelé, dans deux fichiers distincts qui ne se croisent
jamais.

## Octobre — la preuve

1. Mesurer le **20b brut** sur le jeu de test, avec un prompt système sérieux (schéma décrit +
   exemple few-shot). C'est la baseline ; la sous-prompter invaliderait tout.
2. Fixer les hyperparamètres du LoRA sur une lecture argumentée (`docs/DECISIONS.md` Q-07), puis
   LoRA sur le 20b via Unsloth, sur une machine GPU à trancher (Q-13). Itérer : c'est là que le
   dataset se corrige.
3. Remesurer. Les 8 métriques du §4.3 du dispositif, la n° 1 étant le taux de JSON valide.
4. Code déterministe : requêtes référentiel/catalogue, calculs, devis, injection des prix. Le
   modèle ne calcule rien.

**Sortie :** un tableau brut vs fine-tuné. Si l'écart n'est pas là, il reste un mois — c'est
précisément pour ça que ce jalon est en octobre et pas en novembre.

## Novembre — la démo

1. Servir le modèle fine-tuné par le service de production, à la place du modèle brut.
2. Interface web, **une seule session** : capture vocale, reformulation, validation artisan,
   export Word.
3. Répéter le parcours chantier continu multi-corps de métier plusieurs fois, avec une
   **correction artisan provoquée volontairement** sur un des corps de métier (démontre le signal
   qualité en direct) — y compris les cas `mention forte`, gpt-oss ayant des refus pré-entraînés
   qui ressortent en démo.
4. Supports de soutenance, argumentaire centré sur la fiabilité du format et la qualité de
   structuration vocal → devis (`docs/produit/CADRAGE_MODELE.md` §7).

**Sortie :** parcours voix → devis joué sans filet, côté artisan uniquement.

---

## Marges et points de rupture

- **Le mois d'octobre est la vraie marge.** Si le jeu de test glisse, le dataset glisse et il ne
  reste plus rien pour itérer.
- **Si le calendrier dérape**, ce qui saute : le second cercle. Le 120b est déjà suspendu.
  Au-delà, **rien** n'est négociable : ni le jeu de test, ni le référentiel, ni le devis vocal
  sur les quatre corps de métier.
- **Ce qui n'est pas dans ce planning n'est pas dans le projet.**
