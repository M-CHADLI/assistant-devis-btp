# Pivot — Application B2B vocale pour prestataires BTP

> **Statut : sections 1 à 6 validées avec l'utilisateur — cadrage complet.** Reste l'auto-revue
> du spec puis la répercussion dans les documents de conception (voir checklist en bas).
>
> **Ce document remplace, à terme, `docs/CADRAGE_MODELE.md`.** Tant que ce document n'est pas
> finalisé et que `CADRAGE_MODELE.md` n'est pas réécrit, **les deux coexistent** — mais
> `CADRAGE_MODELE.md` décrit l'ancien produit (Assistant Bricolage client final, peinture/sols
> uniquement, canal web, devis sans prix). Ne pas s'y fier pour le produit actuel.

---

## Le pivot en une phrase

**Avant** — Assistant Bricolage fine-tuné : client final, intention floue → devis interactif
client + artisan, chantier pilote peinture/sols uniquement, canal web, saisie texte.

**Après** — Application web B2B pour prestataires de services (priorité BTP) : l'artisan est
admin/validateur, le client participe (coordonnées). Devis structuré, modifiable et exportable
(Word), généré par **commande vocale** sur chantier. Chantier pilote élargi à 4 corps de métier
(peinture, sols, plomberie, électricité). Le produit s'arrête au devis — facture, signature et
relances sont hors périmètre.

---

## Section 1 — Vue d'ensemble & principes directeurs

**Produit :** Application web pour prestataires de services (priorité BTP) — génération de
devis par commande vocale, validée par l'artisan.

**Principes conservés de l'ancien cadrage :**
- Le modèle ne calcule jamais les montants — code déterministe pour les prix/totaux
- Schéma de sortie unique par `intent`
- 100 % local (STT + LLM sur la même machine — DGX Spark)
- Le professionnel fait autorité, ses corrections sont journalisées comme signal qualité

**Principe nouveau :** le signal qualité est capturé à **deux points** du pipeline (correction
de transcription + correction de devis), pas un seul.

**Principe modifié (décision assumée, cf. Section 3) :** le référentiel métier n'est plus
systématiquement sourcé — le LLM comble les valeurs pour les 4 corps de métier. Le jeu de test
reste, lui, écrit/corrigé à la main — non négociable.

---

## Section 2 — Architecture technique (le cœur)

```
┌─────────────┐
│ Capture audio│  Plusieurs enregistrements (mesures, notes de chantier)
└──────┬──────┘
       ↓
┌─────────────┐
│ STT local    │  Type Whisper, tourne sur la DGX Spark — l'audio ne sort jamais
└──────┬──────┘
       ↓
┌──────────────────────┐
│ LLM — correction/     │  Modèle prompté (pas fine-tuné), collabore avec
│ reformulation          │  l'utilisateur pour valider le texte
└──────┬────────────────┘
       ↓ (texte validé par l'utilisateur)
┌──────────────────────┐
│ LLM fine-tuné          │  Génère le JSON structuré (intent, payload, mention)
│ → JSON devis            │
└──────┬────────────────┘
       ↓
┌──────────────────────┐
│ Code déterministe      │  Requêtes référentiel, calculs, prix, devis final
└──────┬────────────────┘
       ↓
┌──────────────────────┐
│ Artisan valide/corrige │  Chaque correction journalisée comme signal qualité
│ (voix ou texte)         │
└──────┬────────────────┘
       ↓
┌──────────────────────┐
│ Devis modifiable/      │  Édition directe + export Word. Le produit s'arrête ici —
│ export Word             │  facture, signature, relances hors périmètre
└──────────────────────┘
```

**Orchestration :** un framework d'agents (LangChain ou équivalent) pilote l'enchaînement —
capture, appel STT, appel LLM reformulation, appel LLM fine-tuné, appels d'outils vers le
référentiel/catalogue. Décision : architecture d'agents réelle (pas juste un sujet de veille),
cohérent avec le `ModelFallbackMiddleware` déjà exploré dans `docs/NOTES.md`.

**API Pappers :** auto-remplit les infos légales du prestataire à l'inscription (SIRET, forme
juridique, adresse) à partir du numéro SIRET — alimente les mentions obligatoires du devis.

**Point ouvert, non bloquant :** un seul modèle chargé qui fait les deux rôles (reformulation
promptée + génération JSON fine-tunée), ou deux modèles séparés — à trancher plus tard sur la
base de mesures mémoire réelles sur la DGX Spark.

---

## Section 3 — Référentiel & dataset

**Chantiers pilotes (4 corps de métier, profondeur uniforme — Approche 1 retenue) :**

| Corps de métier | Rôle | Profondeur |
|---|---|---|
| Peinture | Cœur historique | Large, comblé par le LLM (pas de sourcing systématique) |
| Sols | Cœur historique | Large, comblé par le LLM |
| Plomberie | Démontre `mention forte` | Large aussi |
| Électricité | Démontre `mention forte` | Large aussi |

