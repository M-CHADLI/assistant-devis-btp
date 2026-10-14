# Chaîne MLOps

> Ce document couvre les étapes de la chaîne du modèle, ses déclencheurs, ses
> fichiers de configuration, et la façon de l'exécuter. Il répond aux critères
> C13 du référentiel. Il complète `docs/exploitation/CHAINE_CI_CD.md` (C18 et C19),
> qui porte sur le code, pas sur le modèle.
>
> **Structure du document.** Titres hiérarchisés sans saut de niveau, tableaux
> avec ligne d'en-tête, liens explicites, aucune information portée par la
> seule couleur ou la seule mise en forme — conformément à
> `docs/exploitation/ACCESSIBILITE_DOCUMENTS.md`.

## Pourquoi la chaîne existe avant l'entraînement

Le fine-tuning n'a pas encore eu lieu ; le calendrier le place en octobre
(`PLANNING.md`). Écrire la chaîne après coup serait pourtant trop tard : elle
ne pourrait plus porter la trace de l'entraînement, seulement le récit qu'on en
fait. Une chaîne écrite avant enregistre ce qui s'est passé ; une chaîne écrite
après enregistre ce dont on se souvient.

D'où un parti pris qui traverse tout ce document : **la chaîne distingue trois
états, pas deux.** Une étape est `réussie`, `échouée`, ou `ignorée` faute de
prérequis. Confondre « pas encore lancé » avec « réussi » ferait mentir le
rapport ; le confondre avec « échoué » ferait rougir une chaîne qui va bien.

## Ce que la chaîne protège

Un projet de fine-tuning a une seule mesure honnête : un jeu d'essai écrit à la
main, jamais vu à l'entraînement. Tout le reste — le taux de JSON valide sur le
jeu d'entraînement, l'impression qu'on a en démonstration — se laisse
facilement flatter.

Cette mesure se perd d'un seul geste : un exemple d'essai qui réapparaît dans
le jeu d'entraînement. Le modèle ne le résout plus, il s'en souvient, et le
chiffre monte pour la mauvaise raison. **La détection de fuite est donc
bloquante et sans tolérance** — c'est la seule règle de la chaîne qui n'admet
aucun réglage.

## L'outil retenu, et pourquoi

Un **exécuteur maison de 150 lignes** (`tools/mlops/executer.py`) qui lit une
déclaration TOML.

Trois raisons :

1. **La chaîne compte quatre étapes et tourne sur une machine.** Kubeflow,
   Airflow ou ZenML apporteraient un serveur à tenir, une base de métadonnées,
   et une couche d'abstraction entre la commande et ce qu'elle fait.
2. **Elle doit rester lisible par un jury en trois minutes.** Une déclaration
   TOML de quarante lignes se lit ; un DAG Python réparti sur cinq fichiers se
   parcourt.
3. **Aucune dépendance ajoutée.** Le TOML est lu par `tomllib`, dans la
   bibliothèque standard depuis Python 3.11.

**Ce qui a été écarté, et ce qui le ferait revenir.** MLflow pour le suivi
d'expériences : justifié dès qu'il y aura plusieurs entraînements à comparer,
inutile pour zéro. DVC pour le versionnement du dataset : justifié quand le
dataset dépassera ce que git encaisse confortablement ; à ~2000 exemples JSONL,
git suffit et garde l'historique lisible. Un orchestrateur distribué : le jour
où la chaîne s'exécutera sur plusieurs machines.

## Les fichiers de configuration

| Fichier | Ce qu'il porte | Pourquoi hors du code |
|---|---|---|
| `mlops/pipeline.toml` | L'ordre des étapes, leurs prérequis, leur caractère bloquant | Ajouter une étape ne doit pas demander de modifier l'exécuteur, et l'ordre doit se lire dans git. |
| `mlops/lora.toml` | Les hyperparamètres de l'adaptateur (modèle de base, rang, alpha, époques, graine) | C'est ce qui permettra de rattacher une mesure à une configuration. Un hyperparamètre changé dans un script laisse une trace illisible. |

L'exécuteur ne connaît **aucune étape en dur** : il refuse une déclaration qui
contient deux étapes du même nom, et signale une étape inconnue passée en
argument plutôt que de l'ignorer.

## Les étapes

