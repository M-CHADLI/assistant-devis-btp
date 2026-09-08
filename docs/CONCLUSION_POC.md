# Conclusion de la preuve de concept

> Ce document conclut la preuve de concept et énonce la décision qu'elle
> permet. Il répond au critère C15-113. Il ne décrit pas ce que le produit
> devrait faire — cela relève de `docs/CADRAGE_MODELE.md` — mais ce qu'il a
> **fait**, mesuré le 08/09/2026, et ce qu'on peut en décider.
>
> **Structure du document.** Titres hiérarchisés sans saut de niveau, tableaux
> avec ligne d'en-tête, aucune information portée par la seule couleur —
> conformément à `docs/ACCESSIBILITE_DOCUMENTS.md`.

## La question posée

Une seule, et elle porte tout le projet :

> **Un modèle de langage local peut-il produire un devis de rénovation fiable
> sans jamais calculer un montant ?**

Le pari du cadrage est que la réponse tient dans une frontière : le modèle
*décrit* (intention, lots, quantités), du code Python déterministe *calcule*
(catalogue, conditionnement, remises, TVA). Si cette frontière tient, un modèle
imparfait reste utilisable. Si elle ne tient pas, aucun fine-tuning ne rattrapera
un prix halluciné.

## Le protocole

`tools/parcours_bout_en_bout.py` déroule **24 étapes** contre le produit réel :
serveur FastAPI lancé, `gpt-oss:20b` servi par Ollama en local, catalogue réel,
document `.docx` écrit sur le disque. Rien n'est simulé — c'est ce qui le
distingue de la suite `pytest`, qui remplace le modèle par une fonction factice
pour tester le code.

Le parcours a été **exécuté cinq fois de suite** le 08/09/2026 entre 05 h 57 et
06 h 01, sur la machine de développement (pas la DGX Spark cible).

| Élément | Valeur |
|---|---|
| Exécutions du parcours | 5 |
| Étapes réussies | 24 sur 24, aux cinq exécutions |
| Appels au modèle | 21 |
| Tours de dialogue | 25 |
| Modèle | `gpt-oss:20b`, brut, non fine-tuné |
| Durée d'une exécution | ~46 s |

Cinq exécutions et vingt-et-un appels : c'est un **échantillon petit**, et il
faut le dire avant d'en tirer quoi que ce soit. Ces chiffres indiquent un ordre
de grandeur, ils ne mesurent pas une performance. La mesure honnête viendra du
jeu d'essai de 150 à 200 exemples écrits à la main, qui n'existe pas encore.

## Ce que la preuve de concept établit

### La frontière modèle / code tient

C'est le résultat principal, et il est net.

| Métrique | Seuil | Relevé | Verdict |
|---|---|---|---|
| nº 7 — prix ou référence inventés | 0 | **0** sur 21 appels | conforme |
| nº 8 — latence d'un devis (p95) | ≤ 30 s | **12,82 s** | conforme |

Aucun montant n'est jamais sorti du modèle. Le parcours le vérifie deux fois
plutôt qu'une : il contrôle qu'**avant** la validation de structure (HITL-2) la
réponse ne porte aucune clé de prix, puis qu'**après** validation les quatre
lignes sont chiffrées et que chacune se recalcule depuis ses propres colonnes,
remises comprises. Le total TTC observé — 620,81 € sur le chantier de
démonstration — vient du catalogue, jamais du modèle.

### Les garde-fous tiennent aussi

Sur les cinq exécutions : 5 tentatives d'injection neutralisées et signalées, 5
demandes hors périmètre nommées plutôt qu'esquivées, l'escalade obtenue **sans
appel modèle**, et le devis qui survit à l'escalade. La session se referme et
l'API redevient inaccessible.

### La latence n'est pas le problème

12,82 s en p95 sur une machine qui n'est pas la cible, contre un seuil à 30 s.
Le goulot annoncé au cadrage — la bande passante mémoire — ne s'est pas
manifesté à cette taille de modèle. C'est une inquiétude qu'on peut ranger pour
le 20b ; elle reviendra pour le 120b.

## Ce que la preuve de concept invalide

Un seul point, et c'est celui qui justifie la suite du projet.

