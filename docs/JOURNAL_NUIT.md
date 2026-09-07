# Journal de la session de nuit — reprise après arrêt

**Fichier de reprise.** Si la session s'est arrêtée (interruption, plantage,
contexte compacté), tout ce qu'il faut pour repartir est ici. Le lire d'abord,
le mettre à jour à chaque étape franchie.

Dernière mise à jour : **08/09/2026**, commit `d783b9a`.

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
- Commande de test : `VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync pytest`

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

- **62 tests, tous verts** (`62 passed`). Suites : `test_referentiel` 8,
  `test_devis` 12, `test_pipeline` 21, `test_persistance` 9, `test_api` 12.
- L'application démarre depuis n'importe quel répertoire, sert `/`, expose
  `/`, `/api/devis`, `/api/message`, `/api/corriger`, `/api/quantite`,
  `/api/reset`, `/api/export`, plus `/docs` et `/openapi.json`.
- Ollama répond sur `localhost:11434` et sert `gpt-oss:20b`.
- Le JavaScript du front passe `node --check`
  (node en `~/.nvm/versions/node/v22.22.2/bin`, pas dans le PATH par défaut).

## Fait cette nuit

| Commit | Contenu |
|---|---|
| `01ee0c5` | 26 stories, 7 épiques, kit de transposition Notion (CSV + schémas + CLI) |
| `a781711` | CLAUDE.md remis en accord avec le dépôt réel |
| `e669883` | `app/` et `tests/` versionnés pour la première fois + anomalies S1 |
| `7662a44` | Bornes de plausibilité (US-11), plafond de clarification (US-07) |
| `d783b9a` | Accessibilité RGAA 4.1 du front + arbitrage des quantités côté interface |

Détail des anomalies fermées : branche `quantitatif` manquante au routeur ;
reprises de `llm` et `pipeline` qui se composaient (jusqu'à 4 appels modèle par
message, désormais 2) ; escalades sans motif ; `Session` unique de module
partagée par tous les visiteurs et perdue au redémarrage ; `index.html` ouvert
par chemin relatif ; Ollama arrêté qui provoquait un 500.

---

## File de travail — prendre dans l'ordre

1. **Audit des critères du jury** contre `reference/referentiel-rncp-ai-engineer.xlsx`
   (le fichier source, pas sa paraphrase dans `docs/LIVRABLES.md`). Produire un
   tableau compétence par compétence : couverte / partielle / absente, avec la
   preuve dans le dépôt. Mettre à jour `docs/LIVRABLES.md` ensuite.
2. **Conformité du devis** (`app/export.py`, US-15) : délai d'exécution, identité
   du client, adresse de chantier, RCS, code APE/NAF, TVA intracommunautaire, et
   surtout le cas **article 293 B** (franchise de base) — aujourd'hui la TVA est
   appliquée inconditionnellement.
3. **Régime de TVA de l'artisan** (US-02) : le stocker au profil, le faire porter
   par le devis. Prérequis de la tâche 2.
4. **HITL-0, relecture de la transcription** (US-05) : écran de relecture avant
   traitement, et journalisation de l'écart transcrit/corrigé comme signal qualité.
5. **HITL-2, validation avant chiffrage** (US-12) : séparer la construction de la
   structure et l'injection des prix. Aujourd'hui le chiffrage est immédiat.
6. **Neutralisation des injections de prompt** (US-20, `DISPOSITIF_AGENT.md` §3.1) :
   neutraliser **et journaliser** — la journalisation compte autant.
7. **Détection du hors périmètre** (US-19).
8. **Authentification** (US-23, C9/C17/C21), **observabilité** (US-24, C11/C20),
   **OpenAPI contractuel** (US-22, C5/C9).
9. **Chaîne d'intégration continue** (US-26, C18/C19).
10. **Séance de veille tracée** dans `veille/seances/` — le dossier est **vide**,
    et C6 exige une trace hebdomadaire. Suivre `veille/GABARIT-SEANCE.md`.
11. **Fragilité des tests** : `tests/test_devis.py` recopie en dur des valeurs du
    référentiel et du catalogue (taux de chute 0,05, rendement 0,1, contenance 10,
    prix 34,90, promo 0,10). Le jour où une valeur métier bouge, le test casse
    alors que le code est juste. Les lire depuis la source.
12. **Mettre à jour `docs/STORIES.md`** (lignes de traçabilité « état du code
    constaté ») et les CSV de `docs/notion/`. C'est dans la définition de fini.

## À signaler à l'utilisateur au réveil

- `.env` contient des clés qui ont l'air vivantes (Gladia, Azure AI Foundry). Le
  fichier est ignoré par git et n'a **jamais** été committé — vérifié sur tout
  l'historique. Mais elles se sont affichées en clair dans la sortie terminal de
  cette session : si elle a été partagée ou conservée, faire tourner les clés.
- Le CLI Notion attend un `NOTION_TOKEN` dans `.env`, plus le partage de la page
  racine avec l'intégration (menu `⋯` → Connexions). Sans ce partage l'API
  renvoie une liste vide, pas une erreur.
- Point non tranché qui appartient à l'utilisateur : **Gladia (distant) contre
  Whisper local**. Le prototype actuel utilise la Web Speech API du navigateur,
  qui envoie l'audio à l'éditeur — contradiction avec la règle « 100 % local ».

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
- Identifiant de projet par cookie `httponly`, 30 jours. Ce n'est pas de
  l'authentification — celle-ci reste à faire (US-23).
