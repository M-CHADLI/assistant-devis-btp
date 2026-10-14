# Rituels du projet — objectifs, modalités, destinataires

> Ce document énonce les rituels de conduite du projet : ce que chacun vise, qui
> y participe, ce qu'il produit et où cette production est consultable. Il répond
> au critère C16-117. Il ne décrit pas la méthode agile en général — il décrit
> **celle-ci**, avec ses adaptations et ce qu'elles coûtent.
>
> **Structure du document.** Titres hiérarchisés sans saut de niveau, tableaux
> avec ligne d'en-tête, aucune information portée par la seule couleur —
> conformément à `docs/exploitation/ACCESSIBILITE_DOCUMENTS.md`.

## Une difficulté à nommer d'abord

Ce projet est conduit par **une seule personne**, assistée d'un modèle. Les
rituels agiles ont été conçus pour une équipe : le daily sert à synchroniser des
gens qui travaillent en parallèle, la revue de sprint à confronter un
incrément à un client, la rétrospective à faire parler une équipe de ses
frictions. Aucun de ces mécanismes ne fonctionne tel quel à une personne.

Deux façons de traiter ce problème. La première est de tenir des rituels vides
pour pouvoir dire qu'ils sont tenus — un daily qu'on se récite à soi-même, une
rétrospective sans autre participant. C'est ce que le projet **refuse**, pour la
même raison qu'il refuse d'antidater des séances de veille : un rituel de façade
ne produit pas de décision, il produit une trace, et une trace sans décision ne
vaut rien devant un jury qui sait lire.

La seconde est de garder l'**objectif** de chaque rituel et d'en changer les
modalités pour qu'il produise vraiment quelque chose à cette échelle. C'est le
parti pris ci-dessous : chaque rituel dit ce qu'il vise, et **avec qui** il est
tenu — l'interlocuteur réel, pas un rôle imaginaire.

## Les parties prenantes

| Partie prenante | Rôle réel dans le projet | Ce qu'elle attend |
|---|---|---|
| L'apprenti (moi) | Conception, développement, décisions | Avancer sans perdre le fil du référentiel |
| Le tuteur entreprise | Contrôle de la pertinence métier et du rythme | Voir l'avancement et les points bloquants, tôt |
| L'organisme de formation | Suivi du référentiel de compétences | Preuve que les 21 compétences sont travaillées |
| Le jury de certification | Évaluation finale | Des livrables et des traces, pas des intentions |
| L'artisan témoin | Validation métier du référentiel et des devis | Que le produit dise vrai sur son métier |

L'artisan témoin n'est **pas** utilisateur du produit au sens du cadrage : il
n'a ni compte ni écran. Il intervient comme relecteur métier, et c'est à ce
titre qu'il figure ici.

## Les rituels

### Sprint de deux semaines

**Objectif.** Borner l'engagement. Sans borne, un projet de quatre mois se
consomme en explorations et découvre en novembre qu'il manque l'essentiel.

**Modalités.** Sept sprints de deux semaines, du 01/09 au 30/11/2026, alignés
sur les quatre jalons mensuels de `PLANNING.md`. Le contenu de chaque sprint est
tiré du backlog de `docs/produit/STORIES.md` selon les deux files de priorité — file 1
« ce qui se voit à la démonstration », file 2 « exigences de certification ».

**Production.** `docs/notion/sprints.csv`, et le tableau Notion une fois monté.

**Règle de périmètre.** Rien n'entre en cours de sprint. Un besoin découvert va
au backlog et attend l'arbitrage suivant — c'est la règle « plus rien n'entre
dans le périmètre » de `PLANNING.md`, appliquée à l'échelle de la quinzaine.

### Point d'avancement hebdomadaire avec le tuteur

**Objectif.** Ce que le daily vise dans une équipe — détecter tôt qu'on s'est
engagé dans une impasse — mais à la seule fréquence qui ait du sens ici.

**Modalités.** Une fois par semaine, environ trente minutes, avec le tuteur
entreprise. Trois points, dans cet ordre : ce qui est **fini** au sens de la
définition ci-dessous, ce qui est bloqué et depuis quand, ce qui est décidé
depuis la dernière fois.

**Production.** L'état du kanban au moment du point, plus les décisions ajoutées
au document de conception concerné. Une décision qui ne se retrouve pas dans
`docs/` n'a pas été prise.

### Revue de fin de sprint

