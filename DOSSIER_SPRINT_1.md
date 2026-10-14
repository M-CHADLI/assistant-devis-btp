# Dossier de conception V1 — sprint 1

**Le fil conducteur.** Un artisan dicte son chantier ; l'application lui prépare un devis qu'il corrige, puis chiffre sans jamais inventer un prix. Le dossier suit ce fil : à qui ça sert (§1), ce qu'on construit en six jours et ce qu'on laisse de côté (§2, §3), comment l'agent raisonne (§4), avec quels outils (§5), comment tout s'assemble et arrive en production (§6), comment on saura que c'est fini (§7) et dans quel ordre on avance (§8).

## 1. Le besoin

> 🧭 Le point de départ : un artisan, un problème de temps, une promesse.

### A. Pour qui

**Des artisans** ou petites entreprises du bâtiment : peinture, sols, plomberie, électricité.
Plusieurs artisans utilisent l'application en même temps, **chacun avec ses propres projets de
devis**, isolés de ceux des autres. Leur client final n'a ni compte ni écran.

### B. Le problème

Sur le chantier, l'artisan prend ses mesures et ses notes. Le soir, il doit en
tirer un devis : quantités, consommables qu'on oublie toujours, taux de TVA (taxe sur la valeur
ajoutée), mentions obligatoires du BTP (bâtiment et travaux publics). C'est long, et une erreur
de prix ou de mention coûte cher.

### C. Le parcours promis

> 💡 **En bref** : L'agent prépare, l'artisan décide : il corrige et valide, il ne saisit jamais tout.

L'application est un **copilote** : l'agent pré-remplit le devis en suggestions grisées, l'artisan
garde la main — il accepte, modifie, supprime ou ajoute des blocs, au clic ou à la voix. Le
bouton **« Générer »** complète les vides et calcule les prix : aucun prix n'apparaît avant.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 420}}}%%
flowchart TB
  e1["🗣️ <b>1. Dicter</b><br/>Sur le chantier, mains occupées :<br/>pièces, surfaces, travaux, contraintes"]
  e2["🔄 <b>2. L'agent reformule et comprend</b><br/>Automatique, sans relecture de l'artisan"]
  e3["✨ <b>3. L'agent pré-remplit le devis</b><br/>Lots, ouvrages, quantités, consommables<br/>en <b>suggestions grisées</b> ; une question ciblée si un manque bloque"]
  e4["✍️ <b>4. L'artisan édite, comme avec un copilote</b><br/>Accepte, modifie, supprime, ajoute un bloc<br/>au clic ou à la voix"]
  e5["⚙️ <b>5. Bouton « Générer »</b><br/>Complète les vides, résout les prix,<br/>calcule conditionnements, TVA, totaux"]
  e6["📄 <b>6. Ajuster, puis exporter</b><br/>L'artisan a le dernier mot sur chaque ligne<br/>Fichier Word avec les mentions obligatoires"]

  e1 --> e2 --> e3 --> e4
  e4 -- "🎙️ dicte encore : l'agent complète" --> e3
  e4 -- "⚙️ Générer" --> e5 --> e6
  e6 -. "modifie encore, puis regénère" .-> e4

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef cle fill:#1168bd,stroke:#0b4884,color:#ffffff
  class e1,e2,e3,e6 etape
  class e4,e5 cle
```

### D. Le principe : le modèle décrit, le code calcule

> 💡 **En bref** : Un modèle de langage peut se tromper sur un chiffre ; on ne lui confie donc jamais un prix. Il décrit les travaux, le code fait les calculs.

Le LLM (grand modèle de langage) ne produit jamais un montant.

```mermaid
flowchart TB
  texte["🗣️ <b>Message dicté, reformulé par l'agent</b><br/>« salon 22 m², murs à repeindre, sol stratifié »"]

  subgraph modele["🤖 Le modèle DÉCRIT"]
    direction TB
    m1["📚 S'appuie sur les passages du corpus technique"]
    m2["📋 Rend un JSON qui suit un schéma unique :<br/>intention, lots, quantités techniques, mention"]
    m3["🚫 <b>Le schéma n'a pas de champ prix</b><br/>Le modèle ne peut pas en inventer"]
    m1 --> m2 --> m3
  end

  subgraph code["🧮 Le code CALCULE"]
    direction TB
    c1["✅ Contrôle : schéma, ouvrages référencés ou génériques, quantités plausibles"]
    c2["🏷️ Prix et conditionnements lus dans le catalogue"]
    c3["💶 Quantités d'achat, TVA par taux, totaux, acompte"]
    c1 --> c2 --> c3
  end

  devis["📄 <b>Devis chiffré, chaque ligne sourcée</b><br/>Zéro prix inventé, par construction"]

  texte --> modele
  modele -- "JSON sans prix" --> code
  code --> devis

  classDef bord fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef fin fill:#1168bd,stroke:#0b4884,color:#ffffff
  class texte,m1,m2,m3,c1,c2,c3 bord
  class devis fin
```

## 2. Périmètre V1 — six jours de développement

> 🧭 De la promesse au chantier : ce qu'on construit concrètement, jour par jour.

### A. Les six jours

> 💡 **En bref** : Six jours, un objectif par jour, et une carte verte qui dit simplement « ce jour est fini ».

Le code du parcours existe déjà et il est couvert par les tests ; les six jours servent à
**choisir le modèle sur des mesures, mettre en production, ancrer sur un corpus technique et
mesurer le prompt**. Une rangée de cartes par jour : les tâches, puis la carte verte 🏁 qui dit quand le jour est
fini. Les jours sont alignés sur les sprints de la série.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 200, "nodeSpacing": 18, "rankSpacing": 30}}}%%
flowchart TB
  subgraph s2["🏗️ SPRINT 2 — Socle et chaîne"]
    direction TB
    subgraph j1["Jour 1 — Choisir le modèle"]
      direction LR
      j1a("📝 Jeu de test initial<br/>écrit à la main")
      j1b("📏 Banc d'évaluation :<br/>qualité, latence, coût")
      j1c("⚖️ Mesure des modèles<br/>candidats")
      j1d("🏁 Modèle retenu,<br/>chiffres à l'appui")
      j1a ~~~ j1b ~~~ j1c ~~~ j1d
    end
    subgraph j2["Jour 2 — Tout est livré par la chaîne"]
      direction LR
      j2a("🗂️ Dépôt distant, projet GCP,<br/>PostgreSQL + pgvector")
      j2b("🔌 Client du modèle<br/>configurable")
      j2c("⚙️ Tests bloquants, image,<br/>recette puis production")
      j2d("🏁 Commit cassé bloqué,<br/>retour arrière réussi")
      j2a ~~~ j2b ~~~ j2c ~~~ j2d
    end
    j1 --> j2
  end

  subgraph s3["📚 SPRINT 3 — Données et ancrage"]
    direction TB
    subgraph j3["Jour 3 — Le corpus technique existe"]
      direction LR
      j3a("🌐 Collecte : fiches<br/>fabricants, docs métier")
      j3b("✂️ Nettoyage, passages,<br/>source et date")
      j3c("🗄️ Vecteurs dans pgvector,<br/>ingestion en 1 commande")
      j3e("🧠 Mémoire courte :<br/>30 derniers tours en base")
      j3d("🏁 L'index se reconstruit<br/>en une commande")
      j3a ~~~ j3b ~~~ j3c ~~~ j3e ~~~ j3d
    end
    subgraph j4["Jour 4 — Sources citées, prix résolus"]
      direction LR
      j4a("🔎 Recherche avant<br/>chaque appel au modèle")
      j4b("💶 Prix : catalogue<br/>ou saisie de l'artisan")
      j4c("🙅 Refus sous le seuil<br/>de pertinence")
      j4d("🏁 Questions de démo<br/>passées, hors corpus refusé")
      j4a ~~~ j4b ~~~ j4c ~~~ j4d
    end
    j3 --> j4
  end

  subgraph s45["📏 SPRINTS 4 et 5 — Fiabilité et démonstration"]
    direction TB
    subgraph j5["Jour 5 — Prompt mesuré, correction à la voix"]
      direction LR
      j5a("🧾 Sortie contrainte,<br/>prompt versionné")
      j5b("🚦 Évaluation bloquante,<br/>traces et scores dans Langfuse")
      j5c("👤 Comptes artisans,<br/>projets isolés")
      j5d("🏁 Chaque prompt a son score ;<br/>un artisan ne voit que ses projets")
      j5a ~~~ j5b ~~~ j5c ~~~ j5d
    end
    subgraph j6["Jour 6 — Le parcours tourne en production"]
      direction LR
      j6a("🖱️ Devis copilote :<br/>boutons et « Générer »")
      j6b("🇪🇺 Régions et journaux<br/>conformes RGPD")
      j6c("✅ Six critères du<br/>contrat démontrés")
      j6d("🏁 Parcours complet, quatre<br/>corps de métier, en production")
      j6a ~~~ j6b ~~~ j6c ~~~ j6d
    end
    j5 --> j6
  end

  v1["🎯 <b>V1 livrée</b> — dictée → devis pré-rempli, édité, chiffré, sourcé, exporté"]

  s2 --> s3 --> s45 --> v1

  classDef carte fill:#ffffff,stroke:#1168bd,color:#0b2e52
  classDef fin fill:#e7f6ec,stroke:#15803d,color:#0f5132
  classDef livre fill:#1168bd,stroke:#0b4884,color:#ffffff
  class j1a,j1b,j1c,j2a,j2b,j2c,j3a,j3b,j3c,j3e,j4a,j4b,j4c,j5a,j5b,j5c,j6a,j6b,j6c carte
  class j1d,j2d,j3d,j4d,j5d,j6d fin
  class v1 livre
```

