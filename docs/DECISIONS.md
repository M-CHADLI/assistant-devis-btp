# Journal des décisions

> **Seul document d'historique du dépôt.** Les autres documents de `docs/` décrivent l'état
> **courant** du projet et ne racontent plus comment on y est arrivé. Quand une décision change
> le projet, on ajoute une entrée ici **et** on met à jour le document d'état concerné — dans le
> même commit.
>
> Une entrée dit : le contexte, ce qui a été choisi, la raison, ce que ça coûte. Une décision
> remplacée n'est pas effacée : elle passe en « remplacée par D-xx ».
>
> Les questions pas encore arbitrées sont en fin de document. Elles appartiennent à l'auteur du
> projet : ne pas les trancher à sa place.

## Décisions en vigueur

### D-01 — Le modèle décrit, le code calcule
*Principe posé le 28/07/2026, jamais remis en cause.*
Le LLM produit du JSON structuré (intention, lots, quantités, références). Un code Python
déterministe fait les requêtes catalogue, les calculs, la TVA et le devis. **Le devis est généré
sans prix** : le modèle sort la structure et les quantités (stable), le catalogue injecte prix et
promos a posteriori (volatil).
*Raison* : zéro hallucination de prix, et une frontière testable.
*Où c'est décrit* : `docs/produit/CADRAGE_MODELE.md` §2.

### D-02 — Schéma de sortie unique
Une enveloppe `{ intent, payload, mention }` partagée par toutes les capacités ; le modèle signale
sa tâche via `intent`, le code route derrière.
*Raison* : un format à apprendre, un parseur, une métrique. Rend aussi un changement de modèle
sans effet en aval.
*Où* : `docs/produit/CADRAGE_MODELE.md` §6.

### D-04 — gpt-oss-20b, brut contre fine-tuné — *protocole remplacé par D-23*
Protocole : **20b brut bien promptté contre 20b fine-tuné**, même jeu de test gelé, même prompt
système, même service. La seule variable est le fine-tuning.
*Modifiée le 12/10/2026* : le 120b de démonstration est **suspendu** faute de machine (D-20) ; il
ne revient que sur décision écrite ici.
*Alternatives écartées pour l'instant* : Qwen3-30B-A3B, Gemma 4 26B A4B (licence à vérifier).

### D-05 — Le jeu de test est écrit à la main et gelé
150-200 exemples, écrits ou corrigés à la main, jamais générés, jamais vus à l'entraînement,
jamais élargis en cours de route. Détection de fuite bloquante entre entraînement et essai.
*Raison* : c'est la seule mesure honnête du projet, d'autant plus depuis D-09.

### D-06 — Posture sur le conseil réglementé : mention, jamais refus
Le modèle informe toujours, ne certifie jamais. Trois niveaux : rien / mention simple / mention
forte (gaz, tableau électrique, structure). gpt-oss embarque des refus pré-entraînés : les cas
sensibles **doivent** figurer au dataset avec le comportement voulu.

### D-07 — Produit B2B vocal, un seul utilisateur : l'artisan
*Remplace* l'ancien produit « Assistant Bricolage » destiné au client final (voir H-02).
L'artisan décrit son chantier à la voix, valide et corrige seul. Le client final n'est pas
utilisateur : ses coordonnées sont saisies parce que les mentions obligatoires BTP les exigent.
L'artisan fait autorité, toujours ; ses corrections sont journalisées comme signal qualité.
*Conséquence* : plus de session à deux, une seule interface à faire tenir.

### D-08 — Quatre corps de métier pilotes
Peinture, sols, plomberie, électricité, profondeur uniforme. Les deux derniers rendent les
exemples `mention forte` réels plutôt qu'hypothétiques.

### D-09 — Référentiel métier comblé par le LLM, relu et validé — *remplacée par D-24*
*Remplace* le référentiel sourcé ligne à ligne.
*Raison* : quatre corps de métier ne tiennent pas dans un sourcing manuel.
*Coût assumé* : l'argument du fine-tuning se déplace de « exactitude des valeurs métier » vers
**fiabilité du format JSON** et **qualité de structuration vocal → devis**. Le taux de JSON
valide porte seul cet argument ; à énoncer comme tel devant le jury.
*Maintenu* : le scraping des fiches fabricants reste, comme exercice de collecte (C1), distinct
du référentiel d'entraînement.

