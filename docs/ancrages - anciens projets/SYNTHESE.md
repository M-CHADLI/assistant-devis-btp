# Synthèse transverse — bonnes pratiques des projets agentiques

> Périmètre : les 5 projets de `01_vitrine` et **Kaldera V2** (`02_en_cours`), soit 6 fiches. `mardik-api-mlops` est rattaché à la fiche Mardik LLMOps. Les versions cassées `kaldera-team-ko` et `equipe-agents-qui-se-marche-dessus` servent de contre-exemples dans la fiche Kaldera.
> Chaque fiche détaille les preuves sous forme de liens `fichier:ligne`, tous vérifiés. Ce document les croise ; il ne contient pas de plan d'intégration.

| Fiche | Type | Signature | Point faible majeur |
|---|---|---|---|
| [sorabel.md](sorabel.md) | Serveur MCP gouverné : RAG hybride + Text-to-SQL | Gouvernance par décorateur, citations construites en code | Validation SQL par regex contournable |
| [velmo2.md](velmo2.md) | Agent unique outillé, mémoire longue, multi-canal | Gate qualité chiffré, mémoire RGPD versionnée | Outils sans contrôle de propriété (IDOR) |
| [the-project.md](the-project.md) | Pipeline à sortie structurée + HITL (devis BTP) | « Le modèle décrit, le code calcule » : pas de champ prix | La reprise perd la dictée d'origine |
| [mardik-support.md](mardik-support.md) | Agent support, prétexte à l'observabilité | OTel complet, rejeu de sessions, tests de mutation | Pas de vraie boucle agentique |
| [mardik-llmops.md](mardik-llmops.md) | Pipeline map → agrégation + chaîne LLMOps | Gate → artefact → canary → rollback, tous tracés | Éval en circuit fermé sur moteur factice |
| [kaldera-v2.md](kaldera-v2.md) | Multi-agents à workflow codé + A2A | Un écrivain par section, « jamais de silence » | Données personnelles envoyées au LLM d'extraction |

---

## 1. Matrice pratiques × projets

Légende : ✅ maîtrisé · ◐ partiel ou avec un défaut notable · ❌ absent ou cassé · — sans objet

| Pratique | Sorabel | Velmo2 | the-project | mARDIK | Mardik LLMOps | Kaldera V2 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Décisions métier en code, LLM cantonné | ✅ | ◐ | ✅ | ◐ | ✅ | ✅ |
| Sortie LLM structurée et validée par schéma | ❌ | ◐ | ◐ | ❌ | ◐ | ◐ |
| Distinction panne / refus / sortie invalide | ✅ | ◐ | ✅ | ◐ | ❌ | ✅ |
| Bornes d'exécution (itérations, temps, appels) | ◐ | ✅ | ✅ | ✅ | ◐ | ✅ |
| Garde-fous déterministes avant l'appel LLM | ✅ | ✅ | ✅ | ❌ | — | ✅ |
| Contrôle d'accès centralisé, fail-closed | ✅ | ❌ | ✅ | — | ❌ | ◐ |
| Minimisation des données vers LLM / tiers / logs | ✅ | ◐ | ✅ | ❌ | ✅ | ◐ |
| LLM simulé injectable (tests hors réseau) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gate d'évaluation bloquant en CI | ❌ | ◐ | ◐ | ◐ | ✅ | ✅ |
| Évaluation mesurée sur le vrai modèle | ❌ | ✅ | ◐ | ❌ | ❌ | ◐ |
| Observabilité (traces / métriques / logs corrélés) | ◐ | ✅ | ◐ | ✅ | ✅ | ◐ |
| Versioning prompt + modèle + config | ◐ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Déploiement progressif / rollback | ❌ | ❌ | ❌ | — | ✅ | ❌ |
| CI qui éprouve l'image ou la pile déployée | ◐ | ❌ | ✅ | ❌ | ◐ | ✅ |
| Décisions de conception tracées (écarté / retenu) | ✅ | ✅ | ✅ | ◐ | ✅ | ✅ |
| Tests d'architecture (frontières d'import) | ✅ | — | ✅ | — | — | — |