### B. Améliorer le modèle sans l'entraîner

> 💡 **En bref** : Plutôt que de réentraîner le modèle, ce qui coûte cher, on améliore ses consignes et on mesure chaque amélioration.

Sortie contrainte au schéma, prompt versionné et
évalué sur un jeu de test écrit à la main. Le fine-tuning est une V2 potentielle, engagée
seulement si l'évaluation montre que le prompt plafonne.

## 3. Ce que la V1 ne fera pas

> 🧭 Ce qu'on ne fait pas compte autant que ce qu'on fait : c'est ce qui rend les six jours tenables.

Quatre cercles, du plus proche au plus lointain : la **V1.1**, déjà conçue et livrée juste après
les six jours ; ce qui viendra en V2 si une mesure le justifie ; puis deux familles de pistes —
faire évoluer le produit, l'étendre au-delà du devis.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 200, "nodeSpacing": 18, "rankSpacing": 35}}}%%
flowchart TB
  v1["🎯 <b>La V1</b> — dictée → devis pré-rempli, édité, chiffré, sourcé, exporté"]

  subgraph v11["🔜 A. V1.1 — juste après la V1, déjà conçu"]
    direction LR
    mlong("🧠 <b>Mémoire longue</b><br/>fiche des préférences<br/>et LLM juge (§6.C.5)")
    voix("🎙️ <b>Correction à la voix</b><br/>gabarit hiérarchique (§6.C.3)<br/>en V1 : édition au clic")
    prix2("💶 <b>Prix habituels et<br/>prix documentaires</b> (§6.C.2)")
    canary("🐤 <b>Déploiement progressif</b><br/>en V1 : bascule et<br/>retour arrière")
    azure("☁️ <b>Embeddings sur Azure</b><br/>en V1 : un seul cloud,<br/>GCP")
    mlong ~~~ voix ~~~ prix2 ~~~ canary ~~~ azure
  end

  subgraph v2["⏭️ B. REPORTÉ EN V2 POTENTIELLE — engagé seulement si une mesure le justifie"]
    direction LR
    ft("🧠 <b>Fine-tuning</b><br/>si l'évaluation montre<br/>que le prompt plafonne")
    seg("🎧 <b>Segmentation de la voix</b><br/>si d'autres voix polluent la dictée<br/>⚠️ sans empreinte vocale (RGPD)")
    stt("🎙️ <b>Transcription côté serveur</b><br/>en V1 : reconnaissance du<br/>navigateur, avec accord")
    big("🐘 <b>Modèle gpt-oss-120b</b><br/>si le benchmark montre qu'un<br/>modèle moyen ne suffit pas")
    ft ~~~ seg ~~~ stt ~~~ big
  end

  subgraph hv1["🧭 C. PISTES D'ÉVOLUTION DU PRODUIT — après la V1"]
    direction LR
    cli("👤 <b>Compte client final</b><br/>il reçoit le devis,<br/>il n'utilise pas l'outil")
    mob("📱 <b>Application mobile</b><br/>web uniquement ;<br/>choix web ou mobile à étudier")
    cli ~~~ mob
  end

  subgraph hp["💡 D. PISTES D'EXTENSION AU-DELÀ DU DEVIS — à explorer"]
    direction LR
    fac("🧾 <b>Facture, signature,<br/>relances client</b><br/>le produit s'arrête au devis")
    diag("🔍 <b>Diagnostic de pathologie<br/>du bâtiment</b><br/>engage une responsabilité d'expert")
    mo("⏱️ <b>Estimation de<br/>main d'œuvre</b><br/>savoir propre à chaque artisan")
    fac ~~~ diag ~~~ mo
  end

  v1 ~~~ v11 ~~~ v2 ~~~ hv1 ~~~ hp

  classDef v1c fill:#1168bd,stroke:#0b4884,color:#ffffff
  classDef plus_tard fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef hors_v1 fill:#f2f2f2,stroke:#6b6b6b,color:#333333
  classDef jamais fill:#fdecea,stroke:#b91c1c,color:#7a1010
  class v1 v1c
  class ft,seg,stt,big plus_tard
  class mlong,voix,prix2,canary,azure bientot
  classDef bientot fill:#e7f6ec,stroke:#15803d,color:#0f5132
  class cli,mob hors_v1
  class fac,diag,mo jamais
```

**Réserve sur la segmentation de la voix** : reconnaître l'artisan par son empreinte vocale est une
donnée biométrique (RGPD, article 9) ; une séparation des voix sans identification est à
privilégier.

## 4. La composante agentique

> 🧭 Le cœur intelligent du produit : comment l'agent réfléchit, et quand il rend la main à l'artisan.

### A. La composante retenue

> 💡 **En bref** : Un « workflow » : l'agent suit un chemin balisé, étape par étape, au lieu d'improviser ; l'artisan intervient aux moments clés.

Un **workflow agentique orchestré, avec humain dans la boucle** (HITL, *human in the loop*).
*À valider : son intitulé exact dans le menu du dispositif.*

### B. Ce que fait l'agent

> 💡 **En bref** : À chaque message, l'agent comprend, cherche dans sa documentation, propose, puis vérifie sa propre réponse avant de la montrer.

L'agent prend la dictée telle quelle, en reformule lui-même l'intention et le message, découpe le
chantier en **lots** — un par corps de métier — puis **itère sur chaque lot** autant que
nécessaire : il s'ancre sur le corpus, interroge le modèle, contrôle la réponse, pose les
questions qui manquent et pré-remplit le lot en suggestions grisées, que l'artisan accepte,
modifie, supprime ou complète. Puis il
passe au lot suivant.

Trois règles :

- **L'outil est un copilote, et il est ouvert.** L'agent pré-remplit, l'artisan édite. Un
  ouvrage absent du référentiel n'est pas rejeté : l'agent en fait une **proposition générique
  grisée**, que l'artisan modifie ou affine avec un produit référencé. Toute demande qui relève d'un devis est acceptée, même hors des quatre corps de
  métier pilotes.
- **La session ne s'arrête jamais sur un échec.** L'agent dit ce qu'il n'a pas compris et
  redemande ; l'échec est compté dans `/metriques`, sans interrompre l'artisan.
- **Les questions vérifient ou confirment ce que l'agent a produit**, jamais le point de départ.

**Vocabulaire.** Un **lot** est un corps de métier du devis (peinture, sols…). Un **ouvrage** est
une prestation élémentaire, par exemple « peinture de finition, 2 couches, au m² » ; le
référentiel en connaît les rendements, la chute et les consommables. Une **ligne** est un ouvrage
posé dans le devis, avec sa quantité.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 300}}}%%
flowchart TB
  dictee["🗣️ <b>L'artisan dicte</b><br/>une demande, une réponse ou une correction"]
  reform["🔄 <b>Reformulation automatique</b><br/>intention et message remis au propre<br/>un nombre ou une unité modifié : texte dicté gardé"]
  garde{"🛡️ <b>Garde-fous d'entrée</b><br/>injection de consigne ?<br/>demande sans rapport avec un devis ?"}
  recadre["💬 L'agent l'explique<br/>et ramène au devis"]
  lots["🧭 <b>Découpage en lots</b><br/>un lot par corps de métier :<br/>peinture, sols, plomberie, électricité, autre"]

  subgraph boucle["🔁 BOUCLE D'UN LOT — autant de tours que nécessaire"]
    direction TB
    mem["🧠 <b>Charge la mémoire</b> (§6.C.5)<br/>30 derniers tours · fiche des préférences<br/>métadonnées et commentaires du projet"]
    rag["📚 <b>Recherche dans le corpus</b> pour ce lot<br/>passages sourcés ; si rien de pertinent,<br/>l'agent continue et marque « non sourcé »"]
    llm["🤖 <b>Appel au modèle</b><br/>prompt versionné, passages, état du lot<br/>sortie contrainte au schéma"]
    subgraph verif["✅ Contrôle par le code"]
      direction TB
      v1["<b>1. Le format</b><br/>JSON conforme au schéma ?<br/>sinon : une reprise ; au 2e échec, l'agent dit<br/>ce qu'il n'a pas compris et redemande"]
      v2["<b>2. Les ouvrages</b><br/>connu du référentiel : rendement, chute,<br/>consommables appliqués<br/>inconnu : <b>proposition générique grisée</b>,<br/>modifiable par l'artisan"]
      v3["<b>3. Les quantités</b><br/>dans les bornes : acceptées<br/>hors bornes : l'artisan confirme ou corrige"]
      v1 --> v2 --> v3
    end
    manque{"❓ Manque-t-il<br/>une information ?"}
    question["❓ Question ciblée à l'artisan<br/>ex. « Hauteur sous plafond du salon ? »"]
    propose["✨ <b>L'agent pré-remplit le lot</b><br/>ouvrages, quantités, consommables<br/>en suggestions grisées — sans prix"]
    artisan{"👷 <b>L'artisan édite</b>"}
    mem --> rag
    rag --> llm --> v1
    v3 --> manque
    manque -- "oui" --> question
    manque -- "non" --> propose --> artisan
  end

  affine["✍️ Accepte, modifie, supprime ou ajoute un bloc<br/>affine un générique avec un produit référencé<br/>📝 chaque modification est journalisée"]
  suivant{"Reste-t-il<br/>un lot ?"}
  chiffrage["⚙️ <b>Générer</b><br/>complète les vides, résout les prix,<br/>calcule conditionnements, TVA, totaux"]
  metriques["📊 Tout échec est compté dans /metriques,<br/>sans jamais arrêter la session"]

  dictee --> reform --> garde
  garde -- "oui" --> recadre
  recadre -. "nouvelle dictée" .-> dictee
  garde -- "non" --> lots --> mem
  question -. "réponse dictée" .-> dictee
  artisan -- "modifie" --> affine
  affine -. "nouveau tour du lot" .-> mem
  artisan -- "passe au lot suivant" --> suivant
  suivant -- "oui, lot suivant" --> mem
  suivant -- "non : bouton « Générer »" --> chiffrage
  v1 -.-> metriques

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef decision fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef doux fill:#f2f2f2,stroke:#6b6b6b,color:#333333
  classDef cle fill:#1168bd,stroke:#0b4884,color:#ffffff
  class dictee,reform,lots,mem,rag,llm,v1,v2,v3,question,propose,affine etape
  class garde,manque,suivant decision
  class recadre,metriques doux
  class artisan,chiffrage cle
```