### D-10 — La V1 s'arrête au devis
Devis modifiable et exportable en Word.
*Modifiée par l'auteur du projet* : facture, signature électronique, relances, diagnostic de
pathologie du bâtiment et estimation de main d'œuvre ne sont plus exclus définitivement ; ils
deviennent des **pistes d'extension au-delà du devis**, à explorer après la V1. Restent écartés :
comparaison multi-critères, substitutions, alertes promo proactives, liste de courses.

### D-11 — Canal unique : web
*Modifiée par l'auteur du projet* : le SMS sort entièrement du projet, y compris comme capacité du
modèle. Les exemples courts du dataset restent, comme réponses directes, sans format SMS.

### D-12 — Données de catalogue : structure réelle, valeurs simulées
Les catalogues des enseignes de bricolage sont protégés et ne peuvent pas être redistribués. On
conserve la **structure** d'un export réel (colonnes, défauts) et on **simule les valeurs**.
Les extraits bruts d'enseigne ne sont pas versionnés (`.gitignore`).
*Où* : `docs/donnees/CHAINE_DONNEES.md` §2.

### D-13 — Aucune valeur inventée, aucune ligne rejetée en silence
Règle de la chaîne de données : chaque ligne écartée est comptée avec son motif ; une valeur
absente reste vide et porte sa réserve. La colonne `qualite_correspondance` (`exacte`, `proxy`,
`absente`) interdit de prendre un proxy pour une mesure.

### D-14 — Services externes cantonnés
- **OCR** (devis image/PDF → Markdown) : API externe, jamais le modèle (gpt-oss est textuel).
- **Annuaire d'entreprises** (SIRET → mentions légales) : service externe intégré ; **ne
  revendique pas de compétence IA**.

### D-15 — Constat : l'orchestration est écrite à la main
Le cadrage annonçait un framework d'agents (LangChain « ou équivalent ») ; il n'a jamais été
implémenté. Le pipeline STT → reformulation → modèle fine-tuné → code déterministe est du Python
simple (`app/pipeline.py`), avec des points de validation humaine (HITL-0, HITL-2).
La documentation décrit désormais ce que le code fait. Le **choix de la composante agentique**
du sprint 1 reste à écrire : voir Q-10.

### D-16 — La chaîne du modèle existe avant l'entraînement
Quatre étapes (`donnees` → `preparation` → `entrainement` → `validation`), trois états (`réussi`,
`échoué`, `ignoré`) : « pas encore lancé » n'est jamais « réussi », et l'entraînement ne simule
rien.

### D-17 — Pas de base de données tant que les déclencheurs ne sont pas atteints — *remplacée par D-33*
Persistance par fichiers. Les quatre déclencheurs de migration sont nommés dans
`docs/donnees/MODELE_DONNEES.md`.

### D-18 — Déploiement sur GCP, inférence par modèle hébergé
*Décidé le 12/10/2026 par l'auteur du projet. Remplace D-03 pour l'inférence.*
L'application est déployée sur GCP (Google Cloud Platform) et appelle un modèle hébergé par
API, au lieu d'un modèle servi en local.
*Raison* : le sprint 2 exige une URL de production où le LLM répond ; un modèle sur une machine
personnelle ne la tient pas.
*Coût assumé* : les dictées et les coordonnées des clients sortent de la machine — région
européenne, contrat de sous-traitance et registre RGPD à mettre à jour. Le client du modèle,
écrit pour Ollama en local, devient configurable.
*Précisée par* D-19 (persistance) et D-21 (service du modèle). *Reste ouvert* : le lieu du
fine-tuning (Q-13).
*Où* : `DOSSIER_SPRINT_1.md` §5 et §6.

### D-19 — Persistance des projets sur un bucket Cloud Storage monté en volume — *remplacée par D-33*
*Décidé le 12/10/2026.* Cloud Run efface son disque à chaque démarrage ; les projets, le profil
et le journal (fichiers JSON et JSONL) sont écrits sur un bucket Cloud Storage monté sur
`BTP_DONNEES`, avec **une instance Cloud Run au plus** pour éviter deux écritures concurrentes
sur le même fichier. Garde D-17 : pas de base de données.

