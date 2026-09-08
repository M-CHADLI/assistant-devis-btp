# Journal de la session de nuit — reprise après arrêt

**Fichier de reprise.** Si la session s'est arrêtée (interruption, plantage,
contexte compacté), tout ce qu'il faut pour repartir est ici. Le lire d'abord,
le mettre à jour à chaque étape franchie.

Dernière mise à jour : **08/09/2026**, commit `5e3f370`.

---

## Règles qui ne bougent pas

- **Commits autorisés, `git push` interdit.** Sans exception.
- Toute la documentation et tous les commentaires **en français**.
- `docs/` fait autorité, `archive/` non. Ne jamais aligner un document sur `archive/`.
- **Vérifier avant d'affirmer.** Aucun chiffre, aucun « ça marche » sans la commande qui le prouve.
- Le jeu de test de 150-200 exemples s'écrit **à la main** — jamais généré, ni par moi
  ni par un sous-agent. C'est la seule mesure honnête du fine-tuning.
- Les points marqués « non arbitré » dans `docs/NOTES.md` appartiennent à
  l'utilisateur. Ne pas trancher à sa place ; les lister et attendre.
- **Aucun secret** recopié nulle part : ni valeur de `.env`, ni clé, ni jeton.
- Git est sur un montage OneDrive : préfixer par `git -c core.fsmonitor=false`.
- Commande de test :
  `BTP_DONNEES=<répertoire jetable> VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync pytest`

## Comment ne pas rester bloqué

- Si une commande dépasse deux minutes sans sortie, l'abandonner et passer à la
  tâche suivante de la file. Ne jamais attendre indéfiniment.
- Si Ollama ne répond pas, **ce n'est pas bloquant** : tous les tests neutralisent
  le modèle. Continuer sur le code et les documents.
- Si un sous-agent ne rend rien, reprendre sa tâche soi-même. Ne jamais l'attendre.
- Si une tâche de la file s'avère bloquée, **la sauter, l'écrire ici avec le motif**,
  et prendre la suivante. Une file qui avance vaut mieux qu'une tâche parfaite.
- Ne jamais poser de question bloquante pendant la nuit : poser l'hypothèse,
  l'écrire dans « Décisions prises seul », et avancer.

---

## État vérifié au 08/09/2026

- **420 tests, tous verts.** Répartition relevée par `pytest --collect-only -q` :
  `test_garde_fous` 52, `test_front` 45, `test_chaine_donnees` 43,
  `test_pipeline` 33, `test_mlops` 33, `test_annuaire` 30, `test_api` 29,
  `test_boucle_qualite` 24, `test_auth` 19, `test_api_catalogue` 19,
  `test_devis` 16, `test_export` 13, `test_transcription` 12,
  `test_persistance` 12, `test_packaging` 11, `test_observabilite` 11,
  `test_contrat_api` 10, `test_referentiel` 8.