### C. Pourquoi cette composante sert ce besoin

Le devis engage la responsabilité de l'artisan :
la fiabilité compte plus que l'autonomie. Un agent qui appellerait librement des outils de
calcul ferait du modèle l'auteur des montants, ce que le principe du projet interdit. Le besoin
est un parcours séquentiel avec des validations, pas une exploration ouverte : un workflow
contrôlé y répond mieux qu'un agent autonome ou plusieurs agents.

## 5. La stack

> 🧭 Les briques techniques choisies pour construire tout cela, et pourquoi celles-là.

### A. Les choix

> 💡 **En bref** : Chaque ligne dit quel outil on prend et pourquoi ; tout tourne chez Google Cloud, en Europe.

| Couche | Choix | Pourquoi |
|---|---|---|
| Langage, environnement | Python 3.14, uv | Environnement reproductible depuis `uv.lock` |
| API | FastAPI, Pydantic | Contrat OpenAPI typé, erreurs déclarées |
| Interface | Une page HTML sans compilation | Aucune étape de build |
| Modèle | **Choisi au jour 1 par le benchmark** (§6.C.1). Référence : `gpt-oss-20b`, auto-hébergé par Ollama sur un service Cloud Run privé avec GPU L4 | Le choix se fait sur la qualité, la latence et le coût mesurés, données en Europe exigées |
| Hébergement | Cloud Run, région `europe-west1`, plusieurs instances : l'état vit dans PostgreSQL | Pas de serveur à administrer ; retour arrière natif par révision ; GPU payé à la seconde d'activité |
| Images, secrets | Artifact Registry, Secret Manager | Les clés et secrets d'authentification restent hors du dépôt |
| Authentification | **Un compte par artisan**, mode d'identification à choisir ; chaque requête ne voit que les projets de l'artisan connecté | Plusieurs artisans en même temps : l'isolation des données se vérifie à chaque accès, pas seulement à l'écran |
| Base de données | **PostgreSQL avec pgvector, une seule base** (Cloud SQL, `europe-west1`) : catalogue, ouvrages, projets, devis, profil, corpus et ses vecteurs | Une base pour le relationnel et la recherche vectorielle : jointures entre un passage, sa source et un ouvrage ; plus de fichiers sur un disque que Cloud Run efface |
| Corpus et recherche (RAG) | Vecteurs dans pgvector ; **modèle d'embeddings multilingue servi sur GCP**, région UE (Vertex AI, modèle précis à confirmer). Azure AI Foundry en V1.1 | Un seul cloud en V1 : un seul contrat de sous-traitance, une seule région à tenir |
| Mémoire | Même base PostgreSQL + pgvector que le RAG : en V1, **mémoire courte de 30 tours** ; la mémoire longue (fiche des préférences, LLM juge) arrive en V1.1 | Le contexte de la conversation sans un second appel au modèle |
| Prompts | Fichiers versionnés dans le dépôt, publiés dans Langfuse, chacun avec son rapport d'évaluation | Une version de prompt se compare, se livre et se retire comme du code |
| Observabilité | **Langfuse** pour le modèle : traces de chaque tour, version de prompt, latence, coût, scores d'évaluation ; Cloud Logging pour l'infrastructure | Relier chaque comportement observé à la version de prompt et au modèle qui l'ont produit |
| Export | `python-docx` | Le format que l'artisan sait modifier |
| Chaîne | GitHub Actions, authentifié auprès de GCP sans clé stockée (fédération d'identité) | Aucun secret longue durée dans GitHub |

### B. L'élément exotique

> 💡 **En bref** : La formation n'autorise qu'une technologie hors du socle commun ; ici, héberger soi-même le modèle, et seulement si le benchmark le retient.

Il dépend du benchmark. Si le modèle retenu est auto-hébergé sur GPU, c'est
l'unique dérogation au socle ; s'il est servi par une API européenne, la stack n'en a aucune.

## 6. Les schémas

> 🧭 Comment ces briques s'assemblent (A), comment le code arrive en production sans rien casser (B), et les mécanismes qui font la valeur du produit (C).

### A. Architecture — modèle C4

> 💡 **En bref** : Trois zooms successifs sur la même application, comme une carte : le pays, la ville, puis le quartier.

Les schémas suivent le **modèle C4** : on zoome par niveaux, du système vu de l'extérieur jusqu'à
ses composants. Le déroulé dans le temps est porté par la boucle de l'agent (§4.B).

**Légende commune.** Chaque boîte donne son nom, son type C4 et sa technologie entre crochets.
Chaque flèche porte ce qui circule et son protocole. **[DP]** marque ce qui manipule des données
personnelles. Une boîte à **bord pointillé** est une cible de la V1 pas encore présente dans le
code ; son libellé le dit aussi : **(à faire)**. Tout ce qui est dans GCP tourne en région
`europe-west1`.

#### Niveau 1 — Contexte

> 💡 **En bref** : Qui utilise le système, et avec quels services extérieurs il échange.

Le système, la seule personne qui l'utilise, et les systèmes extérieurs dont il dépend. Les
flèches sont numérotées dans l'ordre du parcours ; chaque système externe dit ce qu'il reçoit,
ce qu'il rend, à quelle fréquence, et **ce que fait le produit s'il est en panne**. Le client
final ne touche pas le système : il reçoit le devis exporté, envoyé par l'artisan.

```mermaid
flowchart TB
  artisan["<b>Artisans</b><br/>[Personnes — plusieurs, chacun ses projets]<br/>Sur le chantier : dicte mesures et travaux<br/>Au bureau : répond, valide, corrige, exporte<br/>Fait autorité sur chaque ligne du devis"]

  stt["<b>Reconnaissance vocale du navigateur</b><br/>[Système externe — éditeur du navigateur]<br/>Transcrit la voix en texte<br/>Sur l'appareil si possible, sinon chez l'éditeur<br/>après accord explicite de l'artisan<br/><i>En panne : saisie au clavier</i>"]

  app["<b>Assistant de devis BTP</b><br/>[Système — notre périmètre, GCP europe-west1]<br/>Dictée reformulée → questions manquantes → structure<br/>sans prix → devis chiffré et sourcé → export Word<br/>Le modèle décrit, le code calcule"]

  subgraph externes["Services appelés pendant l'utilisation"]
    direction TB
    annuaire["<b>Annuaire des entreprises</b><br/>[Système externe — API publique]<br/>Reçoit : le SIRET seul<br/>Rend : raison sociale, adresse, RCS, APE, TVA<br/>Une fois, à la création du profil<br/><i>En panne : saisie manuelle, compte créé quand même</i>"]
    ocr["<b>Service d'OCR</b><br/>[Système externe — facultatif]<br/>Reçoit : un ancien devis, image ou PDF [DP]<br/>Rend : sa mise en page en Markdown<br/>Une fois, si l'artisan dépose un modèle<br/><i>En panne : gabarit par défaut</i>"]
  end

  subgraph ingestion["Sources lues à la construction de l'image"]
    direction TB
    sources["<b>Sources du corpus technique</b><br/>[Systèmes externes]<br/>Fiches fabricants, documentation métier,<br/>API ADEME, pages de référence<br/>Collecte ponctuelle ou par scraping<br/>Licence vérifiée source par source"]
  end

  client["<b>Client final</b><br/>[Personne externe — non utilisateur]<br/>Aucun compte, aucun écran<br/>Nom et adresse du chantier saisis par l'artisan [DP]<br/>Reçoit le devis Word, hors système"]

  artisan <-- "① Voix [DP] → ← texte dicté<br/>dans le navigateur" --> stt
  artisan <-- "② Dictée, réponses, validations →<br/>← questions, devis, fichier Word<br/>HTTPS, compte de l'artisan puis jeton" --> app
  app -. "⓪ À la construction de l'image :<br/>collecte et indexation des passages,<br/>jamais pendant l'utilisation" .-> sources
  app -- "③ SIRET seul<br/>HTTPS" --> annuaire
  app -- "④ Ancien devis, facultatif [DP]<br/>HTTPS" --> ocr
  artisan -. "⑤ Envoie le devis<br/>courriel, hors système" .-> client

  classDef personne fill:#08427b,stroke:#052e56,color:#ffffff
  classDef systeme fill:#1168bd,stroke:#0b4884,color:#ffffff
  classDef externe fill:#8a8a8a,stroke:#6b6b6b,color:#ffffff
  class artisan,client personne
  class app systeme
  class stt,annuaire,ocr,sources externe
```

#### Niveau 2 — Conteneurs

> 💡 **En bref** : Les grandes pièces qui tournent en production, et comment elles se parlent.

Les unités déployées, leurs magasins de données et leurs protocoles. Deux frontières de
confiance : l'API n'est joignable qu'avec le jeton de session d'un artisan, qui ne voit que ses
propres projets ; le
service de modèle n'est joignable que par l'identité de service de l'API.

```mermaid
flowchart TB
  artisan["<b>Artisan</b><br/>[Personne]<br/>Navigateur web"]

  subgraph gcp["Projet GCP — europe-west1"]
    subgraph run_app["Cloud Run « application » — public, un compte par artisan, plusieurs instances"]
      ui["<b>Interface web</b><br/>[Conteneur : HTML et JavaScript]<br/>Dictée, questions, validation, export"]
      api["<b>API et agent</b><br/>[Conteneur : Python 3.14, FastAPI]<br/>Garde-fous, recherche, mémoire, orchestration,<br/>calcul du devis, export Word [DP]"]
    end
    subgraph run_llm["Service de modèle — retenu au benchmark"]
      llm["<b>Service de modèle</b><br/>[Cloud Run GPU privé, ou API européenne]<br/>(à faire)<br/>Reformulation, JSON contraint, LLM juge"]
    end
    db[("<b>Base de données</b><br/>[PostgreSQL + pgvector, Cloud SQL] (à faire)<br/>Catalogue, ouvrages, projets, devis, profil [DP]<br/>Mémoire courte et fiches des préférences [DP]<br/>Corpus et vecteurs")]
    logs["<b>Journaux d'infrastructure</b><br/>[Cloud Logging]"]
    sec["<b>Secrets</b><br/>[Secret Manager]"]
  end
  annuaire["<b>Annuaire des entreprises</b><br/>[Système externe]"]
  langfuse["<b>Langfuse</b><br/>[Observabilité du modèle, UE] (à faire)<br/>Traces, prompts, coûts, scores<br/>données personnelles masquées"]
  azure["<b>Modèle d'embeddings</b><br/>[Vertex AI, europe-west1 — à confirmer]<br/>(à faire) ; Azure en V1.1"]

  artisan -- "HTTPS" --> ui
  ui -- "JSON, jeton de session, HTTPS" --> api
  api -- "SQL et recherche vectorielle<br/>connecteur Cloud SQL" --> db
  api -- "Prompt versionné, passages<br/>HTTPS, identité de service" --> llm
  api -- "Événements<br/>sans dictée" --> logs
  api -- "Traces des tours<br/>HTTPS" --> langfuse
  api -- "Au<br/>démarrage" --> sec
  api -- "SIRET seul<br/>HTTPS" --> annuaire
  api -- "Textes à vectoriser<br/>HTTPS" --> azure
  logs ~~~ langfuse
  sec ~~~ annuaire
  db ~~~ azure

  classDef personne fill:#08427b,stroke:#052e56,color:#ffffff
  classDef conteneur fill:#438dd5,stroke:#2e6295,color:#ffffff
  classDef externe fill:#8a8a8a,stroke:#6b6b6b,color:#ffffff
  classDef afaire fill:#438dd5,stroke:#0b2e52,stroke-width:2px,stroke-dasharray:6 4,color:#ffffff
  class artisan personne
  class ui,api,logs,sec conteneur
  class llm,db afaire
  class annuaire externe
  class langfuse,azure afaireext
  classDef afaireext fill:#8a8a8a,stroke:#0b2e52,stroke-width:2px,stroke-dasharray:6 4,color:#ffffff
```

#### Niveau 3 — Composants de l'API

> 💡 **En bref** : À l'intérieur de l'application : quel fichier de code fait quoi.

Où vit chaque responsabilité dans le conteneur « API et agent ». Le point clé : **le modèle n'est
appelé qu'entre deux couches de code**, une qui prépare, une qui contrôle et calcule. Le
comportement pas à pas est au §4.B.

```mermaid
flowchart TB
  ui["<b>Interface web</b> [conteneur]"]
  auth["<b>Authentification</b> — middleware"]

  subgraph avant["Avant le modèle"]
    direction LR
    reform["Reformulation<br/>app/transcription.py"]
    garde["Garde-fous<br/>app/garde_fous.py"]
    rag["Recherche RAG<br/>(à faire)"]
    mem["Mémoire<br/>(à faire)"]
    prompt["Prompts versionnés<br/>(à faire)"]
  end

  client["<b>Client du modèle</b> — app/llm.py"]
  llm["<b>Service de modèle</b> [conteneur]"]

  subgraph apres["Après le modèle"]
    direction LR
    ctrl["Contrôle et routage<br/>app/pipeline.py, app/schema.py"]
    devis["Moteur de devis<br/>app/devis.py, app/catalogue.py"]
    export["Export Word<br/>app/export.py"]
  end

  obs["<b>Observabilité et signal qualité</b> — SDK Langfuse, app/boucle_qualite.py"]

  ui --> auth --> avant --> client
  client <--> llm
  client --> apres
  apres -.-> obs

  classDef conteneur fill:#438dd5,stroke:#2e6295,color:#ffffff
  classDef composant fill:#85bbf0,stroke:#5d82a8,color:#000000
  classDef afaire fill:#85bbf0,stroke:#0b2e52,stroke-width:2px,stroke-dasharray:6 4,color:#000000
  class ui,llm conteneur
  class auth,reform,garde,client,ctrl,devis,export,obs composant
  class rag,mem,prompt afaire
```

### B. Pilotage : stratégie Git, chaînes, environnements, signaux

> 💡 **En bref** : Comment une modification passe de mon poste à la production sans rien casser, et comment on revient en arrière si besoin.

#### La stratégie : GitHub Flow, avec des versions étiquetées

> 💡 **En bref** : Chaque changement se fait sur une branche à part, puis rejoint la branche principale après vérification ; une étiquette de version marque ce qui part en production.

`main` est toujours livrable. Tout changement part d'une **branche courte** et revient par une
**pull request** ; une version de production est une **étiquette** posée sur `main`.

| Règle | Détail |
|---|---|
| `main` protégée | Aucun push direct ; fusion seulement par pull request, contrôles verts exigés ; historique linéaire (fusion par squash) |
| Branches courtes | Durée de vie de quelques jours au plus, nommées par leur nature : `feat/US-xx-…`, `fix/…`, `prompt/…`, `docs/…`, `hotfix/…` |
| Branche `prompt/…` | Une nouvelle version de prompt est une branche à part entière : elle déclenche l'évaluation sur le vrai modèle |
| Versions | Étiquettes `vX.Y.Z` sur `main` : majeur si le contrat de l'API change, mineur pour une fonctionnalité, correctif pour un défaut |
| Correctif urgent | Branche `hotfix/…` depuis `main`, mêmes contrôles, puis étiquette de correctif |
| Une décision, un commit | Une décision de conception s'écrit dans `docs/DECISIONS.md` dans le même commit que le code qu'elle change |

Le graphe suivant montre un cycle complet : une fonctionnalité et une nouvelle version de prompt
développées en parallèle, une version mineure, puis un correctif.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 240}}}%%
flowchart TB
  subgraph main["main — protégée, toujours livrable"]
    direction TB
    m0["🏷️ v1.0.0"]
    m1["🔀 PR #12 fusionnée<br/>tests verts"]
    m2["🔀 PR #13 fusionnée<br/>score ≥ prompt v3"]
    m3["🏷️ v1.1.0<br/>version mineure"]
    m4["🔀 PR #14 fusionnée<br/>correctif"]
    m5["🏷️ v1.1.1<br/>version de correctif"]
    m0 --> m1 --> m2 --> m3 --> m4 --> m5
  end

  subgraph feat["feat/US-31-generer"]
    direction TB
    f1["bouton Générer"] --> f2["tests du chiffrage"]
  end
  subgraph prompt["prompt/devis-v4"]
    direction TB
    p1["prompt devis v4"]
  end
  subgraph hotfix["hotfix/export-tva"]
    direction TB
    h1["corrige la TVA à l'export"]
  end

  m0 -. "branche" .-> f1
  m0 -. "branche" .-> p1
  f2 -- "pull request" --> m1
  p1 -- "pull request + évaluation" --> m2
  m3 -. "branche" .-> h1
  h1 -- "pull request" --> m4

  classDef tag fill:#1168bd,stroke:#0b4884,color:#ffffff
  classDef fusion fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef br fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  class m0,m3,m5 tag
  class m1,m2,m4 fusion
  class f1,f2,p1,h1 br