### D-20 — La DGX Spark n'est plus disponible
*Constat du 12/10/2026.* L'auteur n'a plus accès à la machine. Ce qui en dépendait est repris :
inférence (D-21), modèle de démonstration 120b suspendu (D-04), lieu du fine-tuning (Q-13).

### D-21 — `gpt-oss-20b` servi par nous-mêmes sur Cloud Run avec GPU, en Europe — *ramenée au rang de candidat par D-25*
*Décidé le 12/10/2026.* Un second service Cloud Run, **privé**, exécute Ollama avec
`gpt-oss:20b` sur un GPU NVIDIA L4 (24 Go), région `europe-west1`. L'application l'appelle avec
une identité de service ; le service de modèle n'est pas joignable depuis Internet.
*Raison* : l'offre gérée de Vertex AI pour ce modèle n'est servie qu'aux États-Unis et est
retirée le 21/10/2026 (constaté le 12/10/2026) ; le 120b géré est traité aux États-Unis. Servir
nous-mêmes le 20b garde les données en Europe et garde **le même modèle, servi par le même
logiciel (Ollama), que la mesure de référence** (71,4 %) — la comparaison avec le fine-tuning
reste honnête, et le modèle fine-tuné s'y servira de la même façon.
*Coût assumé* : GPU payé à la seconde d'activité ; démarrage à froid lent (chargement d'environ
14 Go de poids) ; quota GPU à demander ; le client du modèle, câblé sur `localhost`, devient
configurable.

### D-22 — Le fine-tuning est la V2 — *remplacée par D-23*
*Décidé par l'auteur du projet.* La V1 fait fonctionner le parcours en production avec
`gpt-oss-20b` brut. Le jeu de test écrit à la main, le dataset et le fine-tuning forment la V2 ;
le modèle fine-tuné remplacera le modèle brut dans le même service, sans changer le code de la V1.

### D-23 — La V1 améliore le prompt, évalué ; le fine-tuning devient une V2 potentielle
*Décidé par l'auteur du projet, après l'atelier croisé n°1.* Le prompt devient un artefact
versionné ; chaque version est évaluée sur le jeu de test écrit à la main (D-05) et ne part en
production que si elle fait mieux que la précédente. La sortie du modèle est contrainte au
schéma JSON. La référence reste `gpt-oss-20b` brut à 71,4 % de JSON conforme.
*Raison* : la remarque de l'atelier — « au lieu d'entraîner, on peut versionner le prompt et
les données ». Une sortie contrainte et un prompt mesuré peuvent atteindre l'objectif de
fiabilité sans le coût d'un entraînement, ni d'une machine pour le faire.
Le fine-tuning n'est engagé, en V2, que si l'évaluation montre que le prompt plafonne.
*Conséquences* : Q-06, Q-07, Q-08 et Q-13 sont reportées à cette V2 potentielle ; la chaîne du
modèle (`mlops/`) gagne une étape d'évaluation de prompt.

### D-24 — La connaissance métier vient d'un corpus technique interrogé (RAG)
*Décidé par l'auteur du projet.* Rendements, taux de chute, règles de pose et de TVA viennent
d'un corpus de documentation technique (fiches fabricants, documentation métier), collecté en
une fois ou par scraping, indexé et interrogé avant chaque appel au modèle. Les réponses citent
leurs sources ; sous un seuil de pertinence, l'agent refuse plutôt que d'inventer.
*Raison* : un référentiel écrit par le LLM n'a pas de source ; la consigne du sprint 3 exige de
citer ses sources et de refuser hors corpus.
*Reste ouvert* : outil d'index et modèle d'embeddings (Q-15), liste des sources et leurs
licences.

