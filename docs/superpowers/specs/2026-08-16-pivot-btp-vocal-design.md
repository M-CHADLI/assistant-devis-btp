# Pivot — Application B2B vocale pour prestataires BTP

> **Statut : EN COURS.** Séance de brainstorming interrompue avant la fin. Sections 1 à 3
> validées avec l'utilisateur. Sections 4+ (parcours démo, écarté, impact sur le planning,
> impact sur les livrables RNCP) restent à faire à la reprise.
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
admin/validateur, le client participe (coordonnées, relances, signature). Devis **et** facture,
générés par **commande vocale** sur chantier. Chantier pilote élargi à 4 corps de métier
(peinture, sols, plomberie, électricité).

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
└──────────────────────┘
```

**Orchestration :** un framework d'agents (LangChain ou équivalent) pilote l'enchaînement —
capture, appel STT, appel LLM reformulation, appel LLM fine-tuné, appels d'outils vers le
référentiel/catalogue. Décision : architecture d'agents réelle (pas juste un sujet de veille),
cohérent avec le `ModelFallbackMiddleware` déjà exploré dans `docs/NOTES.md`.

**Facture :** générée par **code déterministe** à partir du devis validé (mêmes lignes +
mentions légales + acompte/solde) — pas un second passage du modèle. Cohérent avec "le modèle
ne calcule jamais".

**API Pappers :** auto-remplit les infos légales du prestataire à l'inscription (SIRET, forme
juridique, adresse) à partir du numéro SIRET — alimente les mentions obligatoires du
devis/facture.

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

## Reste à faire à la reprise

- [ ] **Section 4 — Parcours de démo & écarté explicite.** Le parcours validé plus tôt dans la
      conversation (à reconfirmer par écrit ici) : capture vocale → devis structuré validé par
      l'artisan = le cœur démontré en direct. Signature électronique, facture, relances =
      conçues et documentées, pas le clou de la démo (signature légale explicitement écartée
      du périmètre 4 mois — trop complexe en soi).
- [ ] **Section 5 — Impact sur `PLANNING.md`.** Le jalon d'août ("référentiel v1") change de
      nature : moins de collecte manuelle, mais un vrai travail de relecture/validation du
      référentiel généré par LLM sur 4 corps de métier au lieu d'un. Le plafond de 2-3 semaines
      est-il encore le bon repère ?
- [ ] **Section 6 — Impact sur les livrables RNCP** (`docs/LIVRABLES.md`) — nouvelles
      compétences potentiellement mieux couvertes (C9 agents, base de données client/devis,
      API Pappers = C1/C8), à revérifier corp par corp de métier.
- [ ] Auto-revue du spec (placeholders, cohérence, ambiguïté)
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
| 5 | Parcours démo | Capture vocale → devis validé (signature/facture/relances = conçues, pas démontrées) |
| 6 | Agents IA | Architecture réelle (framework d'orchestration), pas juste de la veille |
| 7 | API Pappers | Auto-remplissage des mentions légales prestataire (SIRET) |
| 8 | Réalisme du texte d'entraînement | Texte propre (validé en amont par l'utilisateur) |
| 9 | Modèle de reformulation | Non tranché, pas bloquant |
| 10 | Profondeur du référentiel (4 corps de métier) | Uniforme, comblée par le LLM — pas de sourcing systématique, y compris peinture/sols |