- **Stories : 28 au découpage — 21 faites, 5 partielles, 2 à faire** (compté
  depuis les lignes de traçabilité de `docs/STORIES.md`, pas depuis un tableau
  recopié).
  - *fait* : US-02, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20,
    21, 22, 23, 24, 25
  - *partiel* : US-01 (tout est écrit et testé sauf l'appel réel, faute de
    clé d'annuaire), US-04 (dictée navigateur, transcription locale à faire),
    US-26 (chaînes écrites et image construite, aucun `remote` pour les
    exécuter), US-27 (chaîne de données faite, pas branchée sur le devis),
    US-28 (chaîne du modèle faite, entraînement non lancé)
  - *à faire* : US-03, 17
- **Le parcours de bout en bout passe 24/24, cinq fois de suite** (08/09,
  05 h 57 – 06 h 01) contre le serveur réel et `gpt-oss:20b` : 4 lignes de devis,
  620,81 € TTC, `.docx` de 37 579 octets, ~46 s par passage.
  `tools/parcours_bout_en_bout.py` — c'est la seule preuve que la chaîne complète
  fonctionne, la suite pytest neutralisant le modèle.
- **Le chiffre le plus important de la nuit** : sur ces 21 appels modèle,
  `gpt-oss:20b` **brut** n'a produit du JSON conforme que dans **71,4 %** des
  cas, contre 98 % visés. Six reprises pour six échecs, aucun passé en silence.
  Le produit tient quand même (24/24 cinq fois), parce que la reprise et le
  moteur déterministe absorbent l'échec — mais c'est la valeur de référence
  contre laquelle se mesurera le fine-tuning. Tout est dans
  `docs/CONCLUSION_POC.md` ; latence p95 12,8 s, 0 prix inventé.
- L'application démarre depuis n'importe quel répertoire et **exige désormais une
  authentification** : seuls `/` et `POST /api/session` sont ouverts, tout le
  reste répond 401 sans jeton — y compris `/docs` et `/openapi.json`.
  Sans `BTP_MOT_DE_PASSE`, une phrase de passe aléatoire est tirée et **affichée
  une fois au démarrage** ; elle change à chaque redémarrage.
- Le JavaScript du front passe `node --check`
  (node en `~/.nvm/versions/node/v22.22.2/bin`, pas dans le PATH par défaut).
- `tools/verifier_accessibilite_docs.py` : **27 documents conformes**
  (`veille/seances/` est entré dans le corpus contrôlé le 08/09).
- **L'image OCI se construit et démarre** : 212 Mo, base catalogue construite à
  la construction et non au démarrage, `/` à 200 et `/api/catalogue/familles` à
  401 sans session — vérifié, pas supposé.
- **La chaîne du modèle s'exécute** : étape `donnees` réussie, les trois autres
  `ignoré` en nommant leur prérequis manquant. `uv run python -m tools.mlops.executer`.
- Ollama répond sur `localhost:11434` et sert `gpt-oss:20b`.

## Fait cette nuit

| Commit | Contenu |
|---|---|
| `01ee0c5` | 26 stories, 7 épiques, kit de transposition Notion (CSV + schémas + CLI) |
| `a781711` | CLAUDE.md remis en accord avec le dépôt réel |
| `e669883` | `app/` et `tests/` versionnés pour la première fois + anomalies S1 |
| `7662a44` | Bornes de plausibilité (US-11), plafond de clarification (US-07) |
| `d783b9a` | Accessibilité RGAA 4.1 du front + arbitrage des quantités côté interface |
| `a019878` | Ce journal de reprise |
| `3c04c02` | Audit des 135 critères du jury (`docs/AUDIT_JURY.md`) |
| `7d29b6f` | Chaîne d'intégration continue (US-26, partiel : pas de remote) |
| `e7eb90b` | Règle d'accessibilité documentaire + son vérificateur |
| `a51e647` | Journal des incidents, sept défauts déjà corrigés |
| `7fdd6f7` | Profil artisan, régime de TVA, mentions obligatoires (US-02, US-15) |
| `9bd62b0` | HITL-0, relecture de la dictée avant traitement (US-05) |
| `1396730` | HITL-2, structure validée avant chiffrage (US-12) |
| `6bc8ddc` | Garde-fous d'entrée : périmètre et injection (US-19, US-20) |
| `ec4ebcd` | Arbitrage des quantités et reprise de projet (US-11, US-16) |
| `c7c551e` | Observabilité : journal applicatif et tableau de bord (US-24) |
| `7e3675a` | API contractuelle : modèles de sortie et erreurs déclarées (US-22) |
| `807171b` | Signal qualité exportable, jamais hors de la machine (US-25) |
| `0442fbe` | Authentification, application fermée par défaut (US-23) |
| `8270c9f` | Escalade demandée par l'artisan lui-même (US-21) |
| `75d5e05` | Sévérité des mentions publiée comme donnée, plus devinée dans le texte (US-18) |
| `f9867a9` | Deux dictées qui se contredisent : ni addition, ni arbitrage silencieux (US-06) |
| `29e3dd7` | Parcours de bout en bout étendu à 24 étapes + piège `BTP_MOT_DE_PASSE` documenté |
| `445a8b8` | Première séance de veille C6, et correction du flux qu'elle prend en défaut |
| `…` | *(suite : RGPD, incidents, modèle de données, maquettes, benchmark STT — voir `git log`)* |
| `9c5b8c3` | Chaîne de données : trois sources hétérogènes → base SQLite → API (US-27) |
| `46e309b` | US-27 inscrite au backlog |
| `311d4c3` | Empaquetage OCI et chaîne de livraison (US-26) |
| `8ef0329` | Chaîne MLOps, écrite avant l'entraînement pour pouvoir en porter la trace (US-28) |
| `a72dc7e` | Définition du sous-agent d'exécution locale |
| `ae90dfe` | Conclusion de la preuve de concept, sur cinq exécutions relevées |
| `48fc1a9` | Rafraîchissement de ce journal |
| `8899b4b` | Rituels agiles, parties prenantes et définition de fini (C16) |
| `743f3ef` | Accessibilité des sources de veille, traitée par le format (C7) |
| `e0868a2` | Journal remis à l'état vérifié (audit 91 / 35 / 9) |
| `abadb06` | Comptes de commits corrigés |
| `5e3f370` | Préremplissage du profil depuis l'annuaire des entreprises (US-01, partiel) |

**Rien n'est poussé.** **Quarante-neuf commits cette nuit** (depuis `87cfb07`), cinquante-huit sur `docs/pivot-btp-vocal-docs` depuis `main`, aucun `push`.

**L'audit jury au réveil : 91 ✅ / 35 🟡 / 9 ❌ sur 135** (il était à
82 ✅ / 31 🟡 / 22 ❌ en début de nuit). **Les neuf ❌ restants sont tous
le même manque : aucun dépôt distant.** Il ne reste plus un seul critère rouge
que le dépôt puisse fermer par lui-même — `git remote add` puis `push` les prend
d'un coup.