```

#### Deux chemins vers la production

> 💡 **En bref** : Le code et les données n'évoluent ni au même rythme ni avec les mêmes risques : chacun a son chemin et ses propres contrôles. Le premier chemin sépare aussi « vérifier vite et gratuitement », avant de fusionner, de « mesurer la qualité du modèle, lentement et en payant », avant la production.

**Chemin 1 — code et prompt.** Deux portes distinctes : la fusion dans `main` n'exige que des
contrôles rapides, gratuits et déterministes ; l'évaluation sur le vrai modèle, lente et payante,
ne bloque que la **promotion** en production. Pour limiter le coût, elle ne tourne que si ce
qu'elle mesure a changé, et commence par une évaluation éclair qui arrête tout au premier échec.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 380, "subGraphTitleMargin": {"top": 8, "bottom": 22}}}}%%
flowchart TB
  dev["👩‍💻 Branche courte : code et/ou prompt"]

  subgraph vers_main["① VERS MAIN — rapide, gratuit, déterministe : bloque la fusion"]
    direction TB
    ci["🧪 Tests avec faux modèle · réponses enregistrées rejouées<br/>garde-fous et injections · image construite et éprouvée"]
    ok1{"Tout est vert ?"}
    ci --> ok1
  end

  subgraph candidat["② CANDIDAT — après la fusion, rien n'est encore en production"]
    direction TB
    pub["📦 Image unique étiquetée par le SHA<br/>📝 prompt publié dans Langfuse, étiquette « candidat »"]
    rec["🧪 Déployé en recette"]
    pub --> rec
  end

  subgraph vers_prod["③ VERS LA PRODUCTION — lent, payant, statistique : bloque la promotion"]
    direction TB
    change{"Le prompt, le schéma<br/>ou le modèle a changé ?"}
    echant["⚡ Évaluation éclair : ~20 cas sur le vrai modèle"]
    complet["📏 Évaluation complète : tout le jeu de test<br/>seuils absolus en V1, puis « pas moins bien que la production »"]
    ok2{"Seuils atteints ?"}
    promo["🚀 Promotion : étiquette vX.Y.Z et étiquette Langfuse « production »<br/>approbation, puis bascule ; progressif en V1.1"]
    change -- "oui" --> echant
    echant -- "réussie" --> complet --> ok2
    change -- "non : rien à mesurer" --> promo
    ok2 -- "oui" --> promo
  end

  stop1["⛔ Fusion refusée"]
  stop2["⏸️ Le candidat reste en recette<br/>la production ne bouge pas"]
  retour["↩️ Retour arrière : révision Cloud Run<br/>ou étiquette Langfuse précédente"]

  dev --> ci
  ok1 -- "non" --> stop1
  ok1 -- "oui : fusion" --> pub
  rec --> change
  echant -- "échouée : on s'arrête là, coût minimal" --> stop2
  ok2 -- "non" --> stop2
  promo -. "signaux dégradés" .-> retour

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef decision fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef stop fill:#fdecea,stroke:#b91c1c,color:#7a1010
  classDef cle fill:#1168bd,stroke:#0b4884,color:#ffffff
  class dev,ci,pub,rec,echant,complet etape
  class ok1,change,ok2 decision
  class stop1,stop2,retour stop
  class promo cle
```

