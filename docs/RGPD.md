# Protection des données personnelles

Ce document tient le **registre des traitements** du produit, les **procédures de tri**
appliquées aux données collectées, et le **détail des opérations avec leur fréquence**.

Il est écrit **depuis le code**, pas depuis un modèle type : chaque donnée listée ci-dessous
a été retrouvée dans un module, et la ligne de code est citée. Ce qui n'est **pas** encore
implémenté est marqué comme tel plutôt que décrit au futur — un registre qui décrit des
mesures inexistantes est pire qu'un registre absent, parce qu'il donne à croire que la
question a été traitée.

## Pourquoi ce document est dû

Le produit n'est pas un exercice sans données : il **collecte des données personnelles de
personnes qui ne sont pas ses utilisateurs**. Le client final n'a ni compte ni écran
(`CLAUDE.md`, périmètre du noyau de démo), mais son nom et l'adresse de son chantier sont
saisis, parce que les mentions obligatoires d'un devis BTP les exigent. Il est donc une
*personne concernée* au sens du RGPD sans jamais être un utilisateur — c'est précisément
la situation où l'on oublie de le compter.

S'y ajoute la voix de l'artisan, qui est une donnée personnelle en elle-même, et dont le
contenu porte les noms de ses clients.

## Rôles

| Rôle | Qui | Remarque |
|---|---|---|
| Responsable de traitement | L'entreprise artisanale qui exploite l'application | C'est elle qui décide des finalités : le produit tourne sur sa machine |
| Sous-traitant | **Un seul** : le service d'OCR de T5, et seulement si l'artisan dépose un ancien devis. Plus la réserve du navigateur (voir plus bas) | Le fine-tuning et l'inférence restent locaux ; l'annuaire d'entreprises interrogé en US-01 ne reçoit qu'un SIRET, et ne reçoit rien du chantier |
| Personnes concernées | L'artisan (utilisateur), le client final (non-utilisateur) | Deux catégories, deux régimes d'information |

En phase de soutenance, les données manipulées sont **simulées** : le catalogue porte une
structure réelle et des valeurs inventées (`docs/SOURCES_DONNEES.md`), et les clients des
jeux d'essai sont fictifs. Cela ne change pas le registre — il décrit ce que le code *fait*,
pas ce qu'il contient aujourd'hui.

## Registre des traitements