**Lecture rapide**
- **Point fort commun** : remplacer le LLM par un faux injectable, partout. Toutes les suites de tests tournent sans réseau ni clé.
- **Angle mort commun** : la sortie structurée et le versioning des prompts. Aucun projet ne contraint le décodage tout en versionnant ses consignes. La version de travail `mardik-api-mlops` le faisait, et ça a été abandonné.
- **Pratique la plus rare** : le déploiement progressif avec rollback, présent dans un seul projet (Mardik LLMOps).

---

## 2. Bonnes pratiques transverses, classées par impact

### A. Frontière entre le LLM et le code — impact maximal

1. **Rendre l'erreur impossible par la forme plutôt que l'interdire par le prompt.**
   - the-project : le schéma de sortie n'a pas de champ prix, donc le modèle ne peut pas en inventer ([schema.py:1](../the-project/app/schema.py:1)).
   - Sorabel : le prompt interdit au LLM de citer ses sources ; les citations sont reconstruites à partir des métadonnées des extraits ([generation.py:59](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/sorabel_rag/generation.py:59>)).
   - Même idée dans les deux cas : on retire au modèle le canal par lequel il pourrait halluciner.

2. **Toute décision qui engage est prise par du code pur et testable.**
   - Kaldera : les règles §10 sont dans une seule fonction ordonnée, avec des montants exacts au centime ([decision.py:14](<../../02_en_cours/Kaldera V2/src/kaldera/decision.py:14>)).
   - the-project : catalogue, rendements, TVA et mentions réglementaires sont calculés par le code.
   - Mardik LLMOps : 75 % du score de confiance est calculé en code.
   - Le LLM se limite à structurer, rédiger ou signaler.

3. **Un LLM auxiliaire est un signal, jamais une correction.**
   - Kaldera : la revue LLM tourne sur une copie, dans un temps borné, et ne modifie jamais l'issue ([revue.py:142](<../../02_en_cours/Kaldera V2/src/kaldera/revue.py:142>)).
   - the-project : la reformulation de dictée est jetée dès que les nombres ou les unités changent ([transcription.py:84](../the-project/app/transcription.py:84)).
   - Sorabel : le reranker produit une note, mais le seuil de refus s'applique à la note brute, pas à la note bonifiée.

4. **Refuser en code, avant l'appel, sans payer de génération.**
   - Sorabel : refus « hors corpus » sous le seuil, et lexique sensible vérifié avant le Text-to-SQL ([generation.py:40](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/sorabel_sql/generation.py:40>)).
   - the-project : les demandes hors périmètre sont court-circuitées avant le modèle.
   - Kaldera : la décision s'arrête dès qu'une règle conclut, ce qui évite tout appel partenaire inutile.

### B. Fiabilité et gestion des échecs

5. **Classer les échecs et donner à chaque type sa réponse.**
   - the-project distingue `SortieModeleInvalide` (on retente) et `ModeleInjoignable` (on escalade sans retenter) ([llm.py:58](../the-project/app/llm.py:58)).
   - Kaldera classe chaque issue d'appel externe par couche : `delai`, `panne`, `transport`, `schema`, `plausibilite`, `doublon`, `disjoncteur` ([partenaire.py:44](<../../02_en_cours/Kaldera V2/src/kaldera/partenaire.py:44>)).

6. **Une panne n'est jamais déguisée en résultat métier.**
   - Sorabel lève `RerankIndisponible` au lieu de renvoyer des notes nulles qui produiraient un faux « hors corpus » ([recherche.py:329](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/sorabel_rag/recherche.py:329>)).
   - *Contre-exemple* : la v2 de Mardik LLMOps avale les pannes du moteur, si bien que le rollback sur taux d'erreur ne peut jamais se déclencher (§3).

7. **Le budget de reprises appartient à un seul niveau.**
   - the-project : `app.llm` ne boucle pas, seul le pipeline borne à 2 appels par message ([pipeline.py:34](../the-project/app/pipeline.py:34)).
   - Ça évite les reprises imbriquées, qui multiplient le coût sans qu'on le voie.

8. **Des bornes nommées, justifiées, et une étape réservée à la conclusion.**
   - Kaldera : `etapes_max` est calculé (9 étapes au pire + 3 de marge), et la vérification lève avant d'atteindre la borne ([bornes.py:11](<../../02_en_cours/Kaldera V2/src/kaldera/bornes.py:11>)).
   - Velmo2 : la boucle d'outils est limitée à 3 itérations, avec un test qui fait demander un outil en boucle au faux LLM ([agent.py:13](../Velmo2/src/velmo/agent/agent.py:13)).
   - *Contre-exemple* dans `kaldera-team-ko` : la borne est calculée mais jamais appliquée.

