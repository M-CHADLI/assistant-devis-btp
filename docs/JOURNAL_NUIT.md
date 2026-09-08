# Journal de la session de nuit — reprise après arrêt

**Fichier de reprise.** Si la session s'est arrêtée (interruption, plantage,
contexte compacté), tout ce qu'il faut pour repartir est ici. Le lire d'abord,
le mettre à jour à chaque étape franchie.

Dernière mise à jour : **08/09/2026**, commit `8270c9f`.

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

- **245 tests, tous verts.** Répartition : `test_garde_fous` 52, `test_api` 29,
  `test_boucle_qualite` 24, `test_front` 24, `test_pipeline` 23, `test_auth` 19,
  `test_devis` 12, `test_transcription` 12, `test_export` 11,
  `test_observabilite` 11, `test_persistance` 11, `test_contrat_api` 9,
  `test_referentiel` 8.
- **Stories : 16 faites, 7 partielles, 3 à faire** (compté depuis les lignes de
  traçabilité de `docs/STORIES.md`, pas depuis un tableau recopié).
  - *fait* : US-02, 05, 08, 10, 11, 12, 13, 15, 16, 19, 20, 21, 22, 23, 24, 25
  - *partiel* : US-04, 06, 07, 09, 14, 18, 26
  - *à faire* : US-01, 03, 17
- L'application démarre depuis n'importe quel répertoire et **exige désormais une
  authentification** : seuls `/` et `POST /api/session` sont ouverts, tout le
  reste répond 401 sans jeton — y compris `/docs` et `/openapi.json`.
  Sans `BTP_MOT_DE_PASSE`, une phrase de passe aléatoire est tirée et **affichée
  une fois au démarrage** ; elle change à chaque redémarrage.
- Le JavaScript du front passe `node --check`
  (node en `~/.nvm/versions/node/v22.22.2/bin`, pas dans le PATH par défaut).
- `tools/verifier_accessibilite_docs.py` : **17 documents conformes**.
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

**Rien n'est poussé.** Vingt commits sur `docs/pivot-btp-vocal-docs`, aucun `push`.

---

## File de travail — prendre dans l'ordre

Les douze premières tâches de la file initiale sont **faites**, sauf celles
listées ci-dessous. Nouvelle file :

1. **Transposer sur Notion** — les CSV de `docs/notion/` sont à jour de cette
   nuit. Bloqué sur `NOTION_TOKEN` + partage de la page racine avec l'intégration
   (menu `⋯` → Connexions). Sans ce partage l'API rend une liste vide, pas une erreur.
2. **Séances de veille** (C6) : `veille/seances/` est **vide** et le référentiel
   exige une trace hebdomadaire. Quatre séances à écrire d'après
   `veille/GABARIT-SEANCE.md`, thématique Unsloth / fine-tuning MoE.
3. **RGPD** (C4-26/27/28) : registre des traitements et procédures de tri des
   données. `donnees/` contient des noms et adresses de clients — voir l'alerte
   plus bas.
4. **Modèle de données Merise** (C4-19, C14-103) et **maquettes** (C14-104,
   C17-121) : deux livrables attendus, absents du dépôt.
5. **Benchmark STT** avec colonne éco-responsabilité (C7, C15-110, C17-126).
   Dépend de l'arbitrage Gladia contre Whisper local, qui appartient à l'utilisateur.
6. **Stories partielles** : US-04, US-06, US-07, US-09, US-14, US-18, US-26.
7. **Fragilité des tests** : `tests/test_devis.py` recopie en dur des valeurs du
   référentiel et du catalogue (taux de chute 0,05, rendement 0,1, contenance 10,
   prix 34,90, promo 0,10). Le jour où une valeur métier bouge, le test casse
   alors que le code est juste. Les lire depuis la source.
8. **Stories à faire** : US-01 (compte par SIRET, API Pappers), US-03, US-17.

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
- **Aucun `remote` git** n'est configuré : neuf critères du jury (revue de code,
  CI observable, collaboration) restent bloqués tant que le dépôt est local.
- Point non tranché qui appartient à l'utilisateur : **Gladia (distant) contre
  Whisper local**. Le prototype actuel utilise la Web Speech API du navigateur,
  qui envoie l'audio à l'éditeur — contradiction avec la règle « 100 % local ».
- Les tâches cron programmées cette nuit **vivent dans cette session seulement** et
  expirent d'elles-mêmes au bout de sept jours. Elles ne survivront pas à la
  fermeture de la session.

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