---

## File de travail — prendre dans l'ordre

La file initiale est **entièrement traitée**, sauf ce qui suit. Ce qui reste se
range en trois familles : ce que vous seul pouvez faire, ce qui demande une
matière que personne ne peut écrire à votre place, et le reste à coder.

### Ce qui n'attend que vous — un geste chacun

1. **`git remote add` puis `push`.** Les neuf ❌ de l'audit tombent d'un seul
   coup — ce sont désormais les seuls, et c'est de loin le meilleur rapport
   effort / critères du dépôt.
2. **Transposer sur Notion.** Les CSV de `docs/notion/` sont à jour (28 stories).
   Bloqué sur `NOTION_TOKEN` **et** le partage de la page racine avec
   l'intégration (menu `⋯` → Connexions). Sans ce partage, l'API rend une liste
   vide — pas une erreur, ce qui rend le diagnostic pénible.
3. **Tenir le rituel de veille pour de vrai.** Une seule séance existe
   (`veille/seances/2026-09-08.md`), préparée avec l'assistant. Le référentiel
   demande une *récurrence*. Antidater des séances fabriquerait la preuve au lieu
   de la produire — délibérément non fait.
4. **Arbitrer Gladia contre Whisper local.** `docs/BENCHMARK_STT.md` instruit la
   question et ne la tranche pas : c'est votre décision, pas la mienne. Le
   prototype utilise encore la Web Speech API du navigateur, qui envoie l'audio
   à l'éditeur — contradiction ouverte avec la règle « 100 % local ».

### Ce qui demande de la matière écrite à la main