| Étape | Module | Prérequis | Bloquante |
|---|---|---|---|
| `donnees` | `tools.mlops.valider_dataset` | aucun | oui |
| `preparation` | `tools.mlops.preparer` | `dataset/entrainement.jsonl` | oui |
| `entrainement` | `tools.mlops.entrainer` | `mlops/artefacts/entrainement.chat.jsonl` | oui |
| `validation` | `tools.mlops.evaluer` | `dataset/essai.jsonl` | oui |

### Étape `donnees` — tester les données

Elle commence par se tester elle-même. `dataset/gabarit_fautifs.jsonl` porte six
exemples, chacun avec un défaut et le **motif de refus attendu** ; si un refus
change de motif ou disparaît, l'étape échoue. Un détecteur qui cesse
silencieusement de détecter est pire que pas de détecteur : il promet une
garantie qu'il ne tient plus. `dataset/gabarit.jsonl` porte à l'inverse quatre
exemples de référence qui doivent tous passer.

Elle valide ensuite chaque exemple du dataset :

- l'enveloppe est conforme à `app.schema.SortieModele` — mêmes modèles Pydantic
  que le produit, pas une copie qui divergerait ;
- le `payload` est conforme à l'intention déclarée ;
- l'`intent` ne contredit pas la capacité annoncée ;
- une capacité raisonnée (`devis`, `quantitatif`, `lots`, `consommables`) porte
  un `reasoning` non vide. C'est lui qui porte l'expertise métier ; sans lui, on
  n'entraîne qu'un formateur de JSON.

Trois règles héritées de la chaîne de données catalogue, parce qu'elles valent
ici aussi : **rien n'est écarté en silence** (chaque refus est compté avec son
motif, et retenus + refusés = lus), **aucune valeur n'est inventée** (un exemple
incomplet est refusé, jamais complété), **l'écart à la cible est une donnée**.

Ce dernier point mérite d'être précisé. La répartition visée par
`docs/produit/CADRAGE_MODELE.md` — ≈ 72 % d'exemples raisonnés, ~15 % de mention
simple, ~5 % de forte, et une part par capacité — est comparée à la répartition
réelle, avec une tolérance. Un écart est **écrit, pas bloquant** : un dataset
déséquilibré se rééquilibre en écrivant des exemples, pas en bloquant la
chaîne. Ce qui bloque, c'est un exemple fautif, et c'est une fuite.

### Étape `preparation` — vers le format Unsloth

Conversion volontairement bête : elle ne corrige rien, ne complète rien, ne
réordonne rien. Toute transformation intelligente ici créerait une divergence
entre ce qui a été relu à la main et ce qui entre dans l'entraînement.

Le raisonnement part dans un message `analysis` distinct de la réponse `final`.
C'est ce qui permet à gpt-oss de conserver sa capacité de raisonnement au lieu
d'apprendre à recracher du JSON sans réfléchir.

### Étape `entrainement` — non exécutée, et elle le dit