### D-25 — Le modèle est choisi par un benchmark de qualité, latence et coût
*Décidé par l'auteur du projet, après l'atelier croisé n°1.* Aucun modèle n'est fixé avant
mesure. Au jour 1 de la V1, les candidats passent deux filtres éliminatoires (données traitées
dans l'Union européenne, sortie contrainte par un schéma JSON), puis sont mesurés sur le jeu de
test initial : qualité, latence p95 (démarrage à froid compris), coût par devis. Est retenu le
moins cher parmi ceux qui passent les seuils de qualité et de latence. `gpt-oss-20b` (71,4 % de
JSON conforme brut) sert de référence. *Où* : `DOSSIER_SPRINT_1.md` §6.C.1.

### D-26 — Gabarit hiérarchique du devis, corrigeable à la voix
*Décidé par l'auteur du projet.* Le devis suit cinq niveaux numérotés — devis, pièce, lot, ligne,
case — affichés à l'écran et dans l'export. L'artisan désigne une case à la voix (« salon,
peinture, ligne deux : quarante-huit mètres carrés ») ; le modèle traduit la phrase en adresse et
en valeur, avec une nouvelle intention `correction` dans le schéma de sortie (extension de D-02) ;
le code vérifie l'adresse, relit la modification à l'artisan, puis l'applique et recalcule.
*Où* : `DOSSIER_SPRINT_1.md` §6.C.3.

### D-27 — Le prix vient de quatre sources nommées, jamais du modèle
*Décidé par l'auteur du projet.* Le prix et le conditionnement d'une ligne viennent de la saisie
de l'artisan (clavier ou voix), de ses prix habituels, du catalogue, ou d'un document du corpus.
Un prix documentaire est extrait par le code à l'ingestion, cité, et marqué « à confirmer ». Sans
source, la ligne reste « prix à saisir » et l'export est bloqué. L'ordre de priorité est une
proposition (Q-17). *Où* : `DOSSIER_SPRINT_1.md` §6.C.2.

### D-28 — La dictée n'est pas relue par l'artisan
*Décidé par l'auteur du projet.* L'agent prend la dictée telle quelle, en reformule lui-même
l'intention et le message, et poursuit sans demander de relecture : la validation systématique
de la transcription (HITL-0) est retirée du parcours. Le garde-fou numérique reste, automatique :
si la reformulation change un nombre ou une unité, l'agent travaille sur le texte dicté et
l'écart est journalisé. L'artisan n'intervient plus que pour répondre aux questions et valider
la structure. **Règle** : une question de l'agent vérifie ou confirme quelque chose qu'il a
produit (une structure, une modification à appliquer), jamais le point de départ. *Conséquence* : le signal qualité n'a plus qu'un point de capture humain, la
correction du devis ; le code de relecture (`app/transcription.py`, US-05) est à adapter.

### D-29 — Un référentiel ouvert : les ouvrages inconnus deviennent des lignes génériques
*Décidé par l'auteur du projet.* Le référentiel n'est plus une liste fermée qui rejette ce qu'elle
ne connaît pas. Un ouvrage absent devient une **proposition générique grisée** (D-31), sans rendement
ni chute inventés, que l'artisan peut affiner plus tard avec un produit référencé. Toute demande
qui relève d'un devis est acceptée, même hors des quatre corps de métier pilotes ; le garde-fou
d'entrée ne filtre plus que les injections et les demandes sans rapport avec un devis.
**Vocabulaire** : un *lot* est un corps de métier du devis ; un *ouvrage* est une prestation
élémentaire du référentiel (le `lot_code` du code actuel, à renommer) ; une *ligne* est un
ouvrage posé dans le devis.

### D-30 — La session ne s'arrête jamais sur un échec, et l'agent itère par lot
*Décidé par l'auteur du projet.* Après une sortie invalide et une reprise, l'agent dit ce qu'il
n'a pas compris et redemande ; l'échec est compté dans `/metriques` sans interrompre l'artisan.
L'agent découpe le chantier en lots et fait autant de tours que nécessaire sur chacun avant de
passer au suivant. Un passage du corpus manquant ne bloque pas la construction du devis : la
ligne est marquée « non sourcé » ; seule une question technique hors corpus reçoit « je ne sais
pas ». *Où* : `DOSSIER_SPRINT_1.md` §4.B.