9. **Un délai d'appel externe pris sur le budget restant.**
   - Kaldera : `min(3 s, duree_max − écoulé − 0,5)`, donc l'appel A2A ne peut jamais faire dépasser la borne globale ([superviseur.py:74](<../../02_en_cours/Kaldera V2/src/kaldera/superviseur.py:74>)).

10. **« Jamais de silence » : toute exception aboutit à une sortie motivée.**
    - Kaldera capture à trois niveaux, et chacun produit une escalade avec le champ `arret` rempli ([superviseur.py:81](<../../02_en_cours/Kaldera V2/src/kaldera/superviseur.py:81>)).
    - Velmo2 bloque par défaut si le classifieur tombe ([input_guard.py:27](../Velmo2/src/velmo/guardrails/input_guard.py:27)).

11. **Un tour atomique, sans effet de bord avant l'étape qui peut échouer.**
    - mARDIK : le message utilisateur et la réponse sont enregistrés ensemble, sous verrou, après l'appel LLM ([session.py:32](../mARDIK/src/mardik/session.py:32)).
    - Un timeout ne laisse donc plus de message orphelin.

### C. Sécurité et gouvernance

12. **Un point de passage unique pour la gouvernance, fail-closed.**
    - Sorabel : le décorateur `_gouverne` résout le périmètre, contrôle le droit, journalise, puis exécute. Une identité qu'on ne peut pas établir vaut un refus ([tools.py:61](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/mcp_server/tools.py:61>)).
    - the-project : authentification par liste blanche dans un middleware, donc toute nouvelle route est protégée par défaut ([main.py:115](../the-project/app/main.py:115)).

13. **Le LLM client ne voit pas ses propres droits.**
    - Sorabel : le paramètre `perimetre` est retiré du schéma MCP exposé, et un test le vérifie ([tools.py:106](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/mcp_server/tools.py:106>)).

14. **Moindre privilège par vues construites pour chaque agent.**
    - Kaldera : chaque agent reçoit un dictionnaire préparé pour lui, jamais la demande complète ([vues.py:10](<../../02_en_cours/Kaldera V2/src/kaldera/vues.py:10>)).
    - Sorabel : le schéma SQL envoyé au LLM est filtré selon le profil.

15. **Liste blanche en sortie, validation en couches en entrée.**
    - Kaldera : la requête A2A est reconstruite champ par champ (7 champs). La réponse est validée en trois couches : transport, schéma, plausibilité ([partenaire.py:139](<../../02_en_cours/Kaldera V2/src/kaldera/partenaire.py:139>)).

16. **Des invariants de sécurité vérifiés au démarrage.**
    - Sorabel : si la matrice d'accès est incohérente, Pydantic empêche le serveur de démarrer ([modeles.py:38](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/gouvernance/modeles.py:38>)).
    - the-project : la CI vérifie qu'une route protégée répond bien 401 dans l'image livrée ([livraison.yml:53](../the-project/.github/workflows/livraison.yml:53)).

17. **Défense en profondeur sur le Text-to-SQL.**
    - Sorabel : connexion `mode=ro`, liste blanche de requêtes, `LIMIT`, timeout ([execution.py:33](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/sorabel_sql/execution.py:33>)).
    - À compléter par un vrai parseur SQL ou `set_authorizer` (§3).

18. **Une double lecture contre l'injection de prompt.**
    - Kaldera : sur les champs critiques, si la lecture du LLM et la lecture déterministe divergent, le traitement est bloqué et la valeur prudente est retenue ([extraction.py:614](<../../02_en_cours/Kaldera V2/src/kaldera/extraction.py:614>)).
    - Le tout est évalué par un banc d'attaques versionné.

### D. Évaluation et qualité

19. **Un gate qui bloque par construction, pas par convention.**
    - Mardik LLMOps : le job de build déclare `needs: gates`, et l'évaluation sort en code 1 sous le seuil ([llmops.yml:84](../Mardik%20deployement/.github/workflows/llmops.yml:84)).
    - Velmo2 : la note est pondérée 40/40/20 avec un seuil, et l'historique est lié au SHA git ([run_eval.py:36](../Velmo2/mlops/run_eval.py:36)).

