# Benchmark : la reconnaissance vocale du produit

> **Pourquoi ce document existe.** L'entrée du produit est la voix. C'est la
> seule brique où le projet hésite encore vraiment : servir un modèle de
> transcription nous-mêmes, ou appeler une **API** (interface de programmation)
> d'un fournisseur. `docs/DECISIONS.md` (Q-03) porte la question, et
> `docs/exploitation/INCIDENTS.md` (INC-10) montre qu'elle a déjà produit un défaut réel.
>
> **Actualisé le 12/10/2026.** Le document a été écrit quand le projet tournait
> sur une DGX Spark avec un principe « 100 % local ». Ce principe est remplacé
> (`docs/DECISIONS.md` D-18 à D-21) : le produit tourne sur GCP, en région
> européenne. Dans ce qui suit, **« local » désigne un modèle servi par nous**, sur
> le service GPU Cloud Run du projet, par opposition à une API de fournisseur.
>
> Ce document rassemble la matière du choix. **Il ne tranche pas** l'arbitrage
> final — celui-là appartient à l'auteur du projet, et la section 7 dit
> exactement sur quoi il porte et ce que chaque branche coûte en code.

**Abréviations employées.** *STT* : *speech-to-text*, reconnaissance vocale.
*WER* : *word error rate*, taux d'erreur de mots — la métrique standard du
domaine, en pourcentage, plus bas est meilleur. *VAD* : *voice activity
detection*, détection de parole, qui découpe l'audio avant transcription.
*HITL* : *human in the loop*, les points où l'artisan valide. *RGPD* : règlement général
sur la protection des données.

**Statut des chiffres.** Tout ce qui suit est **documentaire** : specifications
constructeur, tarifs publics, mesures publiées par des tiers. **Aucune mesure
n'a été faite sur le corpus du projet.** La section 8 dit ce qu'il faudra
mesurer pour que ce benchmark cesse d'être une revue de littérature. Les
chiffres de coût des concurrents proviennent en partie des pages comparatives
d'un des fournisseurs comparés : ils sont signalés comme tels et valent comme
ordre de grandeur, pas comme preuve.

## 1. L'expression de besoin

**Le besoin en une phrase.** Un artisan, seul, sur un chantier bruyant, dicte à
voix haute la description d'un ouvrage à réaliser — surfaces, pièces, matériaux,
nom et adresse du client — et doit pouvoir relire ce texte et le corriger avant
qu'il ne parte au traitement.

Ce que ce contexte impose, besoin par besoin :

| Besoin | Ce qu'il impose au service | D'où il vient |
|---|---|---|
| Dictée en français, vocabulaire du bâtiment | Modèle multilingue ou français, tolérant au jargon (« placo », « ragréage », « GTL ») | `docs/produit/CADRAGE_MODELE.md`, périmètre quatre corps de métier |
| Noms propres et adresses de clients | Ces mots sont hors vocabulaire courant et **ne sont pas rattrapables** par le contexte | Mentions obligatoires BTP, `app/profil.py` (`Client`) |
| Environnement bruyant | Robustesse au bruit large bande (perceuse, radio, extérieur) | Usage sur chantier, `docs/produit/DISPOSITIF_AGENT.md` |
| Confidentialité de la voix | La voix porte des données personnelles de tiers : le client final **n'est pas utilisateur** et n'a rien consenti | `docs/donnees/RGPD.md`, incident INC-10 |
| Latence acceptable | La dictée est relue en HITL-0 : quelques secondes après la fin de la phrase suffisent. **Le temps réel mot à mot n'est pas requis.** | US-05, `app/transcription.py` |
| Coût par artisan | Le produit vise l'artisan seul, pas le grand compte : un coût mensuel à trois chiffres tue l'usage | Modèle économique du cadrage |
| Fonctionnement dégradé | Le chantier a du réseau une fois sur deux | US-04, cas dégradé |

**Ce qui n'est pas un besoin**, et qu'il ne faut donc pas payer :