| Métrique | Seuil | Relevé | Verdict |
|---|---|---|---|
| nº 1 — taux de JSON valide | ≥ 98 % | **71,4 %** (15 sur 21) | **sous le seuil** |

**Le modèle brut échoue à produire du JSON conforme trois fois sur dix.** Six
appels sur vingt-et-un ont dû être repris — le compteur de reprises affiche
exactement 6, ce qui confirme que chaque échec a été rattrapé et qu'aucun n'est
passé en silence.

Ce chiffre est la **valeur de référence** du projet. C'est contre lui que se
mesurera l'apport du fine-tuning, et c'est la raison d'être du protocole de
preuve « 20b brut bien promptté contre 20b fine-tuné » (`docs/CADRAGE_MODELE.md`).

Deux lectures s'en dégagent, et elles ne disent pas la même chose :

1. **Le produit fonctionne quand même.** 24 étapes sur 24, cinq fois sur cinq,
   avec un modèle qui rate trois requêtes sur dix. La reprise et le moteur
   déterministe absorbent l'échec. C'est la robustesse recherchée.
2. **Cette robustesse a un prix.** Chaque reprise est un appel de plus, donc de
   la latence et de l'énergie ; et une reprise qui échouerait à son tour
   remonterait à l'artisan. Un taux de 71 % ne se démontre pas devant un jury
   sans expliquer pourquoi on n'a pas fait mieux.

## Ce que la preuve de concept ne dit pas

À dire avant qu'on ne le lise à sa place :

- **Vingt-et-un appels ne sont pas une mesure.** Aucun intervalle de confiance
  n'est calculable. 71,4 % est une indication, pas un taux.
- **Un seul scénario.** Le chantier de démonstration — un salon, peinture et
  sol — est celui que le parcours déroule. Il n'exerce ni la plomberie ni
  l'électricité, donc ni les cas `mention forte`.
- **Aucun utilisateur réel.** La dictée du parcours est un texte écrit, pas une
  transcription d'artisan sur chantier.
- **Pas de pré-production.** Tout tourne en local ; C15-112 reste partiel pour
  cette raison.
- **Pas la machine cible.** La DGX Spark n'a pas encore servi ; les latences du
  120b restent inconnues.
- **Les métriques 2 à 6 ne sont pas mesurées** — exactitude des quantités,
  complétude des lots, rappel des consommables, justesse de la mention,
  détection hors périmètre. Elles demandent le jeu d'essai annoté à la main.
  Elles sont déclarées non mesurées, pas approchées.

## La décision

**Poursuivre l'architecture, fine-tuner pour lever le seul verrou mesuré.**

Trois décisions en découlent, chacune adossée à un relevé ci-dessus :

| Décision | Ce qui la fonde |
|---|---|
| **Garder la frontière modèle / code telle quelle.** Elle n'est pas à assouplir pour gagner en fluidité. | 0 prix inventé sur 21 appels, et un produit qui reste juste malgré 6 échecs modèle. |
| **Faire du taux de JSON valide la métrique nº 1 du fine-tuning**, et de son passage au-dessus de 98 % le critère de bascule vers la démonstration. | 71,4 % relevé contre 98 % visé : c'est le seul seuil franchi dans le mauvais sens. |
| **Conserver `gpt-oss:20b` comme modèle de preuve** et réserver le 120b à la démonstration. | Le 20b suffit à exercer le parcours entier en 46 s ; la preuve se joue sur l'écart brut/fine-tuné, pas sur la taille. |

**Ce qui reste conditionnel.** Si, jeu d'essai en main, le fine-tuning ne
franchissait pas 98 %, la décision à réexaminer ne serait pas l'architecture —
elle a tenu — mais la place de la reprise : la rendre explicite dans le produit
plutôt que silencieuse, et l'annoncer comme telle en soutenance.

**Le prochain jalon n'est pas du code.** C'est l'écriture à la main du dataset
et du jeu d'essai. La chaîne qui les validera existe déjà
(`docs/CHAINE_MLOPS.md`), et elle attend sa matière.

---

*Relevés du 08/09/2026, 05 h 57 – 06 h 01, `gpt-oss:20b` via Ollama, cinq
exécutions de `tools/parcours_bout_en_bout.py`. Les chiffres cités sont lus dans
`/api/metriques` à l'issue des cinq exécutions, pas recopiés de mémoire.*