20. **Séparer une CI gratuite et déterministe d'une CI payante sur le vrai modèle.**
    - Velmo2 : `ci.yml` est mocké et tourne à chaque push ; `quality.yml` utilise le vrai LLM et se lance à la main ([quality.yml:13](../Velmo2/.github/workflows/quality.yml:13)).
    - Mardik LLMOps : le moteur factice est un composant de production activé par variable d'environnement, pas un mock de test.

21. **Prouver que les tests attrapent bien les bugs.**
    - mARDIK : chaque bug d'origine est réintroduit et la suite doit échouer. C'est ce qui a montré qu'on pouvait retirer un verrou sans qu'aucun test ne casse ([INCIDENTS_ET_OBSERVABILITE.md:232](../mARDIK/docs/INCIDENTS_ET_OBSERVABILITE.md:232)).
    - the-project : le validateur de dataset est testé sur un gabarit d'exemples fautifs ([valider_dataset.py:266](../the-project/tools/mlops/valider_dataset.py:266)).
    - Velmo2 : on montre que la note tombe quand la configuration est volontairement dégradée.

22. **Rejouer des sessions enregistrées à travers la vraie pile.**
    - mARDIK : le JSON de session contient son propre bloc `expected` ([runner.py:24](../mARDIK/src/mardik/runner.py:24)).
    - Kaldera : 28 scénarios rejoués 3 fois pour mesurer la stabilité, plus une CI qui rejoue un scénario de panne sur la pile Docker déployée ([ci.yml:59](<../../02_en_cours/Kaldera V2/.github/workflows/ci.yml:59>)).

23. **Être honnête sur ce qu'on ne mesure pas.**
    - the-project : une métrique non mesurable est marquée « non mesurée » plutôt qu'approchée ([observabilite.py:40](../the-project/app/observabilite.py:40)).
    - the-project : le pipeline MLOps a trois états, et « pas encore lancé » n'est jamais « réussi » ([executer.py:36](../the-project/tools/mlops/executer.py:36)).

24. **Capturer les corrections humaines pour alimenter l'entraînement ou l'évaluation.**
    - the-project : chaque correction devient un triplet entrée / sortie du modèle / corrigé, avec son origine ([boucle_qualite.py:41](../the-project/app/boucle_qualite.py:41)).
    - Mardik LLMOps : les cas à faible confiance sont pseudonymisés avant d'être écrits sur disque, puis relus par un humain avant d'entrer dans `golden.jsonl` ([enrichissement.py:59](../Mardik%20deployement/src/mardik/boucles/enrichissement.py:59)).

### E. Livraison et LLMOps

25. **L'identité de version couvre le code, le modèle et la configuration.**
    - Mardik LLMOps : l'empreinte des seuils entre dans la version servie, et chaque signal la porte ([config.py:114](../Mardik%20deployement/src/mardik/config.py:114)).
    - Seul projet qui sait attribuer un comportement observé à une version précise.

26. **Un point unique de bascule du trafic, toujours tracé.**
    - Mardik LLMOps : `definir_poids` journalise le signal, la valeur observée, le seuil, l'auteur, et le poids avant et après ([canary.py:45](../Mardik%20deployement/src/mardik/api/canary.py:45)).
    - Une promotion refusée est aussi enregistrée comme décision.

27. **Le rollback se déclenche sur la queue de distribution, pas sur la moyenne.**
    - Mardik LLMOps : rollback si plus de 25 % des analyses sont sous 0,60, puis promotion gelée pour éviter l'oscillation ([rollback.py:31](../Mardik%20deployement/src/mardik/boucles/rollback.py:31)).

28. **Contrat v2 ⊇ contrat v1, avec un témoin exécutable.**
    - Mardik LLMOps : `ReponseV2(ReponseV1)` n'ajoute que des champs, et un client v1 « à ne jamais modifier » le vérifie ([schemas.py:37](../Mardik%20deployement/src/mardik/api/schemas.py:37)).

29. **Éprouver l'artefact avant de le publier.**
    - Démarrage réel, sonde de santé et assertion fonctionnelle dans la CI : the-project, Mardik LLMOps, Kaldera.
    - Pour bien faire, il faut publier exactement l'image éprouvée, par digest (§3).