**Chemin 2 — données et pipeline.** Une nouvelle version du corpus s'écrit à côté de l'active,
est évaluée sur des questions de référence, et ne la remplace que si elle fait au moins aussi
bien. L'ancienne version reste en base pour un retour arrière immédiat.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 380, "subGraphTitleMargin": {"top": 8, "bottom": 22}}}}%%
flowchart TB
  src["🌐 Nouvelle source, ou mise à jour d'une source<br/>fiches fabricants, documentation métier, catalogue"]

  subgraph ingest["① INGESTION — rejouable en une commande"]
    direction TB
    col["Collecte · licence vérifiée · date de collecte"]
    net["Nettoyage · découpage en passages · métadonnées de source<br/>données personnelles retirées"]
    qual{"Contrôles de données<br/>schéma, doublons, rejets comptés avec leur motif"}
    col --> net --> qual
  end

  subgraph version["② NOUVELLE VERSION DU CORPUS — à côté de l'active, sans la toucher"]
    direction TB
    vec["🗄️ Passages et vecteurs écrits dans PostgreSQL + pgvector<br/>sous un nouveau numéro de version"]
  end

  subgraph evalr["③ ÉVALUATION DE LA RECHERCHE — sur des questions de référence"]
    direction TB
    q["🔎 Le bon passage est-il retrouvé ? la citation est-elle juste ?<br/>les questions hors corpus sont-elles refusées ?"]
    ok{"Au moins aussi bon<br/>que la version active ?"}
    q --> ok
  end

  bascule["🔀 <b>Bascule</b> : la nouvelle version devient l'active"]
  garde["⏸️ L'active ne change pas ; rapport des écarts"]
  rejet["⛔ Rien n'est écrit ; rapport des rejets"]
  retour["↩️ Retour arrière : repointer vers la version précédente,<br/>conservée en base"]

  src --> col
  qual -- "non" --> rejet
  qual -- "oui" --> vec --> q
  ok -- "oui" --> bascule
  ok -- "non" --> garde
  bascule -. "si un problème apparaît" .-> retour

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef decision fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef stop fill:#fdecea,stroke:#b91c1c,color:#7a1010
  classDef cle fill:#1168bd,stroke:#0b4884,color:#ffffff
  class src,col,net,vec,q etape
  class qual,ok decision
  class garde,rejet,retour stop
  class bascule cle
```

#### Les environnements

> 💡 **En bref** : Trois copies de l'application : une pour essayer, une pour tester, une pour les vrais utilisateurs.

| Environnement | Déclencheur | Base de données | Langfuse | Trafic |
|---|---|---|---|---|
| Prévisualisation | Pull request | Base de recette | Environnement `preview` | Aucun : URL propre à la PR |
| Recette | Fusion sur `main` | Base de recette | Environnement `recette` | Testeurs |
| Production | Étiquette `vX.Y.Z` et approbation | Base de production | Environnement `production` | Artisans |

#### Pourquoi cette stratégie, et pas une autre

> 💡 **En bref** : Il existe plusieurs façons d'organiser ses branches ; celle-ci est la plus simple qui garde un contrôle avant chaque fusion.

| Stratégie | Ce qu'elle apporte | Pourquoi elle n'est pas retenue |
|---|---|---|
| GitFlow (`develop`, `release/…`, `hotfix/…`) | Des versions planifiées, plusieurs versions maintenues en parallèle | Lourde pour une seule personne et un seul produit déployé : deux branches longues à synchroniser, sans bénéfice |
| Trunk-based pur (push direct sur `main`) | La vitesse maximale | Plus de point de contrôle : ni relecture, ni évaluation bloquante avant `main` |
| **GitHub Flow + étiquettes** | Une branche longue, un contrôle par PR, des versions explicites | **Retenue** : la relecture et l'évaluation bloquent avant `main`, l'étiquette sépare « fusionné » de « en production » |

#### Les signaux

> 💡 **En bref** : Les indicateurs qui disent, après une mise en production, si tout va bien, et qui déclenchent un retour arrière sinon.

| Signal | Source | Seuil d'alerte | Effet |
|---|---|---|---|
| Taux d'erreurs serveur | Cloud Monitoring | Au-dessus du niveau de la version précédente | Retour arrière automatique après la bascule (déploiement progressif |
| Latence p95 d'un tour | Langfuse | Au-delà de 30 s | Retour arrière ; incident |
| Coût par devis | Langfuse | Au-delà du budget fixé au benchmark | Alerte |
| Scores d'évaluation | Langfuse | Sous le score de la version précédente | PR bloquée, ou retour arrière |
| Disponibilité | Sonde Cloud Monitoring | Deux échecs consécutifs | Alerte |

Les fichiers existants s'y raccordent : `tests.yml` devient la chaîne ①, `livraison.yml` est
étendu aux chaînes ② et ③, `modele.yml` porte l'évaluation sur le vrai modèle.

### C. Mécanismes clés

> 💡 **En bref** : Les cinq mécanismes qui font la différence pour l'artisan, chacun avec son schéma.

#### 1. Choisir le modèle : benchmark de qualité, latence et coût

> 💡 **En bref** : Avant de choisir un modèle, on le met à l'épreuve sur nos propres cas, en comparant qualité, rapidité et prix.

**Le modèle n'est pas fixé à ce stade.** Il est choisi au jour 1, sur le jeu de test initial, par
une règle écrite à l'avance : deux filtres éliminatoires, trois mesures, une règle de décision.
`gpt-oss-20b`, dont le taux de JSON conforme brut est connu (71,4 %), sert de référence.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 380}}}%%
flowchart TB
  cand["🧪 <b>Modèles candidats</b> (liste à confirmer)<br/>• gpt-oss-20b auto-hébergé : Ollama sur Cloud Run GPU, europe-west1<br/>• Un modèle Gemini servi par Vertex AI en région européenne<br/>• Un modèle Mistral, éditeur et hébergement européens<br/>• gpt-oss sur Azure AI Foundry, zone de données UE"]

  subgraph filtre["🚧 Filtres éliminatoires — oui ou non"]
    direction TB
    f1{"🇪🇺 Données traitées<br/>dans l'Union européenne ?"}
    f2{"🧾 Sortie contrainte<br/>par un schéma JSON ?"}
    f1 -- "oui" --> f2
  end
  ecarte["❌ Écarté, motif écrit"]

  subgraph mesure["📏 Mesures — même jeu de test, même prompt, même schéma"]
    direction TB
    q["✅ <b>Qualité</b><br/>JSON conforme, quantités justes,<br/>bon niveau de mention, ouvrages bien reconnus"]
    l["⏱️ <b>Latence</b><br/>p95 d'un tour, démarrage à froid compris<br/>seuil : moins de 30 s"]
    c["💶 <b>Coût</b><br/>par devis complet : jetons facturés,<br/>ou secondes de GPU pour l'auto-hébergé"]
    q --> l --> c
  end

  decision{"⚖️ <b>Règle de décision</b><br/>parmi les modèles qui passent les seuils<br/>de qualité et de latence, le moins cher"}
  retenu["🏆 <b>Modèle retenu</b><br/>rapport de benchmark versionné,<br/>référence pour toutes les versions de prompt"]
  aucun["🔁 Aucun ne passe :<br/>améliorer le prompt, puis remesurer ;<br/>en dernier recours, fine-tuning (V2)"]

  cand --> f1
  f1 -- "non" --> ecarte
  f2 -- "non" --> ecarte
  f2 -- "oui" --> q
  c --> decision
  decision -- "au moins un" --> retenu
  decision -- "aucun" --> aucun

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef decision fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef stop fill:#fdecea,stroke:#b91c1c,color:#7a1010
  classDef fin fill:#1168bd,stroke:#0b4884,color:#ffffff
  class cand,q,l,c,aucun etape
  class f1,f2,decision decision
  class ecarte stop
  class retenu fin
```