### D-31 — L'application est un copilote : l'agent pré-remplit, l'artisan édite, « Générer » chiffre
*Décidé par l'auteur du projet.* L'agent pré-remplit le devis en suggestions grisées ; l'artisan
accepte, modifie, supprime ou ajoute des blocs, au clic ou à la voix, grâce à des boutons sur
chaque lot et chaque ligne. Le bouton « Générer » complète les vides, résout les prix et calcule ;
aucun prix n'apparaît avant. Un ouvrage inconnu devient une proposition générique grisée (précise
D-29). Une suggestion non revue peut être chiffrée mais bloque l'export tant que l'artisan ne l'a
pas acceptée. Remplace l'étape de « validation de la structure » par l'édition suivie de
« Générer ». *Où* : `DOSSIER_SPRINT_1.md` §1.C, §4.B, §6.C.4.

### D-32 — L'observabilité du modèle passe par Langfuse
*Décidé par l'auteur du projet.* Chaque tour de l'agent est tracé dans Langfuse : version de
prompt, modèle, passages du corpus, latence, coût, scores d'évaluation. Les prompts versionnés y
sont publiés, ce qui relie toute mesure au prompt qui l'a produite. Cloud Logging garde les
journaux d'infrastructure. *Coût assumé* : un sous-traitant de plus ; région UE et masquage des
données personnelles avant envoi des traces. Hébergement Cloud ou auto-hébergé : Q-19.

### D-33 — Une seule base PostgreSQL avec pgvector
*Décidé par l'auteur du projet.* Catalogue, ouvrages du référentiel, projets, devis, profil,
corpus technique et ses vecteurs vivent dans **une seule base PostgreSQL avec l'extension
pgvector**, sur Cloud SQL en `europe-west1`. Remplace la persistance par fichiers (D-17), le
bucket monté (D-19) et l'index SQLite envisagé (Q-15). *Raison* : un seul magasin pour le
relationnel et la recherche vectorielle, des jointures directes entre un passage, sa source et un
ouvrage, et plus de fichier sur un disque que Cloud Run efface. *Conséquence* : le modèle logique
de `docs/donnees/MODELE_DONNEES.md` cesse d'être une simple cible ; l'écart du signal qualité
avec le bucket monté (RGPD, point 8) disparaît.

### D-34 — Stratégie Git : GitHub Flow avec versions étiquetées
*Décidé après l'atelier croisé n°1.* `main` protégée et toujours livrable ; branches courtes
(`feat/`, `fix/`, `prompt/`, `docs/`, `hotfix/`) fusionnées par pull request en squash ;
versions de production par étiquette `vX.Y.Z` avec approbation manuelle. Trois chaînes : pull
request (contrôles, évaluation sur le vrai modèle si un prompt change, prévisualisation), fusion
(image unique, recette), étiquette (même image, déploiement progressif, retour arrière
automatique sur signaux). GitFlow est écarté (trop lourd pour une personne), le trunk-based pur
aussi (plus de contrôle avant `main`). *Où* : `DOSSIER_SPRINT_1.md` §6.B.

### D-35 — Plusieurs artisans, chacun avec ses projets
*Décidé par l'auteur du projet.* L'application sert plusieurs artisans en même temps, chacun avec
ses propres projets de devis, isolés des autres. Remplace l'hypothèse « un artisan par instance ».
*Conséquences* : un compte par artisan au lieu d'une phrase de passe partagée ; chaque accès aux
données filtre sur l'artisan connecté (le défaut vu dans Velmo2, des outils sans contrôle de
propriété, est à éviter) ; Cloud Run peut tourner sur plusieurs instances puisque l'état vit dans
PostgreSQL (D-33) ; le trafic réel rend possibles les expositions progressives. Mode
d'identification : Q-20.

### D-36 — *Reportée en V1.1 par D-38.* Le modèle d'embeddings est déployé sur Azure AI Foundry
*Décidé par l'auteur du projet.* Les passages du corpus et les requêtes de recherche sont
vectorisés par un modèle d'embeddings déployé sur Azure AI Foundry ; les vecteurs sont stockés
dans pgvector (D-33). Tranche le fournisseur de Q-15 ; restent le modèle précis et sa région.
*Coût assumé* : un sous-traitant de plus, Microsoft Azure, à côté de Google Cloud et de Langfuse
— région UE à exiger au déploiement, contrat de sous-traitance, registre RGPD à mettre à jour,
aucune coordonnée de client dans les textes envoyés à vectoriser.
*Où* : `DOSSIER_SPRINT_1.md` §5.A, §6.A (niveau 2) et §8.B.

