# Journal des incidents

> **À quoi sert ce document.** La compétence C21 demande, pour chaque incident :
> la cause identifiée, la reproduction en environnement de développement, la
> procédure de débogage, la solution expliquée étape par étape, et son
> versionnement. Les messages de commit portent déjà la solution ; ils ne
> portent ni la reproduction ni le raisonnement qui a mené à la cause. C'est ce
> journal qui les porte.
>
> Structure conforme à `docs/ACCESSIBILITE_DOCUMENTS.md`.

## La procédure suivie, à chaque fois

Elle est identique pour les sept incidents ci-dessous, et c'est délibéré : une
procédure qui change à chaque incident n'en est pas une.

1. **Reproduire d'abord, comprendre ensuite.** Tant que le symptôme n'est pas
   reproductible à volonté, toute explication est une hypothèse.
2. **Écrire le test qui échoue, avant le correctif.** Il prouve la reproduction,
   et il devient le test de non-régression sans travail supplémentaire.
3. **Remonter à la cause, pas au symptôme.** Un symptôme corrigé sans sa cause
   revient sous une autre forme.
4. **Un correctif, un commit**, dont le message dit pourquoi et pas seulement
   quoi.
5. **Relancer la suite entière**, pas seulement le test concerné.

Commande de reproduction, commune à tous :

```bash
BTP_DONNEES=/tmp/donnees \
  VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync pytest -q
```

## Le tableau de bord

| Réf. | Symptôme | Gravité | Statut | Commit |
|---|---|---|---|---|
| INC-01 | Une demande de quantités ne remplissait jamais le devis | Majeure | Résolu | `e669883` |
| INC-02 | Un seul message pouvait coûter quatre appels au modèle | Majeure | Résolu | `e669883` |
| INC-03 | Deux visiteurs partageaient le même devis | Critique | Résolu | `e669883` |
| INC-04 | L'application ne démarrait que depuis la racine du dépôt | Mineure | Résolu | `e669883` |
| INC-05 | Ollama arrêté renvoyait une erreur 500 nue | Majeure | Résolu | `e669883` |
| INC-06 | Les mentions du devis s'affichaient « undefined » | Majeure | Résolu | `d783b9a` |
| INC-07 | Le fichier de verrouillage des dépendances avait dérivé | Mineure | Résolu | `7d29b6f` |

---

## INC-01 — Une demande de quantités ne remplissait jamais le devis

**Symptôme.** L'artisan dicte « il me faut les quantités pour les 22 m² de
peinture ». Le modèle répond correctement, avec `intent: "quantitatif"` et des
lots exploitables. Le devis reste vide. Aucune erreur, aucun message : le tour
passe et rien ne se produit.

**Reproduction.** Envoyer à `traiter_message` une réponse de modèle portant
`intent: "quantitatif"` avec au moins un lot valide, puis lire `session.devis`.

**Cause.** Le routeur de `app/pipeline.py` testait
`elif intent in ("devis", "lots"):`. La valeur `"quantitatif"` était pourtant
déclarée dans l'enveloppe de sortie (`docs/CADRAGE_MODELE.md`) et acceptée par
le schéma Pydantic. Une branche manquante, pas une erreur : le code tombait
dans le cas par défaut, qui ne fait rien.

**Ce qui a masqué le défaut.** Le prompt système ne décrivait pas la charge utile
attendue pour `quantitatif`. Le modèle produisait donc rarement cet `intent`, et
le trou ne se voyait qu'occasionnellement — le pire régime pour un défaut.

**Correctif.** Deux gestes, parce qu'un seul aurait laissé la moitié du
problème : ajout de `"quantitatif"` à la branche de routage, et ajout de la
description de sa charge utile au prompt système de `app/llm.py`.

**Test de non-régression.** `tests/test_pipeline.py::test_intent_quantitatif_est_route`

---

## INC-02 — Un seul message pouvait coûter quatre appels au modèle

**Symptôme.** Latence anormale sur les messages où le modèle produit un JSON
mal formé. L'objectif de latence du projet est p95 sous 30 secondes
(`docs/DISPOSITIF_AGENT.md` §4.3) ; on l'a dépassé sans comprendre pourquoi.

**Reproduction.** Un faux modèle qui compte ses appels et échoue
systématiquement. Le compteur montait à 4 pour un seul message utilisateur.

**Cause.** **Deux boucles de reprise superposées, écrites à des moments
différents et qui s'ignoraient.** `app/llm.py` réessayait deux fois en interne
sur un JSON illisible ; `app/pipeline.py` réessayait deux fois de son côté sur
un schéma non conforme. Deux fois deux : quatre appels, et aucun des deux
fichiers ne pouvait le voir seul.