- la **diarisation** (qui parle) : il y a un seul locuteur, l'artisan ;
- la **traduction** : le produit est français ;
- le **temps réel sub-seconde** : la relecture HITL-0 absorbe la latence ;
- le **sous-titrage horodaté** : aucun média n'est produit ;
- la **transcription de fichiers longs** (réunions d'une heure) : les dictées de
  chantier tiennent en une à trois minutes.

Cette liste compte autant que la précédente : c'est elle qui écarte des services
excellents mais dimensionnés pour un autre métier.

## 2. Le panel : ce qui a été étudié, ce qui ne l'a pas été

### Les six solutions étudiées

| Solution | Nature | Où tourne l'audio |
|---|---|---|
| **Web Speech API** | API du navigateur | Chez l'éditeur du navigateur, sauf `processLocally` |
| **faster-whisper large-v3-turbo** | Modèle ouvert, servi par nous | Sur notre service GPU, région européenne |
| **NVIDIA Parakeet TDT 0.6b v3** | Modèle ouvert, servi par nous | Sur notre service GPU, région européenne |
| **Gladia** | API commerciale, éditeur français | Chez le fournisseur, région Union européenne |
| **Deepgram** | API commerciale, éditeur américain | Chez le fournisseur |
| **Azure AI Speech** | API commerciale, éditeur américain | Chez le fournisseur, région au choix |

### Les solutions écartées sans étude, et pourquoi

Un benchmark qui ne liste que ce qu'il a regardé cache son angle mort. Voici ce
qui n'a **pas** été étudié, avec le motif :

| Écarté d'emblée | Motif |
|---|---|
| AssemblyAI, Speechmatics, Google Cloud Speech, AWS Transcribe | Même famille que Deepgram et Azure — API commerciale, audio hors machine. Le panel en garde trois, ce qui suffit à instruire le débat « distant contre local » ; en ajouter quatre allongerait le tableau sans déplacer la conclusion. |
| API OpenAI de transcription | Même famille, et redondante avec Whisper : le modèle sous-jacent est déjà étudié en version locale, qui est celle qui intéresse le projet. |
| Vosk, wav2vec2, autres modèles ouverts antérieurs | Génération précédente. Sur le français, l'écart de qualité avec les deux modèles locaux retenus n'est pas discutable au point de mériter un banc d'essai. |
| Dictée native du système (Windows, macOS, Android) | Le canal de démo est **web uniquement** (cadrage). Une dictée système n'est pas intégrable à une application web sans passer par la Web Speech API, déjà au panel. |
| Solutions de transcription de réunion | Répondent aux besoins explicitement exclus en section 1 : diarisation, fichiers longs, horodatage. |

## 3. La grille de critères

| Critère | Poids | Pourquoi ce poids |
|---|---|---|
| **Confidentialité de la voix** | Bloquant | Un principe écrit au cadrage et une donnée personnelle de tiers. Un service qui échoue ici n'est pas rattrapable par ses qualités. |
| **Qualité en français bruité** | Fort | Une erreur sur un chiffre de surface se propage jusqu'au devis. La relecture HITL-0 la rattrape, mais au prix du temps de l'artisan. |
| **Noms propres et adresses** | Fort | Une adresse fausse rend une mention obligatoire fausse. |
| **Coût à l'usage réel** | Moyen | Compte au-delà du prototype, pas avant. |
| **Empreinte énergétique** | Moyen | Critère explicite du référentiel, et vrai arbitrage ici (section 6). |
| **Latence** | Faible | Le besoin est modeste et tous les candidats le tiennent. |
| **Pérennité du fournisseur** | Moyen | Un modèle ouvert ne disparaît pas ; une API, si. |
| **Coût d'intégration** | Moyen | Le prototype existant est déjà écrit pour l'un des candidats. |

## 4. Fiche par solution : contraintes techniques et prérequis

### Web Speech API

Ce qui est **déjà en production dans le dépôt** (`app/static/index.html`,
lignes 745 et suivantes).

- **Prérequis** : aucun côté serveur. Un navigateur récent côté client.
- **Contrainte majeure** : malgré son nom, l'API ne transcrit pas dans le
  navigateur. Chrome envoie l'audio à un service Google, Safari au sien. C'est
  la cause de l'incident INC-10.
- **Atténuation existante** : l'attribut `processLocally` (Chrome 139 et
  au-delà) garde la transcription sur l'appareil. Le front le réclame, et
  lorsqu'il n'est pas disponible **il ne bascule pas en silence** : il nomme ce
  qui sortirait et demande un accord refusable.
- **Limites qui restent** : dépendance à un navigateur et à une version
  précises ; qualité non mesurable et non reproductible (le service change sans
  préavis) ; aucun contrôle sur le vocabulaire.
- **Verdict d'usage** : convient comme **repli de secours accepté par
  l'artisan**, jamais comme brique de référence.