#### 2. D'où vient le prix

> 💡 **En bref** : Un prix vient toujours d'une source qu'on peut montrer, l'artisan ou le catalogue, jamais du modèle.

**Périmètre** : en V1, catalogue et saisie de l'artisan ; prix habituels et prix documentaires
en V1.1.

Le modèle ne produit **jamais** un prix. Chaque prix vient d'une source nommée, dans un ordre de
priorité fixe, et chaque ligne du devis affiche la sienne. **À valider : l'ordre de priorité
proposé.**

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 360}}}%%
flowchart TB
  ligne["⚙️ <b>Clic sur « Générer »</b>, pour chaque ligne sans prix<br/>ex. 1.1.2 — Peinture murs, 2 couches — 45 m²"]

  p1{"✍️ L'artisan a-t-il saisi<br/>un prix pour cette ligne ?<br/>(clavier ou voix)"}
  p2{"📒 Existe-t-il un prix habituel<br/>de l'artisan pour cet article ?"}
  p3{"🏷️ Le catalogue a-t-il<br/>un article correspondant ?"}
  p4{"📚 Un document du corpus<br/>donne-t-il un prix daté ?"}

  s1["✍️ <b>Prix de l'artisan</b><br/>source : saisie, avec la date"]
  s2["📒 <b>Prix habituel</b><br/>proposé, l'artisan le garde ou le change"]
  s3["🏷️ <b>Prix catalogue</b><br/>référence, conditionnement, date de mise à jour"]
  s4["📚 <b>Prix documentaire</b><br/>extrait par le code à l'ingestion, jamais par le modèle<br/>document cité, marqué « à confirmer »"]
  s5["⛔ <b>Prix à saisir</b><br/>la ligne est signalée ;<br/>l'export reste bloqué tant qu'elle n'a pas de prix"]

  cond["📦 <b>Conditionnement</b><br/>quantité d'achat = quantité technique avec chute,<br/>arrondie au conditionnement supérieur (pot de 10 L, paquet de 2,13 m²)<br/>inconnu : l'artisan le saisit, sinon vente à l'unité"]
  calc["🧮 <b>Calcul par le code</b><br/>prix HT de la ligne, TVA selon le taux qualifié,<br/>totaux, ventilation par taux, acompte"]
  affiche["📄 <b>Chaque ligne affiche sa source</b><br/>✍️ artisan · 📒 habituel · 🏷️ catalogue · 📚 document à confirmer"]
  memo["💾 Un prix saisi peut devenir<br/>un prix habituel, si l'artisan le demande"]

  ligne --> p1
  p1 -- "oui" --> s1
  p1 -- "non" --> p2
  p2 -- "oui" --> s2
  p2 -- "non" --> p3
  p3 -- "oui" --> s3
  p3 -- "non" --> p4
  p4 -- "oui" --> s4
  p4 -- "non" --> s5
  s1 & s2 & s3 & s4 --> cond
  cond --> calc --> affiche
  s1 -.-> memo

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef decision fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef stop fill:#fdecea,stroke:#b91c1c,color:#7a1010
  classDef fin fill:#1168bd,stroke:#0b4884,color:#ffffff
  class ligne,s1,s2,s3,s4,cond,calc,memo etape
  class p1,p2,p3,p4 decision
  class s5 stop
  class affiche fin
```

#### 3. Corriger à la voix : le gabarit hiérarchique — V1.1

> 💡 **En bref** : Chaque ligne du devis a un numéro ; l'artisan peut dire « ligne 1.1.2, 48 mètres carrés » et la bonne case change.

**Périmètre** : V1.1. En V1, la numérotation des lignes est affichée et l'artisan corrige au clic.

Pour corriger une case sans toucher à la souris, l'artisan doit pouvoir **la désigner à la
voix**. Le devis suit donc un gabarit à cinq niveaux, numérotés comme un devis BTP classique ;
ces numéros s'affichent à l'écran et dans l'export, et servent d'adresse.

| Niveau | Ce qu'il désigne | Exemple | Ce qu'on dit à la voix |
|---|---|---|---|
| 0 | Le devis | DEV-20261013-xxxx | — |
| 1 | Une pièce ou une zone | **1** Salon | « Salon » |
| 2 | Un lot, c'est-à-dire un corps de métier | **1.1** Peinture | « peinture » |
| 3 | Une ligne : un ouvrage et sa quantité | **1.1.2** Peinture murs, 2 couches | « ligne deux » |
| 4 | Une case de la ligne | quantité, unité, article, prix unitaire, TVA | « quarante-huit mètres carrés » |

Les numéros sont visibles sur l'écran du devis (§6.C.4).

Une correction dictée devient une **adresse** (pièce, lot, ligne, case) et une **valeur**. Le
modèle traduit la phrase ; le code vérifie l'adresse, relit la modification à l'artisan, puis
l'applique et recalcule.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 360}}}%%
flowchart TB
  voix["🎙️ <b>L'artisan parle</b><br/>« Salon, peinture, ligne deux : quarante-huit mètres carrés »"]
  texte["🔄 Reformulée par l'agent, sans relecture"]
  llm["🤖 <b>Le modèle traduit en adresse</b><br/>intention « correction »<br/>cible : 1.1.2 · case : quantité · valeur : 48 · unité : m²"]

  c1{"🧭 La cible existe-t-elle<br/>et une seule ?"}
  c2{"🔒 La case est-elle modifiable<br/>et la valeur plausible ?"}
  ambigu["❓ Question ciblée<br/>« Quelle ligne de peinture : 1.1.1 ou 1.1.2 ? »"]
  refus["🙅 Refus expliqué<br/>ex. un total ne se corrige pas : il se recalcule"]

  relit["🔊 <b>Le produit relit la modification</b><br/>« Ligne 1.1.2 — quantité : 45 → 48 m². Je confirme ? »"]
  ok{"👷 L'artisan confirme ?"}
  applique["🧮 <b>Le code applique et recalcule</b><br/>quantité d'achat, prix de la ligne, totaux"]
  journal["📝 Correction journalisée :<br/>avant, après, cible, motif — signal qualité"]
  annule["↩️ Rien n'est modifié"]

  voix --> texte --> llm --> c1
  c1 -- "non trouvée ou plusieurs" --> ambigu --> voix
  c1 -- "oui" --> c2
  c2 -- "non" --> refus
  c2 -- "oui" --> relit --> ok
  ok -- "oui" --> applique --> journal
  ok -- "non" --> annule

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef decision fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef stop fill:#fdecea,stroke:#b91c1c,color:#7a1010
  classDef cle fill:#1168bd,stroke:#0b4884,color:#ffffff
  class voix,texte,llm,ambigu,journal,annule etape
  class c1,c2,ok decision
  class refus stop
  class relit,applique cle
```

#### 4. Le devis copilote : l'agent pré-remplit, l'artisan édite, « Générer » complète

> 💡 **En bref** : L'écran fonctionne comme un traitement de texte avec suggestions : l'agent propose en gris, l'artisan accepte, modifie ou supprime.

L'écran du devis est un document éditable bloc par bloc. Chaque ligne affiche son état et ses
boutons ; la barre du haut porte les actions globales. Les numéros du gabarit (§6.C.3) sont
visibles : ils servent aussi d'adresse pour corriger à la voix.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 460, "nodeSpacing": 14, "rankSpacing": 18}}}%%
flowchart TB
  subgraph ecran["🖥️ ÉCRAN DU DEVIS — l'agent pré-remplit, l'artisan édite"]
    direction TB
    barre["🎙️ Dicter &nbsp;·&nbsp; ➕ Ajouter un lot &nbsp;·&nbsp; ⚙️ <b>Générer</b> &nbsp;·&nbsp; 📄 Exporter"]

    subgraph lot1["1.1 Peinture &nbsp;—&nbsp; ✅ tout accepter &nbsp;·&nbsp; 🗑️ supprimer le lot"]
      direction TB
      l1["<b>1.1.1</b> Préparation des supports — 42 m²<br/>✅ acceptée &nbsp;·&nbsp; ✏️ &nbsp;·&nbsp; 🗑️"]
      l2["<b>1.1.2</b> Peinture murs, 2 couches — 42 m²<br/>✨ suggestion de l'agent &nbsp;·&nbsp; ✅ &nbsp;·&nbsp; ✏️ &nbsp;·&nbsp; 🗑️"]
      l3["<b>1.1.3</b> Peinture plafond — quantité : <b>vide</b><br/>⬜ à compléter : « Générer » proposera une valeur"]
      l1 ~~~ l2 ~~~ l3
    end

    subgraph lot2["1.2 Sols"]
      direction TB
      l4["<b>1.2.1</b> Dépose de moquette — 18 m²<br/>✨ proposition générique, hors référentiel<br/>✏️ affiner avec un produit référencé &nbsp;·&nbsp; 🗑️"]
    end

    total["Total : <b>à générer</b> — aucun prix avant « Générer »"]
    barre ~~~ lot1 ~~~ lot2 ~~~ total
  end

  classDef barreC fill:#08427b,stroke:#052e56,color:#ffffff
  classDef acceptee fill:#ffffff,stroke:#15803d,stroke-width:2px,color:#0f5132
  classDef suggestion fill:#ececec,stroke:#8a8a8a,stroke-dasharray:5 4,color:#555555
  classDef vide fill:#fff7e6,stroke:#b7791f,stroke-dasharray:5 4,color:#5a3a00
  classDef totalC fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  class barre barreC
  class l1 acceptee
  class l2,l4 suggestion
  class l3 vide
  class total totalC