5. **Le dataset (~2000 exemples) et le jeu d'essai (150-200).** C'est désormais
   le **chemin critique du projet** : plus rien d'autre ne bloque le
   fine-tuning. La chaîne qui les validera existe et tourne
   (`docs/CHAINE_MLOPS.md`) ; `dataset/gabarit.jsonl` donne le format exact sur
   quatre exemples complets. Le jeu d'essai doit être écrit **à la main et
   jamais montré à l'entraînement** — la détection de fuite est bloquante et
   sans tolérance, précisément pour protéger ça.
6. **Le corpus de dictées du banc d'essai STT** : une dizaine de dictées de
   chantier réelles. Le protocole est écrit, il attend son corpus.

### Ce qui reste à coder

7. **US-01 — il ne manque plus que la clé.** Tout le reste est écrit et testé :
   validation locale du SIRET (quatorze chiffres, clé de contrôle, exception
   La Poste), préremplissage des six champs légaux, origines de champ qui
   survivent au rechargement, repli sur la saisie manuelle en 200 quand
   l'annuaire est muet. Ce qui manque tient en une variable,
   `BTP_PAPPERS_CLE` : **le scénario nominal n'a jamais été joué contre
   l'annuaire réel**, et la correspondance des noms de champs JSON vient de la
   documentation publiée, pas d'une réponse observée. La story reste donc
   marquée *partiel*, pas *fait*.
8. **US-03** — OCR d'un devis image/PDF vers Markdown, par API externe, jamais
   par le modèle.
9. **US-17** — confort métier réel, aucun apport de preuve : à faire en dernier.
10. **Brancher le devis sur la base catalogue.** La chaîne de données alimente
    l'API mais **pas encore le moteur de devis**, qui lit toujours le
    dictionnaire de `app/catalogue.py`. La couture est `resoudre_produit()` →
    `moins_cher_de_famille()`. Bloqué sur un arbitrage métier : les codes de lot
    du référentiel et les familles du dump ne se recouvrent pas, et inventer
    cette table de correspondance reviendrait à décider à votre place.
11. **Partager les rituels, pas seulement les écrire.** `docs/RITUELS.md` existe
    désormais (objectifs, modalités, parties prenantes, définition de fini), mais
    C16-117 reste 🟡 volontairement : le critère demande de *partager* avec les
    parties prenantes, et un document versionné n'est pas un partage. C'est un
    acte — l'envoyer au tuteur, l'ouvrir au premier point hebdomadaire.
    C7-43 (accessibilité des sources de veille), qui figurait ici, est clos.

## À signaler à l'utilisateur au réveil

- **`donnees/` est dans le dépôt, donc synchronisé par OneDrive.** Il contient les
  projets persistés : nom, adresse et coordonnées des clients finaux. Le déplacer
  hors du montage est un **arbitrage de cadrage**, pas une correction technique —
  laissé à l'utilisateur, rien n'a été déplacé. Le même constat a fait sortir
  l'export du signal qualité du dépôt (US-25) : `app/boucle_qualite.py` refuse
  d'écrire sur un système de fichiers distant ou synchronisé, `fuse.rclone` compris.
- `.env` contient des clés qui ont l'air vivantes (Gladia, Azure AI Foundry). Le
  fichier est ignoré par git et n'a **jamais** été committé — vérifié sur tout
  l'historique. Mais elles se sont affichées en clair dans la sortie terminal de
  cette session : si elle a été partagée ou conservée, faire tourner les clés.
- **`BTP_PAPPERS_CLE` est la seule chose qui manque à US-01.** Un jeton d'API
  Pappers suffit à jouer le scénario nominal et à vérifier la correspondance des
  champs. Sans elle, l'application ne casse pas : elle bascule sur la saisie
  manuelle en le disant.
- **Aucun `remote` git** n'est configuré : neuf critères du jury (revue de code,
  CI observable, collaboration) restent bloqués tant que le dépôt est local.
- Point non tranché qui appartient à l'utilisateur : **Gladia (distant) contre
  Whisper local**. Le prototype actuel utilise la Web Speech API du navigateur,
  qui envoie l'audio à l'éditeur — contradiction avec la règle « 100 % local ».