### faster-whisper large-v3-turbo

- **Prérequis** : `faster-whisper`, un modèle d'environ 809 millions de
  paramètres (version élaguée de large-v3 : 32 couches de décodeur ramenées à
  4), environ 1,5 Go de mémoire vidéo en quantification `int8`.
- **Qualité** : la dégradation face à large-v3 sur les langues de premier rang,
  dont le français, est annoncée entre 0,5 et 2 points de WER. Un banc d'essai
  francophone tiers sur une carte portable modeste rapporte environ 7,7 % de WER
  en meilleure configuration.
- **Contraintes connues** : la version *turbo* est faite pour la
  **transcription**, pas la traduction, qui se dégrade nettement. Le modèle est
  sujet à des boucles de répétition sur les silences longs — le VAD en amont est
  la parade usuelle, pas une option.
- **Intégration** : bibliothèque Python, appel synchrone, pas de service à
  exploiter. Le *streaming* n'est pas natif : il se simule par découpage, ce qui
  est acceptable pour un besoin de dictée relue.

### NVIDIA Parakeet TDT 0.6b v3

- **Prérequis** : l'écosystème NeMo de NVIDIA, environ 600 millions de
  paramètres, architecture FastConformer avec transducteur *Token-and-Duration*.
- **Qualité** : 25 langues dont le français ; environ 6,34 % de WER agrégé sur
  le classement public *Open ASR Leaderboard* pour la version multilingue.
- **Contraintes connues** : le décodage glouton bat le décodage par faisceau à
  la fois en vitesse **et** en WER, ce qui simplifie l'exploitation. L'attention
  pleine permet des fichiers jusqu'à environ 24 minutes, très au-delà du besoin.
- **Affinité matérielle** : conçu et optimisé par NVIDIA, donc aligné sur le
  GPU NVIDIA L4 du service de modèle.
- **Réserve** : le classement cité est majoritairement anglophone dans sa
  construction ; le WER agrégé n'est **pas** une mesure française.

### Gladia

- **Prérequis** : une clé d'API, un compte, du réseau. Le prototype
  `Speech-to-text.py` du dépôt exploite déjà son *streaming* par websocket, et
  la dépendance `gladiaio-sdk` est épinglée dans `pyproject.toml`.
- **Cadre juridique** : société française, résidence des données annoncée dans
  l'Union européenne, conformité RGPD revendiquée avec certifications SOC 2
  type II, HIPAA et ISO 27001.
- **Coût public** : à partir d'environ 0,61 dollar par heure d'audio en
  asynchrone, 0,75 en temps réel, jusqu'à environ 0,20 au volume.
- **Pérennité** : OVH Groupe est entré en négociations exclusives pour acquérir
  Gladia en juin 2026. C'est une donnée à double lecture — un adossement à un
  acteur européen de l'hébergement plutôt qu'une disparition, mais une
  incertitude contractuelle le temps de l'opération.
- **Contrainte de fond** : la voix quitte la machine. Aucune certification ne
  change ce fait, et c'est ce fait, pas la conformité, que le cadrage interdit.

### Deepgram

- **Contrainte rédhibitoire identifiée** : l'audio des clients est utilisé par
  défaut pour l'amélioration des modèles, et le refus de cet usage se paie par
  un tarif approximativement doublé.
- Un point de terminaison européen existe.
- **Verdict** : écarté sur ce seul motif. Faire payer la confidentialité est
  incompatible avec un produit qui traite des données de tiers non consentants.

### Azure AI Speech

- **Prérequis** : abonnement Azure, ressource régionale, gestion de clés.
- **Coût public** : environ 1,50 dollar par heure en temps réel avec
  diarisation — fonction dont le projet n'a pas besoin.
- **Contrainte** : un traitement strictement européen suppose de choisir des
  régions précises (Allemagne Centre-Ouest, Suède Centre), ce qui ajoute une
  contrainte d'exploitation permanente.
- **Verdict** : le service est solide, mais le contrat le plus lourd du panel
  pour le besoin le plus léger.

## 5. Adéquation par ensemble fonctionnel

Chaque case dit le niveau d'adéquation **sur spécifications publiées**, pas sur
mesure. Le mot compte, la couleur n'existe pas : « oui », « partiel », « non ».