### F. Observabilité et audit

30. **Corréler logs et traces, et propager le contexte dans les threads.**
    - mARDIK : un processeur structlog ajoute `trace_id` et `span_id` aux logs ; `copy_context().run` propage le contexte vers le thread du LLM ([agent.py:63](../mARDIK/src/mardik/agent.py:63)).

31. **Contrôler la cardinalité des métriques.**
    - mARDIK : `session_id` va sur les spans et les logs, jamais en attribut de métrique, et un test le garantit ([test_telemetry.py:67](../mARDIK/tests/unit/test_telemetry.py:67)).

32. **Un journal d'audit qui ne devient pas une fuite.**
    - Sorabel : une ligne par appel, refus compris, mais jamais le contenu des résultats ([journal.py:1](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/gouvernance/journal.py:1>)).
    - Velmo2 et the-project : l'écriture du journal ne bloque jamais la réponse.

33. **Observer sans avaler les erreurs.**
    - mARDIK : `track_turn` mesure, compte, journalise, puis relance toujours l'exception ([telemetry.py:114](../mARDIK/src/mardik/telemetry.py:114)).

### G. État, mémoire, multi-agents

34. **Un seul écrivain, et un auteur par section d'état.**
    - Kaldera : l'état refuse toute écriture hors section et toute réécriture d'une section définitive ([etat.py:10](<../../02_en_cours/Kaldera V2/src/kaldera/etat.py:10>)).
    - C'est la correction directe du défaut « agents qui se marchent dessus » de `kaldera-team-ko`, où tous les agents écrivent dans un `dict` libre.

35. **Un ordre fixe en code plutôt qu'un routeur LLM.**
    - Kaldera : la terminaison est garantie, et chaque `return` correspond à une règle numérotée de la spec ([superviseur.py:114](<../../02_en_cours/Kaldera V2/src/kaldera/superviseur.py:114>)).
    - Velmo2 et the-project : le pipeline est lui aussi codé en dur.

36. **Une mémoire longue gouvernée.**
    - Velmo2 : seuil de confiance, 3 versions conservées, suppression logique pour le RGPD, journal d'audit ([long_term.py:102](../Velmo2/src/velmo/memory/long_term.py:102)).
    - Le contexte d'origine est stocké avec chaque fait, pour cibler l'oubli même quand la clé est mal choisie.

### H. Méthode et documentation

37. **Un dossier de conception écrit avant le code, au format écarté / retenu / limite assumée.**
    - Mardik LLMOps ([dossier-de-conception.md:48](../Mardik%20deployement/docs/dossier-de-conception.md:48)), Kaldera, Sorabel, Velmo2.

38. **Un journal de décisions unique, et une doc qui décrit l'état courant.**
    - the-project : `DECISIONS.md` sert d'ADR, et une décision s'écrit dans le même commit que la doc d'état ([CLAUDE.md:32](../the-project/CLAUDE.md:32)).
    - Kaldera : chaque ajustement part d'un scénario rejoué, avec des preuves avant/après et la liste des ajustements écartés ([journal-ajustements.md:9](<../../02_en_cours/Kaldera V2/docs/journal-ajustements.md:9>)).