```

Chaque ligne passe par des états explicites. Une suggestion que l'artisan n'a pas revue peut être
chiffrée par « Générer », mais elle reste signalée et **bloque l'export** tant qu'il ne l'a pas
acceptée : l'agent propose, l'artisan décide.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 260}}}%%
flowchart TB
  agent["✨ L'agent pré-remplit une ligne"]
  ajout["➕ L'artisan ajoute une ligne<br/>au clic ou à la voix"]
  sugg["<b>Suggestion grisée</b>"]
  acc["<b>✅ Acceptée</b>"]
  mod["<b>✏️ Modifiée par l'artisan</b>"]
  sup["🗑️ Supprimée"]
  gen{"⚙️ Clic sur<br/>« Générer »"}
  chif["<b>💶 Chiffrée</b><br/>prix et source affichés"]
  nonrev["<b>⚠️ Chiffrée, non revue</b><br/>bloque l'export"]
  exp["📄 Exportée"]

  agent --> sugg
  ajout --> acc
  sugg -- "accepter" --> acc
  sugg -- "modifier" --> mod
  sugg -- "supprimer" --> sup
  acc -- "modifier" --> mod
  acc --> gen
  mod --> gen
  sugg -. "jamais revue" .-> gen
  gen -- "ligne revue" --> chif
  gen -- "suggestion non revue" --> nonrev
  nonrev -- "accepter" --> chif
  chif -. "modifier : à regénérer" .-> mod
  chif --> exp

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef grise fill:#ececec,stroke:#8a8a8a,stroke-dasharray:5 4,color:#555555
  classDef ok fill:#ffffff,stroke:#15803d,stroke-width:2px,color:#0f5132
  classDef decision fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef stop fill:#fdecea,stroke:#b91c1c,color:#7a1010
  classDef fin fill:#1168bd,stroke:#0b4884,color:#ffffff
  class agent,ajout,mod etape
  class sugg grise
  class acc,chif ok
  class gen decision
  class sup,nonrev stop
  class exp fin
```

#### 5. La mémoire de l'agent

> 💡 **En bref** : L'agent se souvient de la conversation en cours ; en V1.1, il retiendra aussi les habitudes de chaque artisan.

L'agent se souvient à deux échelles : la conversation en cours (mémoire courte) et l'artisan
lui-même (mémoire longue, sa fiche des préférences). Chaque projet de devis garde en plus son
propre état. Tout vit dans la même base PostgreSQL + pgvector que le corpus, portée par le même
module que la recherche (RAG). **Périmètre** : la mémoire courte est en V1 ; la mémoire longue
(fiche des préférences et LLM juge) en V1.1.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 380}}}%%
flowchart TB
  tour["💬 <b>Un tour de conversation</b><br/>l'artisan dicte, l'agent répond"]
  courte["🧠 <b>Mémoire courte</b><br/>les 30 derniers tours de la conversation<br/>au-delà, le plus ancien sort de la fenêtre"]
  compteur{"🔢 <b>Compteur de tours</b><br/>multiple de 15 ?"}
  juge["⚖️ <b>LLM juge, en parallèle</b><br/>relit les derniers tours et en tire les préférences<br/>ne bloque jamais la conversation"]
  fiche["📇 <b>Fiche des préférences de l'artisan</b><br/>mémoire longue, mise à jour par le juge [DP]<br/>l'artisan peut la voir, la corriger, la supprimer"]
  projet["📁 <b>Données du projet de devis</b><br/>métadonnées<br/>commentaires système : où en est le travail,<br/>laissés par l'agent quand il reprend le devis<br/>commentaires de l'artisan"]
  charge["📥 <b>Au tour suivant, l'agent charge</b><br/>fiche des préférences + mémoire courte<br/>+ données du projet"]
  rag["📚 <b>Passages du corpus</b> pour le lot en cours"]
  llm["🤖 <b>Appel au modèle</b>"]

  tour --> courte --> compteur
  compteur -- "oui, tous les 15 tours" --> juge
  juge -- "met à jour" --> fiche
  compteur -- "non, ou sans attendre le juge" --> charge
  fiche --> charge
  projet --> charge
  charge --> rag --> llm

  classDef etape fill:#eef4fb,stroke:#1168bd,color:#0b2e52
  classDef decision fill:#fff7e6,stroke:#b7791f,color:#5a3a00
  classDef cle fill:#1168bd,stroke:#0b4884,color:#ffffff
  class tour,courte,juge,fiche,projet,rag,llm etape
  class compteur decision
  class charge cle