Elle vérifie ses prérequis, **les nomme un par un** quand ils manquent
(« ça ne marche pas » n'aide personne), affiche ce qui serait lancé d'après
`mlops/lora.toml`, et sort avec le code 3.

Elle ne simule aucun entraînement et ne produit aucun artefact factice : un
adaptateur qui n'existe pas ne doit pas laisser croire le contraire. Le code
d'appel à Unsloth **ne sera versionné qu'une fois exécuté** sur la machine —
du code d'entraînement jamais lancé donne une fausse impression d'avancement,
et c'est exactement ce que ce document cherche à éviter.

### Étape `validation` — mesurer sur le jeu d'essai

Trois métriques, celles que le jeu d'essai permet de mesurer honnêtement
(numérotation de `docs/produit/DISPOSITIF_AGENT.md` §4.3, seuils lus dans
`app.observabilite.SEUILS`, jamais recopiés) :

| Métrique | Seuil | Bloquante | Pourquoi |
|---|---|---|---|
| nº 1 — taux de JSON valide | ≥ 98 % | oui | C'est la mesure directe de l'apport du fine-tuning. |
| nº 5 — justesse de la mention | ≥ 95 % | non | Un modèle qui rate une mention reste utilisable ; l'écart est écrit. |
| nº 7 — prix ou référence inventés | 0 | oui | Le modèle décrit, il ne chiffre pas. Seuil non négociable. |
| nº 8 — latence p95 | ≤ 30 s | non | Indicatif hors machine cible. |

Les métriques 2, 3, 4 et 6 demandent une annotation ligne à ligne du jeu
d'essai qui n'existe pas encore : elles sont **déclarées non mesurées** plutôt
qu'approchées. Un blanc assumé vaut mieux qu'un chiffre flatteur.

Le rapport est horodaté et porte le nom du modèle interrogé — une mesure sans
son modèle ne se compare à rien.

## Les déclencheurs

| Déclencheur | Ce qui s'exécute | Pourquoi |
|---|---|---|
| `push` touchant `dataset/`, `mlops/` ou `tools/mlops/` | `donnees` et `preparation` | Une fuite ou un exemple fautif doit se voir au commit qui l'introduit. |
| `pull_request` touchant les mêmes chemins | Idem | Contrôle avant fusion. |
| Hebdomadaire (lundi, 6 h 23 UTC) | Idem | Attrape une dérive introduite ailleurs — un schéma Pydantic modifié dans `app/`, par exemple. |
| Lancement manuel | Idem | Après une modification de la chaîne. |

**L'entraînement et la mesure ne tournent pas en intégration continue.** Un
exécuteur GitHub n'a ni le GPU, ni le droit de voir les données : ces deux
étapes se lancent à la main sur une machine GPU et déposent leur rapport dans
`mlops/`. Laquelle n'est pas tranché depuis la perte de la DGX Spark
(`docs/DECISIONS.md` Q-13).

## Installer, configurer, exécuter

Aucune installation supplémentaire : la chaîne n'utilise que la bibliothèque
standard et ce que le projet installe déjà.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run python -m tools.mlops.executer
VIRTUAL_ENV=~/.venvs/the-project uv run python -m tools.mlops.executer --simulation
VIRTUAL_ENV=~/.venvs/the-project uv run python -m tools.mlops.executer --jusqu-a donnees
```

Chaque étape s'exécute aussi seule, ce qui est le mode de travail réel quand on
écrit des exemples :

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run python -m tools.mlops.valider_dataset
```

Sortie attendue aujourd'hui, dataset non écrit :

```text
  donnees       réussi    0.84s
  preparation   ignoré    0.00s  — prérequis absents : dataset/entrainement.jsonl
  entrainement  ignoré    0.00s  — prérequis absents : mlops/artefacts/entrainement.chat.jsonl
  validation    ignoré    0.00s  — prérequis absents : dataset/essai.jsonl
```

Un rapport JSON est écrit dans `mlops/executions/`, horodaté, avec l'état et la
durée de chaque étape.

## Le format d'un exemple

Un objet JSON par ligne. `dataset/gabarit.jsonl` en porte quatre, complets, qui
servent de référence.

```json
{"id": "gabarit-consommables-01",
 "capacite": "consommables",
 "user": "j'ai oublié quelque chose pour la pose du stratifié ?",
 "reasoning": "Une pose de stratifié flottant demande une sous-couche acoustique, des cales de dilatation en périphérie et des barres de seuil aux passages de porte.",
 "final": {"intent": "consommables", "mention": null,
           "payload": {"lot_code": "SOL_POSE_STRATIFIE",
                       "items": ["sous-couche acoustique", "cales de dilatation", "barres de seuil"]}}}
```

Le champ `user` simule un texte **déjà relu** par l'artisan à l'étape HITL-0 —
pas une transcription brute. Le dataset n'a donc pas à simuler de bruit de
dictée.

## Ce que cette chaîne ne fait pas

**Elle n'entraîne pas.** C'est le point le plus important de ce document, et il
est écrit ici plutôt que découvert à l'exécution.

**Elle ne versionne pas le dataset autrement que par git.** Suffisant à
~2000 exemples JSONL ; à revoir si le dataset grossit ou si des artefacts
binaires s'y ajoutent.

**Elle ne promeut aucun modèle automatiquement.** La décision de basculer la
démonstration d'un adaptateur à un autre reste manuelle, parce qu'elle engage
une soutenance et pas seulement une métrique.

**Elle ne s'exécute pas encore chez un tiers.** Aucun `remote` git n'est
configuré — même constat que pour les deux autres chaînes, même cause, notée en
tête de `docs/pilotage/COUVERTURE_RNCP.md`.