**Le raisonnement de la correction.** La question n'était pas « quelle boucle
supprimer » mais « qui a le droit de reprendre ». La réponse est le pipeline :
c'est le seul niveau qui voit **tous** les motifs d'échec — JSON illisible *et*
schéma non conforme — et le seul qui puisse borner le **total**. `app/llm.py`
n'en voit qu'un et ne peut donc borner que sa moitié.

**Correctif.** Suppression de la boucle interne de `app/llm.py`, qui ne fait
plus qu'un appel. Le pipeline porte la constante `MAX_APPELS_MODELE = 2`
— un essai, une reprise.

**Test de non-régression.**
`tests/test_pipeline.py::test_un_message_ne_coute_jamais_plus_de_deux_appels`,
qui affirme `f.appels == MAX_APPELS_MODELE`, et
`test_une_reprise_suffit_quand_le_second_appel_est_bon`, qui vérifie que la
reprise n'a pas été supprimée en même temps que la boucle.

---

## INC-03 — Deux visiteurs partageaient le même devis

**Symptôme.** Deux navigateurs ouverts sur l'application voient le **même**
devis. Ce qu'un artisan dicte apparaît chez l'autre. Et tout est perdu au
redémarrage du serveur.

**Gravité.** Critique, et pour deux raisons distinctes. La fuite entre visiteurs
est une fuite de données de chantier — coordonnées de clients finaux comprises.
La perte au redémarrage rend le produit inutilisable sur un vrai chantier.

**Reproduction.** Deux clients de test, un message dans chacun, comparer les
devis. Puis instancier un nouveau registre sur le même répertoire et vérifier
que le devis a survécu.

**Cause.** `app/main.py` portait `SESSION = Session()` **au niveau du module**.
Un objet unique, créé à l'import, partagé par toutes les requêtes du processus
et détruit avec lui. C'est commode pour un prototype à un seul utilisateur, et
faux dès le deuxième.

**Correctif.** Un `Registre` de projets (`app/persistance.py`), un fichier JSON
par projet, écriture atomique — fichier temporaire puis `replace()` — pour
qu'une coupure d'alimentation ne laisse jamais un projet à moitié écrit. Le
navigateur porte son identifiant dans un cookie `httponly`.

**Ce qui n'a pas été fait, et pourquoi.** Ce n'est **pas** de
l'authentification. Un identifiant de cookie isole ; il n'autorise pas. C'est
écrit dans `docs/AUDIT_JURY.md` (C9-59, C17-124) plutôt que présenté comme
résolu.

**Défaut adjacent trouvé pendant la correction.** La méthode `_chemin()` lisait
la racine globale au lieu de `self.racine` : un `Registre(racine=tmp_path)`
aurait écrit **hors** du répertoire de test. Détecté à la relecture avant
versement, jamais livré.

**Tests de non-régression.**
`tests/test_api.py::test_deux_navigateurs_ne_partagent_pas_leur_devis`,
`tests/test_persistance.py::test_un_projet_survit_au_redemarrage`,
`tests/test_persistance.py::test_identifiant_forge_est_refuse`.

---

## INC-04 — L'application ne démarrait que depuis la racine du dépôt

**Symptôme.** `uvicorn app.main:app` lancé depuis un autre répertoire renvoie
une erreur de fichier introuvable sur la page d'accueil.

**Cause.** `app/main.py` ouvrait `"app/static/index.html"`, chemin **relatif au
répertoire courant** et non au fichier source.

**Correctif.** `Path(__file__).resolve().parent / "static" / "index.html"`.

**Pourquoi ça mérite une fiche.** Le symptôme est trivial, la conséquence ne
l'est pas : un chemin relatif au répertoire courant casse tout démarrage par un
service système, un conteneur, ou une chaîne d'intégration — c'est-à-dire tout
ce qui n'est pas la machine de développement.

**Test de non-régression.**
`tests/test_api.py::test_page_d_accueil_se_sert_sans_dependre_du_repertoire_courant`,
qui change de répertoire courant avant d'appeler la racine.

---

## INC-05 — Ollama arrêté renvoyait une erreur 500 nue

**Symptôme.** Ollama arrêté, l'artisan dicte, l'interface renvoie une erreur 500
sans message. Et le serveur avait mis deux minutes à répondre.