### D-37 — Mémoire courte de 30 tours, mémoire longue tenue par un LLM juge
*Décidé par l'auteur du projet.* La mémoire de l'agent vit dans la même base PostgreSQL +
pgvector que le corpus, portée par le même module que la recherche (RAG) :
- **mémoire courte** : les 30 derniers tours de la conversation ;
- **mémoire longue** : une fiche des préférences de l'artisan, enrichie par un LLM juge qui se
  déclenche tous les 15 tours, **en parallèle**, sans bloquer la conversation ;
- chaque **projet de devis** porte ses métadonnées, des **commentaires système** laissés par
  l'agent quand il reprend le devis, pour savoir où en est le travail, et les **commentaires de
  l'artisan**.

À chaque tour, l'agent charge la fiche des préférences, la mémoire courte et les données du
projet, puis les passages du corpus.
*Raison* : reprendre un devis sans refaire la conversation, et ne pas redemander à l'artisan ce
qu'il a déjà dit.
*Coût assumé* : la fiche des préférences est une donnée personnelle — l'artisan peut la voir, la
corriger, la supprimer ; un appel au modèle de plus tous les 15 tours. Conservation et contenu
envoyé au juge : Q-21. *Où* : `DOSSIER_SPRINT_1.md` §6.C.5 et §5.A.