| Ensemble fonctionnel | Web Speech | Whisper turbo | Parakeet | Gladia | Deepgram | Azure |
|---|---|---|---|---|---|---|
| Dictée courte, moins d'une minute | oui | oui | oui | oui | oui | oui |
| Dictée longue, plusieurs minutes | partiel | oui | oui | oui | oui | oui |
| Français avec jargon du bâtiment | partiel | partiel | partiel | partiel | partiel | partiel |
| Noms propres, adresses de clients | non | partiel | partiel | partiel | partiel | partiel |
| Chantier bruyant | partiel | partiel | partiel | partiel | partiel | partiel |
| L'audio ne quitte pas la machine | partiel | oui | oui | non | non | non |
| Fonctionne sans réseau | non | oui | oui | non | non | non |
| Coût nul à l'usage | oui | oui | oui | non | non | non |
| Reproductible pour la démo au jury | non | oui | oui | partiel | partiel | partiel |

**Ce que ce tableau ne dit pas, et qu'il faut lire.** Cinq lignes sur neuf sont
« partiel » partout : jargon, noms propres, bruit. Ce sont précisément les
lignes qui décident de la qualité perçue du produit, et ce sont les seules que
la documentation des fournisseurs ne permet pas de départager. **Aucun choix
honnête ne peut être fait sans la mesure décrite en section 8** — le tableau
sert à éliminer, pas à élire.

## 6. L'éco-responsabilité, sans argument facile

### Le piège

L'argument commode serait : « servir soi-même évite un fournisseur de plus, donc
c'est plus sobre ». Il est faux tel quel : un modèle servi par nous consomme un
GPU, qu'il faut allumer.

### Ce que chaque fournisseur publie

| Service | Ce qui est publié | Ce qui reste opaque |
|---|---|---|
| Whisper turbo, Parakeet (servis par nous) | GCP fournit une estimation d'empreinte carbone par projet et par service | Ce n'est pas une mesure : l'imputation à une heure d'audio reste une estimation |
| Gladia | Résidence des données, certifications | Aucune donnée d'empreinte publiée |
| Deepgram | Tarifs, régions | Aucune donnée d'empreinte publiée |
| Azure | Engagements carbone et indicateurs d'efficacité au niveau du groupe et des centres de données | Rien au niveau du service de transcription : impossible d'imputer une heure d'audio |

Depuis le passage sur GCP, **aucune option n'est mesurable au wattmètre par le
projet** : l'ordre de grandeur calculé pour la DGX Spark ne s'applique plus et a
été retiré.

### La condition d'usage, qui tient toujours

Le raisonnement qui portait la conclusion reste vrai, transposé : le terme
dominant n'est pas la transcription, c'est **le GPU allumé**.

- Si la transcription tourne **sur le service GPU déjà allumé pour le LLM** —
  l'artisan dicte, puis le modèle structure dans la foulée —, son coût marginal
  est faible : le GPU L4 a 24 Go, le LLM en occupe environ 14, et Parakeet ou
  Whisper turbo tiennent dans le reste.
- Si un GPU devait être allumé **uniquement** pour transcrire, une API mutualisée
  amortirait mieux son matériel.

L'éco-responsabilité désigne donc toujours une **condition d'usage**, pas un
fournisseur.

### Ce que le produit fait déjà, et qui compte

- Le front est **un fichier unique, sans cadriciel, sans dépendance externe,
  sans image** : la page transférée est de l'ordre de quelques dizaines de
  kilo-octets. C'est de l'éco-conception effective, pas une intention.
- L'audio n'est pas conservé : seul le texte relu est persisté
  (`docs/donnees/RGPD.md`). Le stockage est le poste d'empreinte le plus facile à
  laisser filer, et il est déjà fermé.
- Aucun appel de modèle n'est fait sur une dictée non relue : HITL-0 filtre
  avant, et non après, ce qui évite les traitements jetés.

## 7. Conclusions : retenus, écartés, et ce qui reste à trancher

### Écartés, sur des faits

| Écarté | Fait qui décide |
|---|---|
| **Deepgram** | Usage par défaut de l'audio client pour l'entraînement, et surcoût pour s'y soustraire. Incompatible avec des données de tiers non consentants. |
| **Azure AI Speech** | Le contrat et l'exploitation les plus lourds du panel, pour une fonction dont le produit n'utiliserait qu'une fraction. Le confinement européen suppose un choix de régions à maintenir. |
| **Web Speech API comme brique de référence** | La transcription part chez l'éditeur du navigateur dès que `processLocally` est absent. Conservée uniquement comme **repli explicitement accepté**, jamais comme voie normale. |

