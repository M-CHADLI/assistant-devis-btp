# Notes de travail

> Bloc-notes. Idées attrapées au vol, pas encore arbitrées.
> Ce qui est tranché ici remonte dans `CADRAGE_MODELE.md` ou
> `DISPOSITIF_AGENT.md`, et la note est retirée.

---

## Tester le dernier Qwen (candidat modèle de base)

**L'idée.** Évaluer la version la plus récente de **Qwen** comme modèle de base,
en alternative à gpt-oss. Réputation de meilleure puissance brute — **à vérifier,
pas à supposer** : rumeur d'usage, pas encore un fait mesuré ici.

**Ce qu'il faut vérifier avant d'aller plus loin**, dans cet ordre :

1. **Quelle version exactement ?** Identifier la dernière release au moment du
   test et son variant (dense vs MoE, taille, quantization disponible). Ne pas
   raisonner sur une version supposée.
2. **Licence.** gpt-oss est en **Apache 2.0**, choisi pour ça. Les Qwen sont en
   général sous licence permissive, mais **elle varie selon les tailles** —
   à lire ligne à ligne avant tout engagement.
3. **MoE et paramètres actifs.** Le goulot sur DGX Spark est la bande passante
   (273 Go/s), pas le total de paramètres. Un Qwen dense, même bon, peut décoder
   plus lentement qu'un MoE de taille supérieure. Comparer les **paramètres
   actifs**, pas la taille affichée.
4. **Support Unsloth du fine-tuning LoRA** pour cette version précise, et à quelle
   empreinte mémoire.
5. **Comportement de refus de sécurité.** gpt-oss embarque des refus pré-entraînés
   qu'on a prévu de gérer par le dataset (`mention forte` : gaz, tableau
   électrique). Qwen aura son propre comportement — à re-caractériser entièrement,
   ce n'est pas transposable.

**Comment trancher honnêtement.** Ne pas comparer sur une impression : passer les
deux candidats sur le **même jeu de test manuel (150-200 exemples)** et sur la
métrique nº 1, le **taux de JSON valide**. C'est le seul comparatif qui tienne
devant un jury.

**Le coût, à nommer.** Changer de modèle de base rejoue tout le protocole de
preuve (baseline brute + fine-tuné) et invalide les mesures déjà faites sur
gpt-oss. Décision de fin de cycle, pas d'opportunité — sauf écart de qualité
massif et mesuré.

**Statut : non arbitré.** À planifier comme une séance de veille dédiée avant
d'engager quoi que ce soit sur le dataset.

---

## Fallback de modèle (`model_fallback`)

**Le besoin.** Le modèle est **auto-hébergé** sur la DGX Spark. Une seule
machine, un seul serveur d'inférence : c'est un point de défaillance unique.
S'il tombe, l'application ne répond plus — y compris le jour de la soutenance.

Il faut donc une **bascule automatique** vers un modèle de secours quand
l'appel primaire échoue : machine indisponible, modèle non chargé, timeout,
saturation mémoire, ou sortie inexploitable.

**Piste technique — LangChain.** `ModelFallbackMiddleware`, module
`langchain.agents.middleware.model_fallback`. C'est un **middleware d'agent**,
à ne pas confondre avec `Runnable.with_fallbacks()` qui traite le même besoin
au niveau d'un runnable isolé.

```python
ModelFallbackMiddleware(
    first_model: str | BaseChatModel,
    *additional_models: str | BaseChatModel,
)
```

Point d'attention : les modèles listés sont les **alternatives**. Le modèle
primaire reste celui déclaré sur l'agent ; le middleware n'entre en jeu qu'après
son échec, puis essaie ses modèles dans l'ordre jusqu'au premier succès.

La documentation ne dit **pas** quels types d'erreur déclenchent la bascule —
elle parle d'« échec de l'appel modèle », sans plus. À vérifier en lisant le
code : ça détermine si une sortie non conforme (JSON invalide) déclenche ou non,
ce qui est justement la question ouverte plus bas.

Choisir LangChain comme couche d'orchestration n'est pas neutre : ça engage
l'architecture de l'API qui expose le modèle. À poser explicitement, pas à
subir par défaut parce que le fallback y était pratique.

**Chaîne de secours envisagée**, du plus fidèle au plus dégradé :

1. **gpt-oss-120b fine-tuné** — le modèle primaire, déclaré sur l'agent
2. **gpt-oss-20b fine-tuné** — même dataset, même schéma de sortie, tient sur
   bien moins de mémoire. Le fallback naturel : les réponses restent conformes
3. **20b brut avec prompt système** — celui de la baseline du §7. Déjà écrit,
   déjà mesuré : on sait exactement ce qu'il vaut
4. **Refus explicite** — mieux qu'une réponse inventée

**Ce qui rend le fallback praticable ici.** Le schéma de sortie est **unique et
partagé par toutes les capacités**. Le code qui consomme le JSON ne change pas
selon le modèle qui l'a produit : basculer de modèle ne casse rien en aval. Sans
ce schéma unique, chaque fallback demanderait son propre parseur.

**Questions ouvertes.**