```

Ce que contient chaque mémoire :

| Mémoire | Contenu | Durée de vie | Qui écrit |
|---|---|---|---|
| Courte | Les 30 derniers tours de la conversation en cours | Glissante : le 31ᵉ tour fait sortir le plus ancien | Le code, à chaque tour |
| Longue — fiche des préférences | Les habitudes de l'artisan : gammes, façons de découper et de rédiger ses devis | Tant que le compte existe ; conservation à fixer (Q-21) | Le LLM juge, tous les 15 tours ; l'artisan la corrige ou la supprime |
| Projet de devis | Métadonnées, commentaires système, commentaires de l'artisan | Celle du projet | Le code, l'agent quand il reprend le devis, l'artisan |

## 7. Le contrat — critères d'acceptance

> 🧭 Comment on saura que la V1 est finie : six phrases auxquelles on répond par oui ou par non.

| # | Étant donné… | quand… | alors… |
|---|---|---|---|
| 1 | une sortie du modèle non conforme au schéma | l'artisan envoie un message | l'agent relance une seule fois, puis dit ce qu'il n'a pas compris et redemande — jamais la sortie brute, jamais d'arrêt de session — et le motif est compté dans `/metriques` |
| 2 | deux artisans A et B, chacun avec ses projets | A demande un projet de B, même en connaissant son identifiant | l'accès est refusé, sans rien révéler du projet de B |
| 3 | un devis pré-rempli par l'agent | l'artisan n'a pas encore cliqué « Générer » | aucun prix ni montant n'y figure, et les suggestions de l'agent sont visibles comme telles (grisées) |
| 4 | un devis édité par l'artisan | il clique « Générer » | chaque ligne se recalcule (quantité × prix unitaire) et cite sa référence et sa source catalogue |
| 5 | un ouvrage absent du référentiel, par exemple une réfection de toiture | l'artisan le dicte | une proposition générique grisée est ajoutée, sans rendement inventé, et l'artisan peut la modifier ou l'affiner avec un produit référencé |
| 6 | un devis validé, profil artisan complet | l'artisan l'exporte | un fichier Word est produit avec SIRET, assurance décennale, TVA ventilée par taux et date de validité |

Chaque critère se démontre sur l'URL de production et se vérifie par un test automatisé ou une
étape du parcours de bout en bout (`tools/parcours_bout_en_bout.py`).

## 8. Plan des sprints 2 à 5 et risques

> 🧭 Dans quel ordre on avance, et ce qui peut faire dérailler chaque étape.

### A. Risques par sprint

> 💡 **En bref** : Pour chaque étape, ce qui peut mal tourner et ce qui est prévu pour l'éviter.

Le contenu de chaque jour est au §2. Ce tableau dit ce qui peut faire dérailler chaque étape, et
la parade prévue.

| Sprint | Jours | Risque principal | Parade |
|---|---|---|---|
| 2 — Socle et chaîne | 1 et 2 | Quota GPU refusé ou tardif ; démarrage à froid du modèle au-delà de 30 s | Demander le quota dès le jour 1 ; mesurer le démarrage à froid et, si besoin, garder une instance chaude pendant les démonstrations |
| 3 — Données et ancrage | 3 et 4 | Corpus pauvre ou sous licence restrictive ; seuil de refus mal réglé | Vérifier la licence source par source ; régler le seuil sur les questions de démonstration, refus hors corpus compris |
| 4 et 5 — Fiabilité et démonstration | 5 et 6 | Jeu de test trop petit pour départager deux prompts | Démarrer avec un jeu initial, l'enrichir à chaque correction de l'artisan (signal qualité) |
| V2 potentielle | — | Le prompt plafonne sous l'objectif ; des voix parasites polluent la dictée | Fine-tuning du modèle retenu ; segmentation de la voix pour isoler l'artisan |

### B. Risque transverse : le RGPD

> 💡 **En bref** : Les données des artisans et de leurs clients restent en Europe, chez des prestataires encadrés par contrat.

Le RGPD (règlement général sur la protection des données) s'applique : les dictées
et les coordonnées des clients sont désormais chez Google Cloud. Il faut la région
`europe-west1` partout, journaux compris, et le contrat de sous-traitance de Google Cloud
(`docs/donnees/RGPD.md`, point 8). Langfuse est un sous-traitant de plus : région européenne, et
masquage des noms, adresses et coordonnées avant l'envoi des traces. Le modèle d'embeddings, sur
Azure AI Foundry, en ajoute un autre, Microsoft Azure : région UE à exiger au déploiement, contrat
de sous-traitance, et aucune coordonnée de client dans les textes envoyés à vectoriser. La fiche
des préférences de l'artisan (§6.C.5) est une donnée personnelle : l'artisan peut la voir, la
corriger et la supprimer ; sa durée de conservation et ce qui est envoyé au LLM juge restent à
fixer (Q-21).

## 9. Ce qui reste à valider

> 🧭 Les décisions qui restent ouvertes, et qui doit les prendre.

| Point | Proposition | Qui tranche |
|---|---|---|
| Intitulé de la composante agentique dans le menu | Workflow orchestré avec humain dans la boucle | Formateur |
| Modèle d'embeddings | Fournisseur tranché : Azure AI Foundry (D-36). Reste le modèle précis, multilingue, mesuré sur les questions de démonstration, et sa région UE | Auteur du projet |
| Mémoire longue | Durée de conservation de la fiche des préférences, droit de regard de l'artisan, ce qui est envoyé au LLM juge (Q-21) | Auteur du projet |
| Langfuse hébergé ou auto-hébergé | Langfuse Cloud, région UE, pour la V1 : rien à administrer ; auto-hébergé sur GCP si les données ne doivent pas sortir du projet | Auteur du projet |
| Liste des modèles candidats au benchmark | Voir §6.C.1 : un auto-hébergé, trois servis en Europe par API | Auteur du projet |
| Ordre de priorité des prix | Artisan, prix habituel, catalogue, document du corpus (§6.C.2) | Auteur du projet |
| Sources du corpus technique | Fiches fabricants et documentation métier, collectées en une fois ou par scraping ; licence de chacune à vérifier | Auteur du projet |
| Anciens devis et factures de l'artisan, y compris papier, comme source | À compléter : volume, numérisation, pseudonymisation | Auteur du projet |

## 10. Ce que les projets précédents apportent

> 🧭 Ce que mes projets agentiques précédents m'ont appris, et que je reprends ici.

Six projets agentiques antérieurs ont été relus et comparés (`docs/ancrages - anciens projets/`,
synthèse dans `SYNTHESE.md`). Leur constat d'ensemble : **l'ingénierie est solide partout, mais la
qualité du vrai modèle n'est mesurée nulle part de façon reproductible**, et aucun projet ne
contraint la sortie du modèle tout en versionnant ses prompts. C'est exactement ce que la V1
corrige. Les pratiques reprises, et où elles entrent :

### A. Les pratiques reprises

| Pratique éprouvée | Projet d'origine | Où elle entre dans la V1 |
|---|---|---|
| Sortie contrainte par un schéma JSON strict, au lieu d'extraire le JSON du texte | Version de travail de Mardik LLMOps | Client du modèle (§6.A, niveau 3) |
| Prompts versionnés, empreinte de version portée par chaque mesure | Mardik LLMOps, Sorabel | Prompts versionnés ; chaque rapport d'évaluation cite sa version |
| Évaluation qui **bloque** la chaîne par construction (`needs:`), pas par convention | Mardik LLMOps, Velmo2 | Chaîne CI/CD, sprints 4 ou 5 |
| CI gratuite et déterministe à chaque push ; CI payante sur le vrai modèle, déclenchée à part | Velmo2 | Chaîne CI/CD : tests avec faux modèle, évaluation sur le service GPU |
| RAG avec seuil de refus sur la note brute, et citations reconstruites par le code, jamais écrites par le modèle | Sorabel | Recherche dans le corpus (sprint 3) |
| Une panne n'est jamais déguisée en résultat métier (« corpus indisponible » ≠ « hors corpus ») | Sorabel | Recherche dans le corpus, typologie d'échecs du pipeline |
| Rejouer des sessions enregistrées à travers la vraie pile | mARDIK, Kaldera | Jeu de test rejoué sur la production |
| Pseudonymiser avant d'écrire sur disque, puis relecture humaine avant d'entrer au jeu de test | Mardik LLMOps | Anciens devis (Q-14), signal qualité |
| Journaux et traces corrélés, sans données personnelles dans les métriques | mARDIK | Langfuse et Cloud Logging |
| Retour arrière tracé, déclenché sur un seuil | Mardik LLMOps | Pilotage (§6.B), sprint 2 |

### B. Ce que ce projet apporte en propre

À préserver : « le modèle décrit, le code
calcule », poussé jusqu'au schéma (aucun champ prix) ; la reformulation jetée si un nombre change ;
aucun prix avant « Générer » ; l'authentification fermée par défaut.

### C. Les erreurs vues ailleurs à ne pas reproduire

Des surfaces annexes sans authentification à
côté d'un cœur protégé ; des données personnelles envoyées au modèle ou aux traces ; un appel au
modèle sans délai ni plafond ; une documentation qui ment sur le code.

## 11. La présentation à l'atelier croisé

> 🧭 Comment ce dossier se présente en vingt minutes.

Vingt minutes de présentation, sans code, puis quinze minutes de questions guidées par la grille
du §12, et dix minutes de conseils. Ensuite, les rôles s'inversent.

### A. Le déroulé

| Temps | Section | Le message à faire passer |
|---|---|---|
| 3 min | §1 Besoin | L'artisan dicte, l'agent pré-remplit, l'artisan édite puis génère ; aucun prix inventé, par construction |
| 3 min | §2 et §3 Périmètre | Six jours : choisir le modèle, livrer par la chaîne, ancrer sur un corpus, mesurer le prompt ; le fine-tuning est une V2 potentielle |
| 4 min | §4 Composante agentique | Pourquoi un workflow contrôlé, avec l'artisan dans la boucle, plutôt qu'un agent autonome |
| 2 min | §5 Stack | Deux services dans GCP, une base PostgreSQL, un seul élément exotique |
| 3 min | §6.A et §6.B Architecture et pilotage | Trois niveaux C4 ; deux chemins vers la production : la fusion ne paie rien, la promotion se mérite |
| 2 min | §6.C Mécanismes clés | Le modèle se choisit sur des mesures ; le prix a toujours une source ; l'artisan corrige une case à la voix ; l'agent se souvient de la conversation et de l'artisan |
| 2 min | §7 Contrat | Lire deux critères à voix haute et montrer qu'on répond oui ou non |
| 1 min | §9 Points à valider | Ce que le formateur doit trancher |

### B. À montrer en direct

Si on le souhaite : l'application lancée sur le poste de développement,
et son cas dégradé — une phrase dictée, et la réponse « le moteur d'analyse ne répond pas » avec
le devis conservé. C'est la preuve du constat du §2.

## 12. Grille d'évaluation — atelier croisé n°1

> 🧭 La grille que remplit l'évaluateur.

À remplir par l'évaluateur pendant la présentation. Cotation : **démontré**, **partiel** ou
**absent**, chaque cotation appuyée sur une preuve observée. L'évaluateur lit ce dossier en se
mettant à la place d'un futur repreneur du projet.

### A. Identification

| Présenté | Évaluateur | Date | Projet |
|---|---|---|---|
| Mehdi Chadli | Steeve | | Assistant devis BTP vocal |

### B. Les six critères

| # | Critère | Cotation | Preuve observée, remarque |
|---|---|---|---|
| 1 | **Besoin clair.** En une page, je comprends à qui sert le projet et ce que promet le parcours principal. | | |
| 2 | **Périmètre tenable.** La V1 me paraît réalisable en six jours par une personne. Sinon, qu'est-ce que je couperais ? | | |
| 3 | **Hors-périmètre assumé.** Ce que la V1 ne fera pas est écrit noir sur blanc. | | |
| 4 | **Composante agentique à la hauteur.** Elle figure au menu, au bon niveau, et la justification me convainc. | | |
| 5 | **Stack justifiée.** Socle du parcours, ou dérogation argumentée (un seul élément exotique). | | |
| 6 | **Critères vérifiables.** Pour chaque critère du contrat, je peux répondre oui ou non en le lisant. | | |

### C. Conseils

**Le point fort du dossier :**

**Le conseil prioritaire pour le sprint 2** (actionnable avant la fin du sprint 2) :

**Avis sur le périmètre** (le formateur tranche) — tenable en l'état, ou à resserrer, et sur
quoi :

## 13. Journal des retours

> 🧭 Ce que je fais de chaque retour reçu.

Le sprint 2 demande que chaque retour de l'atelier n°1 soit **traité, reporté ou écarté**. Une
ligne par retour, remplie après l'atelier.

| # | Retour reçu | De qui | Suite donnée | Où c'est visible |
|---|---|---|---|---|
| 1 | Au lieu d'entraîner, versionner le prompt et les données | Steeve | **Traité** : prompt versionné et évalué en V1 ; fine-tuning en V2 potentielle | §2, §3, `docs/DECISIONS.md` D-23 |
| 2 | RAG | Steeve | **Traité** : la connaissance métier vient d'un corpus technique interrogé | §2, §4, §8, D-24 |
| 3 | Anciennes factures et devis, y compris papier, pour entraîner | Steeve | **Reporté** : source à compléter (volume, numérisation, pseudonymisation) | §9, Q-14 |
| 4 | Travailler le schéma complet | Steeve | **Traité** : architecture au modèle C4, trois niveaux | §6.A |
| 5 | Analyse application web contre application mobile | Steeve | **En cours** : à étudier et documenter | — |
| 6 | RGPD | Steeve | **En cours** : stratégie complète avec son propre schéma | — |
| 7 | Stratégie Git | Steeve | **Traité** : GitHub Flow avec versions étiquetées, comparée à GitFlow et au trunk-based | §6.B |
| 8 | Les différents pipelines CI/CD (release, correctif…) et pourquoi ces stratégies | Steeve | **Traité** : trois chaînes (PR, fusion, étiquette), environnements, signaux, justification | §6.B |
| 9 | Résumer les anciens projets agentiques et en faire la synthèse | Steeve | **Traité** : synthèse et pratiques reprises dans la V1 | §10 |