### Retenus en finale

| Retenu | Ce qui le qualifie |
|---|---|
| **faster-whisper large-v3-turbo** | Servi par nous, écosystème Python mûr, dégradation française annoncée faible, quantification légère. |
| **NVIDIA Parakeet TDT 0.6b v3** | Servi par nous, aligné sur le GPU NVIDIA du service, décodage glouton simple et rapide, français couvert. |
| **Gladia** | Éditeur français, résidence européenne, prototype déjà écrit. Recevable depuis D-18, au prix d'un sous-traitant de plus. |

### L'arbitrage qui appartient à l'auteur du projet

`docs/DECISIONS.md` (Q-03) pose la question et ne la tranche pas. Ce benchmark ne la
tranche pas davantage — il la réduit à une seule phrase :

> **La transcription tourne-t-elle sur notre service GPU, ou chez Gladia ?**

Les deux réponses sont défendables, et elles n'ont pas le même coût :

| Si la réponse est… | Alors | Ce que ça change dans le code |
|---|---|---|
| « sur notre service GPU » | Le finaliste est **Whisper turbo ou Parakeet**, départagés par la mesure de la section 8 | US-04 implémente un point d'entrée de transcription ; le modèle partage le GPU du LLM ; `gladiaio-sdk` sort de `pyproject.toml` ; `Speech-to-text.py` devient un vestige à retirer |
| « chez Gladia » | Le prototype existant a de la valeur | `docs/donnees/RGPD.md` gagne un sous-traitant ; la clé d'API passe par Secret Manager |

Ce qui n'est **pas** arbitrable, en revanche, et vaut dans les deux branches :
l'artisan doit savoir où va sa voix, et le produit ne doit jamais basculer d'un
mode à l'autre en silence. C'est l'acquis d'INC-10, et il précède le choix.

## 8. Le protocole de mesure, encore à tenir

Ce benchmark restera une revue de littérature tant que ceci n'aura pas été fait.
Ce n'est pas long, et rien ne le remplace.

**Le corpus.** Trente dictées de chantier enregistrées par l'auteur, réparties
sur les quatre corps de métier du périmètre, dont au moins dix en environnement
bruyant réel, et dont chacune contient un nom de client, une adresse et trois
chiffres de dimension. **Transcription de référence écrite à la main.** Le
corpus reste sur la machine et ne rejoint pas le dépôt : il porte des données
personnelles.

**Les métriques**, dans cet ordre d'importance :

1. **taux d'erreur sur les chiffres et les unités** — le seul qui contamine le
   devis. Un WER global de 5 % avec une surface fausse est pire qu'un WER de
   10 % intact ;
2. **taux d'erreur sur les noms propres et adresses** ;
3. WER global, pour comparabilité externe ;
4. latence sur une dictée de 90 secondes, au 95e centile ;
5. **temps GPU consommé** pour transcrire le corpus entier, seul indicateur
   d'énergie que le projet puisse relever lui-même sur Cloud Run (section 6).

**Ce que la mesure a le droit de faire.** Départager Whisper turbo et Parakeet :
c'est une question technique, elle se règle par un chiffre. **Ce qu'elle n'a pas
le droit de faire** : trancher entre servir soi-même et appeler une API. Si Gladia sortait meilleur
de trois points de WER, cela ne rendrait pas l'envoi de la voix acceptable — ce
serait un argument dans un arbitrage de principe, pas la décision.

## Sources

Consultées le 8 septembre 2026. Les tarifs et les mesures tierces vieillissent
vite ; la date compte autant que le lien.

- [Fiche du modèle NVIDIA Parakeet TDT 0.6b v3 sur Hugging Face](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) — langues couvertes, architecture, WER agrégé.
- [Fiche du modèle OpenAI Whisper large-v3-turbo sur Hugging Face](https://huggingface.co/openai/whisper-large-v3-turbo) — élagage du décodeur, dégradation annoncée, restriction à la transcription.
- [Grille tarifaire publique de Gladia](https://www.gladia.io/pricing) — tarifs asynchrone, temps réel et volume.
- [Blog de Gladia sur la résidence des données et la conformité](https://www.gladia.io/blog) — certifications, région européenne, comparaisons tarifaires avec Deepgram et Azure. **Source intéressée** : c'est un fournisseur du panel qui compare ses concurrents.