Cinq traitements, dont quatre portent des données personnelles au sens strict et un porte
une donnée technique identifiante (l'adresse IP). Le cinquième est le seul du produit à
faire sortir des données personnelles de la machine, et il est facultatif.

### T1 — Établissement du devis

| Rubrique | Contenu |
|---|---|
| Finalité | Produire un devis conforme aux mentions obligatoires du BTP |
| Base légale | Exécution de mesures précontractuelles à la demande de la personne (art. 6.1.b) |
| Personnes concernées | Le client final ; l'artisan pour ses propres mentions légales |
| Données — client | Nom, adresse du chantier (`app/profil.py`, classe `Client`) |
| Données — artisan | Raison sociale, SIRET, adresse, RCS, code APE/NAF, TVA intracommunautaire, régime de TVA, assureur et numéro de contrat décennale (`app/profil.py`) |
| Source | Saisie par l'artisan, ou dictée puis relue en HITL-0 |
| Destinataires | L'artisan seul ; le client reçoit le devis exporté en `.docx` |
| Transferts hors UE | Aucun |
| Stockage | Un fichier JSON par projet sous `donnees/`, en clair (`app/persistance.py:29`) |
| Conservation | **Non implémentée.** Voir « Ce qui manque » |
| Sécurité | Accès derrière phrase de passe unique, jeton HMAC de 12 h, cookie `httponly` + `samesite=strict` (`app/authentification.py`) ; identifiant de projet en liste blanche stricte, qui interdit toute remontée d'arborescence (`app/persistance.py:33`) |

### T2 — Dictée vocale et relecture

| Rubrique | Contenu |
|---|---|
| Finalité | Permettre la saisie sur chantier, mains occupées, puis relire avant traitement (HITL-0) |
| Base légale | Intérêt légitime de l'artisan à saisir son devis oralement |
| Personnes concernées | L'artisan ; incidemment le client, dont le nom est prononcé |
| Données | Signal vocal, puis texte de la dictée brute et texte proposé à la relecture |
| Destinataires | Le modèle de relecture, exécuté localement sur Ollama (`app/transcription.py`) |
| Transferts hors UE | Aucun quand la transcription se fait sur l'appareil ; sinon, sur accord explicite de l'artisan seulement — voir la réserve ci-dessous |
| Conservation | L'audio n'est jamais écrit sur disque ; la dictée textuelle vit dans la session du projet |
| Sécurité | Le modèle de relecture est prompté, jamais fine-tuné, et un contrôle déterministe rejette sa proposition si un chiffre ou une unité a bougé |

> **Réserve, et elle était sérieuse.** La dictée du prototype passe par la *Web Speech API*
> du navigateur. Contrairement à ce que son nom laisse croire, cette interface **ne transcrit
> pas dans le navigateur** : par défaut Chrome envoie l'audio à un service Google, Safari au
> sien. La voix de l'artisan et les noms de clients qu'elle porte quittaient donc la machine,
> ce qui contredisait frontalement l'engagement « 100 % local » du cadrage. Le bouton portait
> la mention « prototype navigateur », ce qui n'est pas une mesure de protection.
>
> **Corrigé le 08/09/2026** (`app/static/index.html`, bloc de dictée) : le front réclame
> `processLocally`, l'option introduite par Chrome 139 qui garde la transcription sur
> l'appareil. Quand le navigateur ne sait pas le faire, ou quand le paquet de langue
> française manque, **il n'y a pas de repli silencieux** : l'application nomme ce qui sortirait
> de la machine et demande un accord explicite, refusable — l'artisan fait autorité, y compris
> sur ce qu'il accepte d'envoyer. Deux tests tiennent la propriété
> (`tests/test_front.py`), dont un qui interdit un second point de démarrage de la
> reconnaissance, lequel contournerait la demande d'accord.
>
> La dictée locale d'US-04 (Whisper sur la machine) reste ce qui rendra la question sans
> objet. D'ici là, l'accord distant est un choix éclairé, pas un défaut.

### T3 — Signal qualité et réentraînement

| Rubrique | Contenu |
|---|---|
| Finalité | Faire des corrections de l'artisan la matière première du réentraînement (US-25) |
| Base légale | Intérêt légitime — améliorer un outil professionnel à partir de ses propres corrections |
| Personnes concernées | L'artisan ; le client, présent dans le texte des dictées |
| Données | Le triplet exigé par la story : ce que l'artisan a fourni, ce que la chaîne a produit, ce que l'artisan a retenu (`app/boucle_qualite.py`) |
| Destinataires | Personne. Le fichier ne sert qu'à l'entraînement local |
| Transferts hors UE | Aucun, et le code le fait respecter |
| Stockage | `~/.local/share/the-project/signal_qualite.jsonl`, **hors du dépôt** (`app/boucle_qualite.py:49`) |
| Conservation | Sans limite par construction : l'export est en ajout seul et le jeu ne rétrécit jamais |
| Sécurité | La destination est vérifiée avant écriture : ni URL, ni chemin UNC, ni système de fichiers synchronisé ou réseau — la liste `FS_NON_LOCAUX` couvre NFS, CIFS, sshfs, rclone, davfs, s3fs, gcsfuse. Une destination dans le dépôt est **refusée**, parce que le dépôt est monté en `fuse.rclone` vers OneDrive |

### T4 — Journalisation technique et sécurité

| Rubrique | Contenu |
|---|---|
| Finalité | Mesurer les seuils du §4.3 et détecter les tentatives d'accès (OWASP A09) |
| Base légale | Intérêt légitime — sécurité du système d'information |
| Personnes concernées | Quiconque appelle l'application, y compris sans y être autorisé |
| Données | Horodatage, type d'événement, intention, code de lot, latence, et **l'adresse IP d'origine sur échec d'authentification** (`app/main.py:98`, `app/authentification.py:176`) |
| Destinataires | L'artisan, via `/api/metriques` |
| Transferts hors UE | Aucun |
| Stockage | `donnees/journal.jsonl` (`app/observabilite.py:60`) |
| Conservation | **Non implémentée.** La CNIL recommande six mois pour des journaux de sécurité |
| Sécurité | Le journal ne porte **aucun texte libre** : `correction_artisan` n'enregistre que son origine et le code de lot, jamais la dictée elle-même. C'est une propriété voulue, pas un hasard — la dictée est dans le signal qualité, qui a son propre garde-fou de destination |

### T5 — Reprise de mise en page depuis un ancien devis (US-03)

**Le seul traitement du produit qui envoie des données personnelles à un tiers.** Il est
facultatif, déclenché par un geste explicite de l'artisan, et annoncé avant le dépôt.

| Rubrique | Contenu |
|---|---|
| Finalité | Reprendre l'ordre des sections et les intitulés d'usage de l'artisan, pour que les devis produits ressemblent aux siens |
| Base légale | Intérêt légitime de l'artisan — l'adoption de l'outil tient à ce détail. L'alternative est le gabarit par défaut, complet et conforme : le traitement est donc évitable |
| Personnes concernées | **Un client antérieur de l'artisan**, qui n'est ni utilisateur, ni informé, ni partie à ce chantier — c'est ce qui rend ce traitement le plus délicat du registre |
| Données transmises | Le fichier déposé **tel quel** : PDF ou photo d'un ancien devis, donc le nom et l'adresse de ce client, les montants, le numéro de contrat décennale de l'artisan (`app/gabarit.py`, `_transport_http`) |
| Données conservées | **Rien du fichier.** Le gabarit ne retient que des clés du dictionnaire `BLOCS` de `app/gabarit.py` et lequel de *nos propres* synonymes déclarés chacune a reconnu. Aucune chaîne du document n'atteint le profil, le disque ou le navigateur |
| Source | Dépôt manuel par l'artisan |
| Destinataires | Le service d'OCR, le temps de l'appel. Personne d'autre |
| Transferts hors UE | **Possibles**, selon le service retenu. À vérifier avant toute exploitation réelle : c'est le point à instruire de ce traitement |
| Stockage | Le champ `gabarit` du profil (`app/persistance.py`) : une liste de clés et une table de synonymes, tous issus de notre propre vocabulaire |
| Conservation | Tant que le profil vit. **Révocable à tout moment** : `DELETE /api/profil/gabarit`, exposé par un bouton de l'écran de profil |
| Sécurité | Type et taille vérifiés **avant** tout appel, sur les octets de tête et non sur l'extension : un fichier qu'on sait refuser ne sort jamais de la machine. La clé d'API ne quitte pas le serveur — le navigateur ignore jusqu'au nom du service. Le journal ne porte que le motif, jamais le nom du fichier ni son contenu |

**Ce que ce traitement écarte volontairement, et pourquoi.** Le Markdown rendu par l'OCR
contient tout l'ancien devis. Le retenir, même « pour améliorer la reconnaissance », ferait
entrer dans le produit les données d'un tiers qui n'a consenti à rien et dont l'artisan
n'a plus forcément de relation contractuelle. La contrainte est donc posée dans le code
plutôt que dans une intention : `vocabulaire()` énumère l'intégralité de ce qu'un gabarit
peut contenir, un test l'exige mot à mot sur un devis truffé de données personnelles, et
la relecture depuis le disque revalide le même vocabulaire — un fichier de profil édité à
la main ne peut pas y faire entrer autre chose.

## Procédures de tri

Le tri se fait à trois moments distincts, et chacun a une règle qui lui est propre.

### Tri à la collecte — ce qui n'entre pas

- **Le client n'a pas de compte.** Pas d'identifiant, pas de mot de passe, pas d'adresse
  électronique, pas de numéro de téléphone. Seul entre ce qu'une mention obligatoire exige.
- **La mémoire de l'agent ne porte pas le client.** « Le client n'apparaît en mémoire agent
  que par le nécessaire » (`docs/DISPOSITIF_AGENT.md` §5) ; les données personnelles non
  sollicitées sont « non stockées, non répétées en sortie » (même document, tableau des
  garde-fous).
- **L'audio n'est pas conservé.** Seul le texte issu de la dictée l'est, après relecture.
- **Le devis déposé pour en tirer un gabarit n'est pas conservé** — ni le fichier, ni le
  texte que l'OCR en tire, ni aucun fragment. Voir T5 : c'est le tri le plus strict du
  produit, parce que la personne concernée n'est pas celle qui dépose.
- **La phrase de passe n'est jamais stockée en clair**, ni journalisée quand elle est fausse :
  l'environnement ne porte que son empreinte scrypt (`app/authentification.py`).

### Tri avant réutilisation — ce qui ne part pas à l'entraînement

Un candidat du signal qualité porte une dictée brute, donc potentiellement un nom et une
adresse. Deux règles, dont **une seule est aujourd'hui tenue par le code** :

| Règle | État |
|---|---|
| La destination reste locale, vérifiée avant écriture | **Tenue par le code** (`verifier_destination`) |
| Les noms et adresses sont remplacés par des marqueurs avant versement au jeu d'entraînement | **À faire** — voir « Ce qui manque » |

La seconde règle est celle qui compte pour le RGPD : un jeu d'entraînement se relit, se
copie et survit à tout le reste. Un devis effacé dont le nom du client subsiste dans le
dataset n'est pas effacé.

### Tri à la sortie — ce qui ne s'affiche pas

Le devis exporté porte les mentions obligatoires, donc le nom et l'adresse du chantier :
c'est sa raison d'être. En revanche, le tableau de bord des métriques n'expose que des
compteurs et des latences — aucun contenu de projet ne transite par `/api/metriques`.

## Détail des opérations et leur fréquence

| Opération | Déclencheur | Fréquence | Trace |
|---|---|---|---|
| Saisie du profil et du client | L'artisan ouvre un projet | Une fois par chantier | `donnees/<projet>.json` |
| Dictée et relecture (HITL-0) | L'artisan dicte | Plusieurs fois par chantier | En session, puis dans le projet |
| Appel au modèle | Chaque tour de conversation | Plusieurs fois par dictée | `journal.jsonl`, sans texte libre |
| Écriture du projet sur disque | Fin de chaque tour | À chaque tour | Le fichier du projet |
| Dépôt d'un ancien devis pour en tirer un gabarit | Geste explicite de l'artisan | Facultatif, une fois par artisan en pratique | `journal.jsonl`, motif seul — ni nom de fichier, ni contenu |
| Export du devis en `.docx` | L'artisan exporte | Une à quelques fois par chantier | Fichier remis au client |
| Versement au signal qualité | Correction de l'artisan | À chaque correction | `signal_qualite.jsonl`, hors dépôt |
| Réentraînement à partir du signal | Décision de l'artisan | Rythme visé : hebdomadaire, non automatisé | Jeu de données local |
| Purge des projets clos | — | **Aucune. À implémenter** | — |
| Purge des journaux | — | **Aucune. À implémenter** | — |

## Droits des personnes

Aucun de ces droits n'a d'interface aujourd'hui ; tous sont exerçables à la main, et c'est
ce que le registre doit dire.

| Droit | Comment il s'exerce aujourd'hui |
|---|---|
| Accès | Lire le fichier JSON du projet — il est en clair et lisible à l'œil |
| Rectification | L'artisan corrige dans l'application ; la correction est journalisée comme signal qualité |
| Effacement | Supprimer le fichier du projet. **Incomplet** : le signal qualité, lui, ne rétrécit jamais. Le gabarit de T5, en revanche, s'efface d'un bouton |
| Opposition | Ne pas utiliser l'application pour ce chantier |
| Information | **Non fait.** Le client final n'est informé de rien : il reçoit un devis, pas une notice |

## Ce qui manque

Cette section est la partie utile du document. Elle est écrite comme une liste de travaux,
avec le motif de chacun.

1. **Aucune durée de conservation n'est implémentée.** Ni pour les projets, ni pour le
   journal. C'est le manquement le plus visible : le registre annonce des durées qu'aucun
   code n'applique. Deux purges à écrire, l'une sur `donnees/*.json`, l'autre sur
   `journal.jsonl`, avec des durées à arbitrer (proposition : projets, durée de la garantie
   décennale imposée par la nature du document ; journaux, six mois).
2. **Le tri avant entraînement n'existe pas.** Les candidats partent avec les noms dedans.
   Une passe de pseudonymisation est à écrire dans `app/boucle_qualite.py`, avant export.
3. **La dictée locale reste à faire pour de bon.** La réserve de T2 est désormais encadrée —
   traitement sur l'appareil réclamé, accord explicite sinon — mais un navigateur sans
   `processLocally` laisse toujours le choix d'envoyer l'audio dehors. Seul Whisper local
   (US-04) supprime l'option.
4. **Le client final n'est pas informé.** Une mention d'une phrase au bas du devis suffirait
   à couvrir l'article 14, en nommant le responsable de traitement et la finalité.
5. **`donnees/` est dans le dépôt, qui est synchronisé vers OneDrive.** Le code interdit cette
   destination au signal qualité (`FS_NON_LOCAUX`), mais ne l'applique **pas** aux projets ni au
   journal, qui atterrissent par défaut dans le dépôt. Le contournement existe déjà — la
   variable d'environnement `BTP_DONNEES` déplace la racine — mais le défaut, lui, expose des
   noms et des adresses de clients à une synchronisation dans le nuage.
   **Arbitrage laissé à l'artisan** : changer le défaut, ou documenter `BTP_DONNEES` comme
   obligatoire en exploitation.
6. **Le sous-traitant de T5 n'est pas encadré.** Aucun contrat de sous-traitance (art. 28),
   aucune vérification de la localisation des traitements, aucune durée de rétention connue
   côté service. Tant que `BTP_OCR_CLE` n'est pas configurée, le produit ne transmet rien et
   la lacune est théorique ; le jour où elle l'est, ces trois points sont un préalable, pas
   une formalité. C'est aussi le motif pour lequel le dépôt reste **facultatif** et le
   gabarit par défaut **complet**.
7. **Aucune analyse d'impact (AIPD) n'a été menée.** Elle n'est vraisemblablement pas requise
   — ni données sensibles, ni surveillance systématique, ni grande échelle — mais l'absence
   de traitement de la question est elle-même une lacune. Une demi-page de justification suffit.

## Ce que ce document ne fait pas

Il ne remplace pas les mentions obligatoires du devis, qui relèvent du droit de la
consommation et du BTP, pas du RGPD (`docs/CADRAGE_MODELE.md`). Et il ne prétend pas à la
conformité : il décrit un état, dont une partie est en défaut, et il nomme les travaux qui
la corrigeraient.