**Objectif.** Confronter l'incrément à quelqu'un qui n'a pas participé à
l'écrire. C'est le seul rituel dont la valeur tient entièrement à la présence
d'un tiers.

**Modalités.** À la fin de chaque sprint, avec le tuteur, et avec l'artisan
témoin lorsque le sprint a touché au métier — référentiel, quantités,
consommables, mentions obligatoires. La démonstration se fait sur le produit qui
tourne, jamais sur des captures.

**Production.** Un compte rendu daté dans `docs/revues/`, sur le modèle des
comptes rendus de veille : ce qui a été montré, ce qui a été dit, ce qui est
décidé. Les corrections métier de l'artisan rejoignent le signal qualité
(US-25).

### Rétrospective de fin de sprint

**Objectif.** Corriger la façon de travailler, pas le produit.

**Modalités.** Immédiatement après la revue, quinze minutes, seul mais **écrit**
— c'est l'écriture qui remplace ici la parole des autres. Trois questions :
qu'est-ce qui a pris plus de temps que prévu et pourquoi, qu'est-ce qui a été
fait sans être demandé, qu'est-ce qui a été décidé sans être noté.

**Production.** Une section datée dans `docs/revues/`, et pour les défauts
techniques une entrée dans `docs/exploitation/INCIDENTS.md`, qui tient déjà ce rôle.

### Séance de veille hebdomadaire

**Objectif.** La compétence C6 du référentiel, et une raison de fond : le sujet
— fine-tuning MoE et Unsloth — bouge plus vite que le projet.

**Modalités.** Une heure le vendredi, cinq flux déclarés dans
`veille/sources.opml`, format imposé par `veille/GABARIT-SEANCE.md`. Chaque item
reçoit un verdict explicite : retenu, écarté, à surveiller.

**Production.** Un compte rendu par séance dans `veille/seances/`. Ce qui est
retenu se traduit en modification d'un document de conception ou en tâche du
backlog — sans quoi la veille n'est que de la lecture.

**État réel.** Une seule séance existe à ce jour (08/09/2026). La récurrence
attendue par le référentiel **n'est pas encore établie** ; c'est dit ici plutôt
que compensé.

## Ce qui compte comme fini

Un rituel qui ne partage pas la même définition de « fini » que le backlog
produit des désaccords à répétition. Celle du projet, valable pour toute story :

1. Le comportement est implémenté **et son cas dégradé aussi**.
2. Les critères d'accessibilité de la story sont satisfaits — ils sont au même
   rang que les critères fonctionnels, pas en option.
3. Des tests couvrent le nominal et le dégradé, et la suite est verte.
4. La ligne de traçabilité de la story dans `docs/produit/STORIES.md` est mise à jour
   avec l'état **constaté**, y compris ce qui reste.
5. Ce qui a été décidé en chemin est écrit dans le document de conception
   concerné.

Le point 4 est celui qu'on oublie, et c'est le seul qui permette de répondre
« où en est-on » sans relire le code.

## Comment ces rituels sont partagés

| Canal | Contenu | Destinataires |
|---|---|---|
| Tableau Notion (thème JIRA) | Backlog, sprints, tâches, kanban vivant | Tuteur, formation |
| Ce dépôt | Documents de conception, comptes rendus, incidents | Toutes, à la remise |
| Point hebdomadaire | Avancement, blocages, décisions | Tuteur |
| Revue de fin de sprint | Démonstration du produit qui tourne | Tuteur, artisan témoin |
| Dossier de certification | La synthèse des cinq livrables | Jury |

**Le tableau Notion n'est pas encore monté.** Le kit de transposition est prêt
(`docs/pilotage/NOTION_BOARD.md`, trois CSV, une CLI), et il attend un jeton
d'intégration plus le partage de la page racine. Tant que ce n'est pas fait, les
parties prenantes n'ont accès qu'au dépôt, ce qui suffit pour lire mais pas pour
suivre.

## Ce que ce document ne prouve pas

Il énonce des modalités ; il ne prouve pas qu'elles sont tenues. Cette preuve-là
est ailleurs, et elle est **partielle** : une séance de veille écrite sur une
récurrence attendue, aucun compte rendu de revue, aucune rétrospective, et un
tableau de suivi pas encore ouvert aux parties prenantes.

Le dire ici est délibéré. La suite consiste à tenir ces rituels et à en déposer
les traces, pas à réécrire ce document.
