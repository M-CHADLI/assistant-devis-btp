# Empaquetage du produit — voir docs/LIVRAISON_CONTINUE.md
#
# Trois intentions, dans cet ordre :
#   1. qu'un jury puisse lancer le produit sans installer Python ni uv ;
#   2. que l'image soit reproductible — uv.lock fait foi, jamais la résolution
#      du jour ;
#   3. que l'image soit hors ligne — aucune collecte n'est refaite à la
#      construction, la base catalogue est reconstruite depuis le jeu de
#      données versionné.
#
# Ce qui n'est PAS dans l'image, volontairement : le modèle. L'assistant
# appelle un LLM qui tourne ailleurs (BTP_LLM_URL) ; embarquer 65 Go de poids
# dans une image de démonstration n'aurait aucun sens. Sans modèle joignable,
# l'application démarre quand même et le signale — c'est le cas dégradé de
# US-26.

# --- Étape 1 : dépendances et base catalogue --------------------------------
FROM python:3.14-slim-bookworm AS constructeur

COPY --from=ghcr.io/astral-sh/uv:0.9.29 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /src

# Les métadonnées d'abord : tant qu'elles ne changent pas, le cache Docker
# évite de réinstaller les dépendances à chaque modification du code.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/ app/
COPY tools/ tools/
COPY catalogue/jeu_de_donnees.json catalogue/

# La base est construite ici, pas au démarrage : un conteneur qui démarre ne
# doit pas dépendre d'une étape qui peut échouer. `importer` est idempotent et
# ne lit que le jeu de données versionné — aucun accès réseau.
RUN /opt/venv/bin/python -m tools.donnees.importer

# --- Étape 2 : image d'exécution --------------------------------------------
FROM python:3.14-slim-bookworm AS execution

LABEL org.opencontainers.image.title="assistant-devis-btp" \
      org.opencontainers.image.description="Assistant vocal de devis pour artisans du bâtiment" \
      org.opencontainers.image.licenses="MIT"

# Utilisateur non privilégié : un conteneur qui tourne en root donne le root de
# l'hôte à qui s'échappe du conteneur.
RUN useradd --create-home --uid 10001 artisan

COPY --from=constructeur /opt/venv /opt/venv
WORKDIR /app
COPY --from=constructeur /src/app /app/app
COPY --from=constructeur /src/tools /app/tools
COPY --from=constructeur /src/catalogue /app/catalogue

# BTP_DONNEES pointe hors du code : les devis et le journal qualité sont des
# données d'exploitation, pas des fichiers d'application. Le volume les rend
# persistants entre deux conteneurs.
RUN mkdir -p /donnees && chown artisan:artisan /donnees
VOLUME ["/donnees"]

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BTP_DONNEES=/donnees \
    BTP_CATALOGUE_BASE=/app/catalogue/catalogue.sqlite3

USER artisan
EXPOSE 8000

# La page d'accueil est le seul chemin ouvert sans session (avec /api/session) :
# c'est donc le bon point de sonde. Une sonde authentifiée mesurerait
# l'authentification, pas la santé.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