**Cause.** Deux défauts qui se cumulaient. `app/llm.py` levait la même exception
pour « le modèle a mal répondu » et pour « le modèle n'a pas répondu du tout ».
Le pipeline, incapable de distinguer, **réessayait** — sur un service arrêté,
avec un délai d'expiration de 60 secondes par tentative.

**Le raisonnement.** Reprendre a du sens quand la sortie est mauvaise : le
modèle est non déterministe, un second tirage peut réussir. Reprendre n'a aucun
sens quand le service est absent : rien n'aura changé en 60 secondes, et on
double l'attente d'un utilisateur qui est sur un chantier.

**Correctif.** Deux exceptions distinctes : `SortieModeleInvalide` (on reprend)
et `ModeleInjoignable` (on abandonne tout de suite). Le pipeline court-circuite
sur la seconde, journalise une escalade et renvoie l'intention `"indisponible"`,
que l'interface sait présenter.

**Test de non-régression.**
`tests/test_pipeline.py::test_modele_injoignable_ne_reprend_pas`, qui affirme
`f.appels == 1` et `r.intent == "indisponible"`.

---

## INC-06 — Les mentions du devis s'affichaient « undefined »

**Symptôme.** Un devis portant une mention réglementée affiche
`Mentions : undefined` au lieu de l'avertissement. Sur un poste électrique ou
gaz, c'est l'avertissement de sécurité qui disparaît.

**Reproduction.** Dicter un poste `ELEC_TABLEAU`, ouvrir le panneau du devis.

**Cause.** L'API renvoie les mentions sous forme de **codes** — `"simple"`,
`"forte"`. Le JavaScript testait le **libellé français** :
`m.toLowerCase().includes('réglementé')`. Aucune branche ne pouvait
correspondre, et la fonction de correspondance n'avait pas de valeur de repli :
elle rendait `undefined`, que le gabarit affichait tel quel.

**Comment il a été trouvé.** Pas par un test — le front n'en a pas. Par la
relecture du rendu à la main, en comparant ce que l'API renvoie
(`sorted(session.devis.mentions)`) à ce que le front attend. **C'est la leçon
de cet incident** : une frontière entre deux langages sans test automatisé, où
le producteur et le consommateur ont chacun leur vocabulaire.

**Correctif.** Un dictionnaire `LIBELLE_MENTION` qui traduit le code en phrase,
avec repli sur le code brut. Un code inconnu affiche donc `forte` plutôt que
`undefined` — laid, mais pas silencieux.

**Test de non-régression.** Aucun, et c'est un manque assumé : le front n'a pas
de suite de tests. La chaîne d'intégration passe désormais `node --check` sur
son JavaScript, ce qui attrape la syntaxe, **pas** ce genre de défaut. Un test
de bout en bout de l'interface reste à faire.

---

## INC-07 — Le fichier de verrouillage des dépendances avait dérivé

**Symptôme.** `uv lock --check` échoue : `uv.lock` ne correspond plus à
`pyproject.toml`. Le groupe de dépendances `dev` — pytest, httpx — n'y figurait
pas.

**Comment il a été trouvé.** En vérifiant à la main les étapes de la chaîne
d'intégration **avant** de la livrer. Sans cette vérification, la première
exécution de la chaîne aurait échoué à l'installation, et le diagnostic se
serait fait sur un journal distant plutôt qu'en local.

**Cause.** Le venv est hors du dépôt (`~/.venvs/the-project`) et les
dépendances de développement y ont été installées sans repasser par `uv lock`.
Localement tout fonctionne — le décalage ne se voit que sur une machine vierge.

**Correctif.** `uv lock` régénéré, versionné avec la chaîne. La chaîne utilise
`--frozen`, ce qui **fait échouer** l'installation si le lock dérive à nouveau,
au lieu de résoudre en silence des versions que personne n'a vues.

**Test de non-régression.** L'étape `uv sync --frozen` de la chaîne elle-même.

---

## Ce que ce journal ne couvre pas encore

- **Aucun outil de suivi.** C21-155 demande une procédure de débogage
  documentée *depuis l'outil de suivi*. Ce fichier tient lieu de suivi ; le
  tableau Notion (`docs/NOTION_BOARD.md`) le portera quand il sera monté.
- **Aucune merge request.** C21-157 la cite en exemple. Sans dépôt distant, les
  correctifs sont des commits atomiques et rien de plus.
- **Aucun incident de production**, puisqu'il n'y a pas de production. Les sept
  incidents ci-dessus sont des défauts de développement — ce sont de vrais
  incidents, avec de vraies causes, mais aucun n'a touché un utilisateur.