**Décision assumée et sa conséquence, nommée explicitement :** le référentiel n'est plus
sourcé systématiquement (une ligne = une valeur = une source, comme dans l'ancien cadrage) —
le LLM comble les valeurs métier pour les 4 corps de métier, y compris peinture/sols qui
portait auparavant l'argument central du pivot ("le modèle généraliste produit du plausible,
pas du juste").

**Conséquence à assumer pour la soutenance :** l'argument de différenciation du fine-tuning se
déplace de *"exactitude des valeurs métier"* vers *"fiabilité du format JSON"* et *"qualité de
structuration vocal → devis"*. Argument toujours défendable, mais différent — à énoncer comme
tel, pas à laisser dériver silencieusement.

**Garde-fou conservé (non négociable) :** le **jeu de test (150-200 exemples)** reste écrit/
corrigé à la main, jamais généré. Il porte plus de poids que dans l'ancien cadrage puisque le
référentiel d'entraînement n'est plus sourcé — c'est la seule mesure qui reste honnête devant
le jury.

**Dataset (~2000 exemples, structure inchangée) :**
- Le texte source de chaque exemple simule un texte **déjà validé** par l'utilisateur (pas de
  bruit vocal à simuler — le LLM de reformulation nettoie avant que le fine-tuné reçoive le
  texte)
- `reasoning` obligatoire, ~72 % raisonné, `mention` transverse (~15 % simple, ~5 % forte) —
  la présence de plomberie/électricité rend les exemples `mention forte` réels, pas
  hypothétiques

**Protocole de preuve (20b brut vs fine-tuné) : inchangé dans sa forme**, mais son
interprétation change — il mesure maintenant *fiabilité du format + qualité de
structuration*, pas *justesse des valeurs métier*.

**Piste "second cercle" notée, pas dans le noyau actuel :** scraping ou MCP pour la recherche
produit / liste de matériaux, envisageable plus tard pour retrouver un sourcing plus rigoureux
sans repasser par la collecte manuelle.

---

## Section 4 — Parcours de démo & écarté explicite

**Parcours démontré en direct (cœur de la démo) :**
Un chantier continu multi-corps de métier (peinture, sols, plomberie, électricité) en une
captation vocale suivie : l'utilisateur décrit son chantier à la voix, le pipeline (STT local →
LLM reformulation → LLM fine-tuné → code déterministe) produit un devis structuré couvrant les
4 corps de métier. L'artisan valide et **corrige volontairement une erreur provoquée** sur un
des corps de métier (ex. quantité ou référence), démontrant en direct la capture du signal
qualité — pas seulement décrite, jouée.

**Montré, non interactif :**
Le devis est **exportable en Word** et/ou **éditable directement** dans l'interface — capacité
montrée à l'écran en fin de démo.

**Hors produit, point final (pas seulement hors périmètre 4 mois) :**
Facture, signature électronique, relances client. Le produit s'arrête au devis structuré,
modifiable et exportable ; au-delà, le client se débrouille. Décision assumée : ça simplifie
l'architecture (plus de génération de facture, cf. Section 2) et recentre l'argument de
différenciation sur le devis par la voix.

**Reconduit de l'ancien cadrage, à reconfirmer en Section 6 (RNCP) :** diagnostic de pathologie
du bâtiment et estimation de main d'œuvre restent écartés du périmètre (déjà actés dans
`docs/CADRAGE_MODELE.md`, sans lien avec le pivot).

---

## Section 5 — Impact sur `PLANNING.md`

**Août — référentiel :** créneau inchangé. La nature du travail change (relecture/validation du
référentiel comblé par le LLM sur 4 corps de métier, plutôt que collecte sourcée sur 1), mais le
plafond de 2-3 semaines tient — décision assumée, à surveiller en pratique une fois le travail
commencé.

**Septembre — dataset :** inchangé dans sa forme (schéma JSON, jeu de test 150-200 exemples
gelé, génération ~2000 exemples). Porte plus loin qu'avant : le référentiel non sourcé
systématiquement rend le jeu de test manuel encore plus central (cf. Section 3).

**Octobre — la preuve :** inchangé. Le code déterministe à écrire perd la brique facture
(retirée du produit, cf. Section 4) — légèrement allégé.

**Novembre — la démo :** simplifié. L'interface à deux sessions simultanées (client/artisan)
disparaît — le produit s'arrête au devis côté artisan, il n'y a plus de rôle client actif à
démontrer. Une seule interface (artisan, capture vocale + validation + export) à faire tenir.
Le parcours répété plusieurs fois reste le chantier continu multi-corps de métier avec
correction provoquée (cf. Section 4).