39. **Les critères du brief transcrits en tests d'acceptance, qui définissent « fini ».**
    - Mardik LLMOps (10 critères) et Kaldera (56 tests d'acceptance).

40. **Un `CLAUDE.md` court et normatif, qui renvoie au dossier technique.**
    - Sorabel et the-project : contraintes non négociables, frontière entre modèle et code, pièges déjà rencontrés.

---

## 3. Anti-patterns récurrents

Classés par nombre de projets touchés.

| # | Anti-pattern | Projets | Remède observé ailleurs |
|---|---|---|---|
| 1 | **Évaluation en trompe-l'œil** : elle ne mesure pas le système livré (faux LLM à mots-clés, pipeline d'éval différent de la prod, moteur factice qui définit lui-même le « juste », runner jamais écrit) | Velmo2 ([test tautologique](../Velmo2/tests/test_agent_e2e_guardrails.py:23), [éval mémoire](../Velmo2/scripts/eval_memory.py:41)), Mardik LLMOps ([circuit fermé](../Mardik%20deployement/src/mardik/modele/llm.py:32)), mARDIK, Sorabel (E6 absente), the-project (pas de jeu de test) | CI payante séparée (Velmo2 `quality.yml`), bout en bout sur pièces réelles (Kaldera 15/15) |
| 2 | **Sortie LLM extraite entre la première `{` et la dernière `}`**, puis validée à la main | Sorabel, Kaldera, the-project, Velmo2 (Judge), mARDIK (pas de sortie structurée du tout) | `response_format` + JSON schema strict, version de travail [`mardik-api-mlops`](../../02_en_cours/mardik-api-mlops/models/v2/config.yaml:48) |
| 3 | **Prompts non versionnés et non tracés** : impossible de rattacher une mesure au prompt qui l'a produite | 5 sur 6 | Instantanés de prompts (Sorabel), empreinte de version (Mardik LLMOps), bundle YAML (`mardik-api-mlops`) |
| 4 | **Surfaces non authentifiées** à côté d'un cœur bien protégé | Velmo2 (IDOR, [webhook SMS](../Velmo2/apps/sms_server/main.py:62)), Mardik LLMOps ([endpoints de pilotage](../Mardik%20deployement/src/mardik/api/app.py:261)), Kaldera ([console publique](<../../02_en_cours/Kaldera V2/src/kaldera/web.py:217>)) | Middleware en liste blanche (the-project), décorateur de gouvernance (Sorabel) |
| 5 | **Fuite de données personnelles** vers le LLM ou les traces, contredisant la minimisation pratiquée ailleurs dans le même projet | Kaldera ([IBAN vers Azure](<../../02_en_cours/Kaldera V2/src/kaldera/extraction.py:325>)), mARDIK ([I/O d'outils en traces](../mARDIK/src/mardik/agent.py:86)), Velmo2 (payload SMS en INFO, message recopié dans l'audit RGPD) | Liste blanche de champs (Kaldera revue / A2A), pseudonymisation avant disque (Mardik LLMOps) |
| 6 | **Appel LLM sans timeout ni plafond de coût, ou thread abandonné qui continue à facturer** | Sorabel ([client.py:63](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/sorabel_llm/client.py:63>)), Velmo2, Kaldera ([revue.py:156](<../../02_en_cours/Kaldera V2/src/kaldera/revue.py:156>)), mARDIK | Délai pris sur le budget restant (Kaldera A2A), `timeout` + `max_retries` explicites |
| 7 | **Doc désynchronisée du code** : un document désigné comme source de vérité ment | Sorabel ([conception.md:600](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/docs/conception.md:600>)), Velmo2 (Kimi / DeepSeek / Redis), the-project ([modele.yml:4](../the-project/.github/workflows/modele.yml:4)), Mardik LLMOps (workflow annoncé mais absent) | Règle « même commit » (the-project), à faire respecter par la CI |
| 8 | **Promesse d'audit non tenue** : les pannes échappent au journal, l'état et le journal ne sont pas atomiques, le journal n'est pas persistant | Sorabel ([exceptions hors journal](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/mcp_server/tools.py:96>)), Mardik LLMOps ([canary.py:62](../Mardik%20deployement/src/mardik/api/canary.py:62)) | `try/finally` dans le point de passage unique, journal écrit avant l'effet |
| 9 | **Panne avalée et déguisée en résultat métier** | Mardik LLMOps ([v2.py:68](../Mardik%20deployement/src/mardik/modele/v2.py:68)), Velmo2 ([embedding aléatoire silencieux](../Velmo2/src/velmo/memory/long_term.py:46)) | `RerankIndisponible` (Sorabel), typologie d'échecs (the-project, Kaldera) |
| 10 | **État global mutable ou configuration figée à l'import** | Sorabel (enseigne), Velmo2 ([identité des outils dans un dict module](../Velmo2/src/velmo/business/tools.py:10)), mARDIK (store partiellement verrouillé) | Injection de dépendances (Velmo2 `VelmoAgent`, mARDIK `Telemetry`) |
| 11 | **Règles métier recopiées dans le prompt**, qui dérivent de leurs constantes | Kaldera ([revue.py:303](<../../02_en_cours/Kaldera V2/src/kaldera/revue.py:303>)) | Interpoler le prompt depuis le référentiel (the-project : `lot_code` injectés) |
| 12 | **Fenêtre de décision non réinitialisée** : une promotion ou un rollback relit d'anciens signaux | Mardik LLMOps ([promotion.py:42](../Mardik%20deployement/src/mardik/boucles/promotion.py:42)) | Filtrer par version et par horodatage (`mardik-api-mlops`, `deploy.py`) |

Correctifs de sécurité concrets à appliquer dans les projets existants :
- **Sorabel** : `SELECT v.marge_ht FROM produits p, ventes v` et `FROM "ventes"` passent `valider()` avec le périmètre « support » ([validation.py:20](<../Sorabel - l'agent augmenté par la donnée, exposé via MCP/sorabel_sql/validation.py:20>)).
- **Velmo2** : `lookup_order` et `get_customer_orders` ne filtrent pas par client ([tools.py:50](../Velmo2/src/velmo/business/tools.py:50)).
- **Kaldera V2** : nom, email, téléphone et IBAN partent vers Azure OpenAI depuis une console sans authentification.

---

## 4. Signatures originales à retenir

- **« Un champ absent vaut mieux qu'une consigne »** (the-project) : l'interdiction passe par le schéma, pas par le prompt.
- **Stable avant volatil** (the-project) : l'humain valide la structure du devis, et le prix n'est calculé qu'ensuite.
- **LLM cosmétique sous contrat numérique** (the-project) : la reformulation est libre, sauf les nombres et unités, vérifiés par multiensemble.
- **Filtre déguisé en bonus** (Sorabel) : une référence détectée fait passer le document en tête sans exclure les autres, mais le seuil de refus lit la note brute.
- **Gouvernance différente selon le transport** (Sorabel) : en stdio, les tools hors périmètre n'existent pas ; en HTTP, le profil est relu dans le jeton à chaque appel.
- **Revue « signal, jamais correction »** avec trois réviseurs interchangeables (Kaldera) : règles, LLM, modèle calibré.
- **Partenaire A2A double** (Kaldera) : un simulateur pilotable (panne, lent, invalide) pour la recette, et un vrai partenaire sans routes de simulation.
- **« L'absence de promotion est aussi une décision »** (Mardik LLMOps) : on journalise ce qu'on n'a pas fait, avec la valeur observée et le seuil.
- **Dérive simulée qui change les entrées, pas les scores** (Mardik LLMOps) : c'est l'observabilité réelle qui doit la détecter.
- **Lire les trois signaux comme un opérateur** (mARDIK) : chaque incident est rejoué, puis vérifié à la fois sur la trace, les métriques et le log.
- **Garde-fou de destination des données** (the-project) : l'export refuse d'écrire sur un dossier synchronisé (OneDrive, NFS…).
- **Déclarer ce qu'on ne sait pas faire** (Kaldera, the-project) : « photo exigée mais non analysée » plutôt qu'une vérification simulée.

---

## 5. Constats d'ensemble

1. **Ta signature d'architecte est constante : le LLM propose, le code dispose.** Les meilleurs projets (the-project, Kaldera, Sorabel) poussent cette frontière jusqu'au schéma de données. C'est la pratique la plus différenciante du portfolio.
2. **La rigueur d'ingénierie dépasse la rigueur d'évaluation.** Tests, CI, observabilité et documentation sont solides partout. En revanche, la qualité du *vrai* modèle n'est mesurée de façon automatisée et reproductible dans aucun projet. C'est l'écart le plus systématique.
3. **La sécurité est excellente au centre et faible en périphérie.** Gouvernance, minimisation et listes blanches sont soignées sur le chemin principal. Les surfaces annexes (webhook, console, endpoints de pilotage, extraction) sont oubliées.
4. **Les bonnes pratiques existent, mais dispersées.** Sortie structurée stricte, versioning de bundle, filtrage des fenêtres par version : `mardik-api-mlops` les avait, et la version aboutie les a perdues. Chaque projet maîtrise un pan (gouvernance, LLMOps, observabilité, multi-agents, HITL), aucun ne les réunit tous.
5. **Les meilleurs garde-fous sont structurels, pas déclaratifs.** Un champ absent, `needs: gates`, une table d'auteurs, un `mode=ro` : ce sont eux qui tiennent. Les promesses écrites seulement dans la doc (audit complet, gate bloquant, workflow séparé) sont celles qui ont été trouvées fausses.
