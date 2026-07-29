# RenoAssistant — Diagramme de Séquence

> Utiliser sur https://mermaid.live ou dans tout fichier Markdown.

---

## Séquence Globale — US1 + US2

```mermaid
sequenceDiagram
    participant C as Client PRO
    participant T as Twilio
    participant API as FastAPI
    participant R as Redis
    participant G as Gemma 4
    participant DB as PostgreSQL + pgvector

    C->>T: SMS entrant
    T->>API: POST /sms/incoming (From, Body)
    API->>DB: Vérifie whitelist
    DB-->>API: ✅ Autorisé
    API->>R: Récupère contexte + shots
    R-->>API: Historique session

    API->>G: [historique + SMS + tools]

    alt US1 — Matching Promo via SMS
        G->>DB: tool: match_promos(prompt, top=10)
        Note over DB: Table: operations_commerciales\n3500 articles (pgvector)
        DB-->>G: Top 10 articles matchés
        G-->>API: Top 10 + liens filtrés
        API->>R: Incrémente compteur shots
        API-->>T: "Top 10 : Bosch -30% [lien]..."
        T-->>C: SMS reçu

        C->>T: "plutôt pour du béton"
        T->>API: POST /sms/incoming
        API->>R: shots restants ?
        R-->>API: 4 shots restants
        API->>G: [contexte + prompt affiné]
        G->>DB: tool: match_promos(prompt affiné, top=10)
        DB-->>G: Top 10 affinés
        API->>R: Incrémente compteur shots
        API-->>T: "Top 10 affiné : [lien]..."
        T-->>C: SMS → continue sur site/app LM

    else US2 — Filtre Agentique (site/app LM)
        Note over C,G: Canal différent — widget bouton sur site/app LM
        C->>G: "perceuse pour béton, budget 100€ max"
        G->>G: Analyse contexte page actuelle\n+ filtres disponibles LM
        G->>DB: tool: translate_to_filters(prompt, page_context)
        Note over DB: Filtres existants LM\n(catalogue natif)
        DB-->>G: {type:burin, usage:béton, prix_max:100}
        G-->>C: Applique filtres → résultats mis à jour

        C->>G: "plutôt en sans fil"
        G->>DB: tool: translate_to_filters(prompt affiné, contexte)
        DB-->>G: {type:burin, usage:béton, prix_max:100, alim:batterie}
        G-->>C: Résultats affinés automatiquement
    end
```

---

*Visualiser sur [mermaid.live](https://mermaid.live)*