**Marges et points de rupture — mis à jour :** l'ordre de dégradation en cas de dérapage reste
*120b puis second cercle*. Le repli "interface à une seule fenêtre" disparaît avec la session
client — pas de filet de sécurité supplémentaire ajouté à sa place : au-delà de 120b et second
cercle, plus rien n'est négociable (référentiel, jeu de test, devis vocal sur les 4 corps de
métier).

---

## Section 6 — Impact sur les livrables RNCP (`docs/LIVRABLES.md`)

**E1 — Données (C1-C5) : renforcé, décision assumée.** Le référentiel comblé par le LLM
(Section 3) ne peut plus porter à lui seul l'argument « collecte multi-sources sourcée » de C1.
Décision : le **scraping des fiches techniques fabricants est maintenu comme exercice de
collecte à part entière**, même s'il ne sert plus directement à entraîner le modèle. Deux usages
distincts, assumés comme tels dans le document : collecte structurée pour C1, référentiel
d'entraînement comblé par le LLM pour le dataset. Le dump catalogue LM et l'API OCR restent les
autres piliers de C1 déjà identifiés.

**E2 — Veille (C6-C8) : inchangé par le pivot en lui-même**, mais le champ de la veille s'élargit
mécaniquement (STT, agents, API type Pappers — déjà noté dans la checklist de reprise). **C8**
reste porté par l'OCR ; l'**API Pappers n'est pas un service IA** et ne revendique pas C8 — elle
est documentée comme service externe intégré (accès, configuration), sans effet sur la
couverture.

**E3 — Le modèle IA (C9-C13) : renforcé sur C9.** Le framework d'orchestration d'agents
(Section 2) n'est plus qu'un sujet de veille : c'est une architecture réelle qui pilote
l'enchaînement STT → LLM reformulation → LLM fine-tuné → outils référentiel. Il **renforce C9**
(API exposant le modèle) plutôt que d'ouvrir une compétence à part — l'orchestration fait partie
de la réponse à C9, pas un livrable distinct.

**E4 — L'application (C14-C19) : pas d'inquiétude particulière.** Le retrait de la
facture/signature/relances (Section 4) réduit un peu la matière disponible pour C15 (parcours,
plus de rôle client actif) et C17 (développement, moins d'écrans), mais le gain sur C1 et C9
suffit à compenser — pas de manque à signaler dans la grille pour cette raison.

**E5 — Exploitation (C20-C21) : inchangé.** Le pivot ne change rien à ce qui reste à faire
(journalisation, outil de suivi des incidents dès le début).

**Conséquence à reporter dans `docs/LIVRABLES.md` :** la ligne C1 du tableau « source exigée →
ce que le projet peut y mettre » doit préciser que le scraping fabricants sert la collecte (C1)
indépendamment du dataset d'entraînement, pour ne pas laisser croire que le référentiel reste
sourcé ligne à ligne comme dans l'ancien cadrage.

---

## Reste à faire à la reprise

- [x] Auto-revue du spec (placeholders, cohérence, ambiguïté) — faite, spec complète et
      cohérente
- [ ] Une fois validé : réécrire `docs/CADRAGE_MODELE.md`, `docs/DISPOSITIF_AGENT.md`,
      `PLANNING.md`, `docs/LIVRABLES.md` pour refléter ce cadrage
- [ ] Répercuter dans Notion (the-projet + Livrables RNCP)
- [ ] Reprendre la mise en place de la routine de veille (élargie : STT, fiscalité,
      comptabilité, API type Pappers, agents IA, fine-tuning) — interrompue avant cadrage du
      pivot

## Décisions déjà actées pendant le brainstorming (résumé rapide)

| # | Question | Décision |
|---|---|---|
| 1 | Scope du fine-tuning | Texte validé → JSON devis structuré uniquement |
| 2 | STT | Local (type Whisper), même machine que le LLM |
| 3 | Corps de métier | Peinture + sols + plomberie + électricité |
| 4 | Choix plomberie/électricité | Retenu malgré la complexité `mention forte` |
| 5 | Parcours démo | Chantier continu, 4 corps de métier enchaînés dans une captation vocale unique |
| 5b | Correction artisan en démo | Provoquée volontairement sur un corps de métier, pour montrer le signal qualité en direct |
| 5c | Facture/signature/relances | Hors produit, point final — le client exporte le devis (Word) ou l'édite, et se débrouille au-delà |
| 6 | Agents IA | Architecture réelle (framework d'orchestration), pas juste de la veille |
| 7 | API Pappers | Auto-remplissage des mentions légales prestataire (SIRET) |
| 8 | Réalisme du texte d'entraînement | Texte propre (validé en amont par l'utilisateur) |
| 9 | Modèle de reformulation | Non tranché, pas bloquant |
| 10 | Profondeur du référentiel (4 corps de métier) | Uniforme, comblée par le LLM — pas de sourcing systématique, y compris peinture/sols |