- Les tâches cron programmées cette nuit **vivent dans cette session seulement** et
  expirent d'elles-mêmes au bout de sept jours. Elles ne survivront pas à la
  fermeture de la session.
- **Le chemin critique a changé de nature.** Au début de la nuit, ce qui bloquait
  le projet était de l'outillage : pas de chaîne de données, pas d'empaquetage,
  pas de chaîne MLOps, pas de conclusion de preuve de concept. Tout cela existe
  maintenant. Ce qui bloque désormais est de la **matière** — les 2000 exemples
  du dataset et les 150 à 200 du jeu d'essai, qui ne peuvent être écrits ni par
  moi ni par un sous-agent sans détruire la seule mesure honnête du projet.
- **Le modèle brut est à 71,4 % de JSON valide, pas à 98 %.** C'est une mauvaise
  nouvelle utile : elle donne au fine-tuning une raison chiffrée et datée. À ne
  pas enjoliver en soutenance — le document qui la porte
  (`docs/CONCLUSION_POC.md`) explique aussi pourquoi le produit tient quand même.

## Décisions prises seul (à faire relire)

- Quatre hypothèses par défaut concrètes quand le plafond de clarification est
  atteint : TVA à 10 %, hauteur sous plafond 2,50 m, supports sains, surfaces
  données comme surfaces à traiter. C'est de l'implémentation, mais ça engage le
  métier.
- Bornes de plausibilité : surface 0,5–400 m², longueur 0,5–300 ml, unité 1–60 ;
  resserrées à 1–3 pour `ELEC_TABLEAU`, 1–20 pour `PLOMB_APPAREIL`, 0,5–200 m²
  pour `SOL_POSE_CARRELAGE`. Chiffres d'un logement résidentiel.
- Persistance en JSON à plat sur disque plutôt qu'une base de données, avec
  écriture atomique. Pas de migration à gérer, fichier lisible à l'œil.
- **Authentification par phrase de passe unique** (`hashlib.scrypt` + jeton signé
  HMAC en cookie `HttpOnly`, `SameSite=strict`), sans nouvelle dépendance et sans
  mode ouvert : pas de phrase configurée ⇒ phrase tirée au hasard, jamais
  d'application accessible sans jeton. Convient à un poste de démo, pas à un
  multi-utilisateurs — US-01 changera cela.
- **Escalade détectée par expression régulière**, pas par le modèle : la demande
  exige une cible humaine (« humain », « conseiller », « technicien »), jamais le
  verbe seul, pour ne pas couper l'artisan sur « passe-moi la truelle ».
- Identifiant de projet par cookie `httponly`, 30 jours. Ce n'est **plus** la
  sécurité de l'application (US-23 l'a remplacée), seulement la reprise de projet.
- **US-01 codée alors que la file la disait bloquée.** Elle y figurait sous
  « demande une clé » ; en la relisant, trois de ses quatre scénarios — SIRET mal
  formé, annuaire indisponible, aucun secret au dépôt — et la totalité de ses
  critères d'accessibilité n'en demandent aucune, et le scénario nominal se teste
  derrière un transport injecté. Le choix a été de l'écrire entièrement plutôt que
  de la sauter, **et de la marquer *partiel*** : ce qui n'a pas été vérifié contre
  l'annuaire réel est nommé comme tel dans le code, dans les tests et dans la story.
- **Trois arbitrages dans US-01, tous inscrits dans `docs/STORIES.md`** : la
  validation locale précède le réseau (un numéro mal recopié ne coûte pas
  d'aller-retour) ; l'indisponibilité de l'annuaire répond **200 et non 5xx**
  (faire échouer une inscription parce qu'un tiers est en panne serait le mauvais
  arbitrage) ; un champ prérempli qu'on enregistre sans y toucher garde l'origine
  `annuaire` et reste écrasable — **accepter sans relire n'est pas décider**.
