# Notes de travail

> Bloc-notes. Idées attrapées au vol, pas encore arbitrées.
> Ce qui est tranché ici remonte dans `CADRAGE_MODELE.md` ou
> `DISPOSITIF_AGENT.md`, et la note est retirée.

---

## Fallback de modèle (`model_fallback`)

**Le besoin.** Le modèle est **auto-hébergé** sur la DGX Spark. Une seule
machine, un seul serveur d'inférence : c'est un point de défaillance unique.
S'il tombe, l'application ne répond plus — y compris le jour de la soutenance.

Il faut donc une **bascule automatique** vers un modèle de secours quand
l'appel primaire échoue : machine indisponible, modèle non chargé, timeout,
saturation mémoire, ou sortie inexploitable.

**Piste technique — LangChain.** `ModelFallbackMiddleware`, module
`langchain.agents.middleware.model_fallback`. C'est un **middleware d'agent**,
à ne pas confondre avec `Runnable.with_fallbacks()` qui traite le même besoin
au niveau d'un runnable isolé.

```python
ModelFallbackMiddleware(
    first_model: str | BaseChatModel,
    *additional_models: str | BaseChatModel,
)
```

Point d'attention : les modèles listés sont les **alternatives**. Le modèle
primaire reste celui déclaré sur l'agent ; le middleware n'entre en jeu qu'après
son échec, puis essaie ses modèles dans l'ordre jusqu'au premier succès.

La documentation ne dit **pas** quels types d'erreur déclenchent la bascule —
elle parle d'« échec de l'appel modèle », sans plus. À vérifier en lisant le
code : ça détermine si une sortie non conforme (JSON invalide) déclenche ou non,
ce qui est justement la question ouverte plus bas.

Choisir LangChain comme couche d'orchestration n'est pas neutre : ça engage
l'architecture de l'API qui expose le modèle. À poser explicitement, pas à
subir par défaut parce que le fallback y était pratique.

**Chaîne de secours envisagée**, du plus fidèle au plus dégradé :

1. **gpt-oss-120b fine-tuné** — le modèle primaire, déclaré sur l'agent
2. **gpt-oss-20b fine-tuné** — même dataset, même schéma de sortie, tient sur
   bien moins de mémoire. Le fallback naturel : les réponses restent conformes
3. **20b brut avec prompt système** — celui de la baseline du §7. Déjà écrit,
   déjà mesuré : on sait exactement ce qu'il vaut
4. **Refus explicite** — mieux qu'une réponse inventée

**Ce qui rend le fallback praticable ici.** Le schéma de sortie est **unique et
partagé par toutes les capacités**. Le code qui consomme le JSON ne change pas
selon le modèle qui l'a produit : basculer de modèle ne casse rien en aval. Sans
ce schéma unique, chaque fallback demanderait son propre parseur.

**Questions ouvertes.**

- **Où vit le fallback ?** Dans l'API qui expose le modèle, ou dans
  l'application qui la consomme ? Réponse probable : dans l'API — c'est elle qui
  sait quel modèle est chargé.
- **Un fallback distant est-il acceptable ?** Une API externe comme dernier
  recours violerait le « 100 % local, les données ne sortent pas de la
  machine ». À trancher : soit on l'exclut, soit on l'autorise avec un
  consentement explicite. Par défaut, **exclu**.
- **Sur quoi déclenche-t-on ?** Erreur réseau et timeout, évidemment. Mais aussi
  **JSON invalide** ? Un JSON invalide est déjà la métrique nº 1 du projet — le
  retenir comme déclencheur de fallback mélangerait la mesure et la mitigation.
  Prudence : mesurer d'abord sur le modèle primaire seul, activer le fallback
  ensuite.
- **Faut-il journaliser chaque bascule ?** Oui. C'est une métrique
  d'exploitation à part entière, et le taux de recours au fallback dit la
  fiabilité réelle de l'hébergement.

**Ce que ça apporte au-delà de la robustesse.** Cette chaîne est de la matière
directe pour deux compétences : le **monitorage** (taux de bascule, seuil
d'alerte) et la **gestion d'incident**. Le fallback est un cas d'incident réel,
reproductible et documentable — pas un incident fabriqué pour l'occasion.

**Sources.**

- [ModelFallbackMiddleware — LangChain Reference](https://reference.langchain.com/python/langchain/agents/middleware/model_fallback/ModelFallbackMiddleware)
- [How to add fallbacks to a runnable](https://python.langchain.com/v0.2/docs/how_to/fallbacks/) — l'autre mécanisme, au niveau runnable

**Coût honnête.** Faire tourner deux modèles simultanément sur 128 Go de mémoire
unifiée n'est pas gratuit : le 120b en occupe déjà une large part. Deux options
— soit le 20b reste chargé en permanence (mémoire consommée en continu), soit il
est chargé à la demande (bascule lente, plusieurs dizaines de secondes). Le
second ne tient pas la latence p95 de 30 s du plan d'évaluation. **À mesurer
avant de promettre quoi que ce soit.**
