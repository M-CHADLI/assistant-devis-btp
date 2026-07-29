# RenoAssistant — Sources de Données

> Brief : "Concevoir les sources de données de mon fil rouge"
> Livrable 3 : Identifier les sources de données utiles pour l'ensemble (liens, pages, API précisément)

---

## Tableau des sources

| # | Source | Usage | Technologie | Lien / Endpoint précis | Statut |
|---|--------|-------|-------------|------------------------|--------|
| 1 | **SMS Gateway** | Réception/envoi SMS (US1) | Twilio | `https://api.twilio.com/2010-04-01/`<br>Webhook : `https://[id].ngrok.io/sms/incoming` | ✅ |
| 2 | **LLM + Embeddings** | Matching sémantique + génération vecteurs | Ollama / Gemma 4 27B | `http://localhost:11434/api/chat`<br>`http://localhost:11434/api/embeddings` | ✅ |
| 3 | **Catalogue Promos** | 3500 articles promo (US1) | Dump SQL simulé → PostgreSQL | Table `operations_commerciales`<br>(données LM anonymisées) | ✅ |
| 4 | **Base de données** | Persistance + recherche vectorielle | PostgreSQL 15 + pgvector (Docker) | Image : `pgvector/pgvector:pg15`<br>Port : `5432` | ✅ |
| 5 | **Contexte sessions** | Historique conversation + compteur shots | Redis 7 Alpine (Docker) | Image : `redis:7-alpine`<br>Port : `6379`<br>TTL : 3600s | ✅ |
| 6 | **Filtres LM (US2)** | Système de filtres catalogue natif LM | API interne LM | ❓ À investiguer avec équipe tech LM | ⏳ |
| 7 | **Page promos LM** | Lien envoyé dans les SMS (US1) | Page publique LM | `https://www.leroymerlin.fr/promotions` | ✅ |

---

## Détail par User Story

### US1 — Matching Promo via SMS

| Source | Rôle dans le flux |
|--------|--------------------|
| Twilio | Réceptionne le SMS client, envoie la réponse |
| Table `operations_commerciales` | Contient les 3500 articles en promotion à matcher |
| Ollama / Gemma 4 | Génère les embeddings + fait le matching sémantique |
| Page `leroymerlin.fr/promotions` | Destination des liens envoyés au client |

### US2 — Filtre Agentique (site/app LM)

| Source | Rôle dans le flux |
|--------|--------------------|
| Widget bouton (site/app LM) | Point d'entrée de la conversation client |
| API interne LM (filtres) | Doit traduire le prompt en filtres catalogue — **à investiguer** |
| Ollama / Gemma 4 | Traduit le langage naturel en paramètres de filtre |
| Catalogue LM natif | Source des résultats affichés au client |

---

## Infrastructure (Docker)

```yaml
# docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: renoassistant

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

Démarrage : `docker compose up -d`

---

## Légalité des données

Les données LM (catalogue + promos) sont accessibles via le poste de travail actuel mais ne peuvent pas être utilisées directement hors mission.

**Solution retenue pour le MVP :**
- Conserver la **structure réelle** du dump SQL (tables, colonnes, relations)
- **Simuler les valeurs** (noms, prix, références randomisés)
- Objectif : valider l'architecture sans exposer de vraies données

---

## Point bloquant identifié

L'intégration du filtre agentique (US2) dans le site/app LM nécessite de connaître comment le système de filtres existant est exposé (API interne, paramètres d'URL, ou manipulation du DOM).

**Action requise :** clarifier ce point avec l'équipe technique LM avant le démarrage du développement d'US2.