- **Où vit le fallback ?** Dans l'API qui expose le modèle, ou dans
  l'application qui la consomme ? Réponse probable : dans l'API — c'est elle qui
  sait quel modèle est chargé.
- **Un fallback distant est-il acceptable ?** Une API externe comme dernier
  recours violerait le « 100 % local, les données ne sortent pas de la
  machine ». À trancher : soit on l'exclut, soit on l'autorise avec un
  consentement explicite. Par défaut, **exclu**.
- **Sur quoi déclenche-t-on ?** Erreur réseau et timeout, évidemment. Mais aussi
  **JSON invalide** ? Un JSON invalide est déjà la métrique nº 1 du projet — le
  retenir comme déclencheur de fallback mélangerait la mesure et la mitigation.
  Prudence : mesurer d'abord sur le modèle primaire seul, activer le fallback
  ensuite.
- **Faut-il journaliser chaque bascule ?** Oui. C'est une métrique
  d'exploitation à part entière, et le taux de recours au fallback dit la
  fiabilité réelle de l'hébergement.

**Ce que ça apporte au-delà de la robustesse.** Cette chaîne est de la matière
directe pour deux compétences : le **monitorage** (taux de bascule, seuil
d'alerte) et la **gestion d'incident**. Le fallback est un cas d'incident réel,
reproductible et documentable — pas un incident fabriqué pour l'occasion.

**Sources.**

- [ModelFallbackMiddleware — LangChain Reference](https://reference.langchain.com/python/langchain/agents/middleware/model_fallback/ModelFallbackMiddleware)
- [How to add fallbacks to a runnable](https://python.langchain.com/v0.2/docs/how_to/fallbacks/) — l'autre mécanisme, au niveau runnable

**Coût honnête.** Faire tourner deux modèles simultanément sur 128 Go de mémoire
unifiée n'est pas gratuit : le 120b en occupe déjà une large part. Deux options
— soit le 20b reste chargé en permanence (mémoire consommée en continu), soit il
est chargé à la demande (bascule lente, plusieurs dizaines de secondes). Le
second ne tient pas la latence p95 de 30 s du plan d'évaluation. **À mesurer
avant de promettre quoi que ce soit.**

---

## Stack technique de la couche application (à trancher — grill-me à venir)

**L'idée.** Cataloguer les briques candidates pour la couche
**application/hébergement**, en amont d'une séance de type *grill-me* qui
tranchera chaque choix un par un. À ne pas confondre avec la couche modèle
(DGX Spark, Unsloth, gpt-oss) déjà cadrée dans `CADRAGE_MODELE.md` — celle-là
reste 100 % locale, ce qui suit concerne l'application qui l'entoure.

**Candidats notés jusqu'ici, aucun arbitré :**

- **GCP** — plateforme cloud envisagée pour l'hébergement. Rôle précis non
  posé (appli web ? stockage ? auth ? tout ?) — à préciser au grill-me.
- **PostHog** — tracking utilisateur et reconstitution de parcours client
  (product analytics, session replay, funnels). Piste retenue pour le suivi
  d'usage de l'application.
- **Piano Analytics** — alternative à PostHog sur le même besoin. Comparatif à
  faire : coût, conformité RGPD, self-host vs SaaS, granularité du parcours
  reconstitué, ce que chacun exige comme instrumentation côté appli.
- **Supabase** — candidat noté, rôle non précisé (BDD Postgres managée ? auth ?
  les deux ? recouvrement avec un autre choix déjà fait ?).
- **Gladia** — API de speech-to-text, déjà testée dans `Speech-to-text.py`
  (transcription live via websocket, fonctionnelle). **Tension à trancher en
  priorité** : le pivot (`docs/CADRAGE_MODELE.md`) pose un STT **local** (type
  Whisper, sur DGX Spark, audio qui ne sort jamais de la machine) — Gladia est
  une **API distante**, donc à l'opposé de ce principe. Soit Gladia reste un
  prototype jetable pour valider le flux avant de passer en local, soit le
  principe 100 % local se limite au LLM et le STT peut être externe — **à ne
  pas laisser implicite**, ça touche un principe déjà posé dans le cadrage, pas
  seulement un choix d'infra. **Matière rassemblée le 08/09/2026** dans
  `docs/BENCHMARK_STT.md` : coût, résidence des données, pérennité du
  fournisseur, empreinte énergétique et conséquences en code de chaque branche.
  La note reste ici parce que **le benchmark instruit, il ne tranche pas**.
- **Whisper (local)** — l'alternative locale à Gladia, celle qui respecte le
  principe posé dans le cadrage. Comparatif à faire au grill-me : latence sur
  DGX Spark, qualité de transcription FR, empreinte mémoire face au(x) LLM déjà
  chargé(s), et si un mode « live/streaming » est aussi simple à obtenir qu'avec
  Gladia (le prototype actuel exploite le streaming websocket de Gladia).
  `docs/BENCHMARK_STT.md` §4 ajoute un troisième candidat local, **Parakeet TDT
  0.6b v3**, et §8 le protocole qui départagera les deux — une fois le corpus de
  trente dictées enregistré, ce qui suppose d'aller sur un chantier.

**Outils déjà mobilisés, à inventorier sans re-trancher :**

- **Notion** — déjà utilisé pour le suivi de projet (bases User Stories,
  Tickets, Sprints, Compétences RNCP, Métriques, et les comptes rendus de
  séance). Pas un candidat : déjà en usage, listé ici pour que l'inventaire du
  stack soit complet.
- **LangChain** — piste d'orchestration déjà creusée dans la note « Fallback de
  modèle » ci-dessus (`ModelFallbackMiddleware`) et confirmée dans le spec du
  pivot (`2026-08-16-pivot-btp-vocal-design.md`, Section 6) comme appuyant C9.
  Pas encore engagé formellement dans `CADRAGE_MODELE.md` ni
  `DISPOSITIF_AGENT.md` — à faire au moment où l'architecture d'orchestration
  sera figée, pas nécessairement au grill-me stack.
- **API Pappers** — auto-remplissage des informations légales du prestataire
  (SIRET, forme juridique, adresse) à l'inscription. Déjà documenté comme
  service externe intégré dans le spec du pivot (Sections 2 et 6) — ne
  revendique pas C8, qui reste porté par l'OCR.
- **uv** — gestionnaire de paquets Python déjà en usage dans le dépôt
  (`pyproject.toml`, `uv.lock`, `.python-version`). Outillage dev, pas un choix
  à trancher.

**Ce qu'il faudra trancher au grill-me.** Le rôle exact de chaque brique, les
recouvrements entre elles (ex. auth Supabase vs autre chose), le coût, et si
le tracking utilisateur (PostHog/Piano) crée une tension avec le principe
« 100 % local » de `CADRAGE_MODELE.md` — a priori non, puisqu'il porterait sur
l'usage de l'application et non sur les données vocales/métier envoyées au
modèle, mais **à vérifier explicitement pendant le grill-me, pas supposé ici.**
Voir aussi le lien possible avec les compétences RNCP de la couche application
(C9 API, C17 développement) dans `docs/LIVRABLES.md`.

**Statut : non arbitré.** En attente de la séance de grill-me dédiée — aucune
de ces briques n'est encore engagée dans `CADRAGE_MODELE.md` ni
`DISPOSITIF_AGENT.md`.

---

## Fixer les hyperparamètres du LoRA sur une mesure, pas sur les défauts

*(sorti de la séance de veille du 08/09/2026, item 2 — verdict « impacte le projet »)*

**Le manque.** Le projet devra fixer taux d'apprentissage, taille de lot, nombre
d'époques, rang du LoRA et optimiseur pour gpt-oss-20b. Aujourd'hui la seule
justification disponible devant un jury serait « les valeurs par défaut
d'Unsloth » — ce qui est un choix par omission, pas une décision.

**La matière.** *Post-Training Science for Supervised Fine-Tuning*
(arXiv 2609.01244, 01/09/2026) mesure ces leviers un par un dans un protocole
unique, et couvre les modèles **denses et MoE** — rare, et exactement notre cible.

**Ce qu'il faut en faire.** Le lire en entier **avant** la première session
d'entraînement, en tirer une valeur de départ argumentée par levier, et citer la
source en note des choix retenus. Ne pas transposer les valeurs mécaniquement :
le papier balaie des datasets de taille usuelle, le nôtre fera quelques centaines
d'exemples écrits à la main — un régime où l'on surapprend vite.

**Statut : non arbitré.** Lecture à planifier sur le mois d'octobre, avant
l'entraînement. Lié à [[la note MonteCLoRA de la séance du 08/09]] : si
l'entraînement se révèle instable d'une graine à l'autre, l'hyperparamétrage est
la première chose à regarder, avant le dataset.

---

## GRPO en seconde passe, si le taux de JSON valide plafonne

*(sorti de la séance de veille du 08/09/2026, item 3 — verdict « à surveiller »)*

**L'idée.** *Fine-tuning a 350M Model for Better Structured Outputs in 100 GRPO
Steps* (blog Hugging Face, 03/09/2026) entraîne un petit modèle à respecter un
schéma de sortie par renforcement, la récompense étant calculée par du code :
le JSON parse, ou il ne parse pas. La métrique nº 1 du projet — le **taux de JSON
valide** — est précisément de cette nature : vérifiable sans juge humain.

**Pourquoi ce n'est pas pour maintenant.** Le protocole de preuve est figé :
*20b brut bien promptté vs 20b fine-tuné en supervisé*. Changer de régime
d'entraînement en cours de route rendrait la comparaison illisible, et c'est
elle qui porte la démonstration devant le jury.

**Quand ce redeviendrait pertinent.** Après la mesure du SFT, et seulement si le
taux de JSON valide plafonne sous la cible. GRPO viendrait alors en **seconde
passe** sur le modèle déjà fine-tuné, avec sa propre mesure avant/après — sans
toucher au comparatif initial, qui reste publié tel quel.

**Statut : non arbitré.** Rien à engager avant d'avoir le chiffre du SFT.