### D-38 — La V1 est resserrée sur six jours ; le reste passe en V1.1
*Décidé par l'auteur du projet, après une auto-évaluation sur la grille de l'atelier n°1.* Passent
en **V1.1**, déjà conçus mais livrés après les six jours : la mémoire longue et son LLM juge, la
correction à la voix (en V1 : édition au clic), les prix habituels et documentaires (en V1 :
catalogue et saisie de l'artisan), le déploiement progressif (en V1 : bascule et retour arrière),
les embeddings sur Azure (en V1 : un seul cloud, GCP). Restent en V1 : la mémoire courte, les
comptes artisans isolés, le benchmark, le RAG, l'évaluation du prompt, l'écran copilote.
*Raison* : rendre le périmètre tenable et ramener la stack à un seul élément exotique.

## Historique — décisions remplacées

### H-01 — RenoAssistant (SMS + promotions), abandonné le 28/07/2026
Matching de promotions Leroy Merlin par SMS (Twilio, pgvector, Redis, Gemma 4). Abandonné : le
blocage légal sur les données d'enseigne rendait la démonstration fragile, et le fine-tuning
n'y était pas le sujet. Les documents de cette conception ont été retirés du dépôt (ils restent
dans l'historique git).

### H-02 — Assistant Bricolage fine-tuné, remplacé le 16/08/2026 par D-07
Client final, saisie texte, devis interactif arbitré à deux, peinture et sols uniquement. Remplacé
par le pivot B2B vocal : un utilisateur professionnel, une entrée vocale, quatre corps de métier.

### H-03 — 100 % local sur DGX Spark, remplacé le 12/10/2026 par D-18, D-20 et D-21
Fine-tuning et inférence sur la DGX Spark (128 Go, 273 Go/s de bande passante) ; les données
métier ne quittent pas la machine.
*Raison* : confidentialité des chantiers et blocage légal sur les données d'enseigne (voir D-12).
*Corollaire matériel* : la vitesse de decode dépend des paramètres **actifs**, d'où MoE + FP4
(gpt-oss-120b : 52,9 tok/s ; dense 70B : 2,7 tok/s).
*Tension non tranchée* : le STT, voir Q-03.

## Questions ouvertes — non arbitrées

Elles appartiennent à l'auteur du projet.

- **Q-01 — Un modèle ou deux** pour la reformulation promptée et la génération JSON fine-tunée ?
  À trancher sur mesures réelles sur le GPU L4 (24 Go) du service de modèle.
- **Q-02 — Quel modèle de reformulation** après le STT ? Non bloquant.
- **Q-03 — Où transcrire la voix ?** Un modèle de transcription (Whisper, Parakeet) servi par
  nous sur GCP, ou une API distante (Gladia). Depuis D-18, l'argument du « tout local » ne tient
  plus ; restent la région des données, le coût et la qualité sur une dictée de chantier.
  `docs/modele/BENCHMARK_STT.md` instruit, ne tranche pas ; son protocole de mesure (§8) n'a pas tourné.
- **Q-04 — Fallback de modèle.** Un seul service GPU est un point de défaillance unique. Chaîne
  envisagée : 20b fine-tuné → 20b brut promptté → refus explicite. À décider :
  où vit la bascule (probablement dans l'API), le recours distant est exclu par défaut, un JSON
  invalide ne doit **pas** déclencher la bascule tant que la métrique nº 1 n'est pas mesurée, et
  chaque bascule est journalisée. Deux modèles de 14 Go ne tiennent pas ensemble sur un L4 de
  24 Go : le secours suppose un second service.
- **Q-05 — Analytique d'usage** de l'application. Aucun candidat n'est engagé ; vérifier qu'un
  outil d'analytique respecte la région européenne de D-21.
- **Q-06 — Tester un autre modèle de base** Reportée à la V2 potentielle (D-23).
- **Q-07 — Hyperparamètres du LoRA.** Reportée à la V2 potentielle (D-23).
- **Q-08 — GRPO en seconde passe** Reportée à la V2 potentielle (D-23).
- **Q-09 — Second cercle** (question technique, arbitrage budget, recommandation produit) : entre-t-il
  dans le périmètre ? Saute en second, après le 120b.
- **Q-10 — Composante agentique majeure** du parcours (sprint 1). Proposée dans
  `DOSSIER_SPRINT_1.md` §4 : workflow orchestré avec humain dans la boucle. Reste à l'aligner sur
  l'intitulé du menu du dispositif et à la faire valider.
- ~~**Q-11 — Le fine-tuning est-il hors de la V1 ?**~~ Tranchée par D-22.
- ~~**Q-12 — Comment servir `gpt-oss-20b` ?**~~ Tranchée par D-21.
- **Q-13 — Où s'entraîne le modèle fine-tuné ?** Reportée à la V2 potentielle (D-23).
- **Q-14 — Les anciens devis et factures de l'artisan, y compris papier, comme source.** Pour
  le jeu de test, ou comme exemples injectés dans le prompt. À compléter : volume, numérisation
  (OCR), pseudonymisation des clients avant tout usage.
- **Q-15 — Quel modèle d'embeddings ?** L'index est tranché par D-33 (pgvector), le fournisseur
  par D-36 (Azure AI Foundry). Reste le modèle précis, multilingue, à mesurer sur les questions
  de démonstration, et sa région UE de déploiement.
- **Q-16 — La liste des modèles candidats au benchmark.** Proposition : `gpt-oss-20b`
  auto-hébergé, un modèle Gemini sur Vertex AI en région européenne, un modèle Mistral, `gpt-oss`
  sur Azure AI Foundry en zone de données UE. Disponibilité et région de chacun à vérifier.
- **Q-17 — L'ordre de priorité des sources de prix.** Proposition : saisie de l'artisan, prix
  habituel, catalogue, document du corpus.
- **Q-18 — Segmentation de la voix (V2 potentielle).** Séparer les locuteurs d'un enregistrement
  pour ne garder que la voix de l'artisan quand d'autres voix le polluent. Réserve : identifier
  l'artisan par son empreinte vocale est une donnée biométrique (RGPD, article 9) ; une séparation
  sans identification est à privilégier.
- **Q-19 — Langfuse en service géré ou auto-hébergé ?** Proposition : Langfuse Cloud en région UE
  pour la V1, rien à administrer ; auto-hébergé sur GCP si les traces ne doivent pas sortir du
  projet.
- **Q-20 — Comment un artisan s'identifie-t-il ?** Lien de connexion par courriel, compte Google,
  ou accès « visiteur » sans compte pour la démonstration. Le choix change la liste des données
  personnelles et le registre RGPD.
- **Q-21 — La fiche des préférences de l'artisan face au RGPD.** Combien de temps la conserver,
  et que devient-elle quand le compte est fermé ? Comment l'artisan exerce-t-il son droit de
  regard : la voir, la corriger, la supprimer, depuis quel écran ? Et que reçoit le LLM juge :
  les 15 derniers tours bruts, ou un extrait débarrassé des coordonnées des clients ? (D-37)
