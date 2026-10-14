"""Configuration commune des tests.

L'authentification (docs/produit/STORIES.md US-23) est **toujours active** : il n'existe
pas de mode ouvert à activer pour les tests. On fixe donc ici une phrase de passe
connue, avant que `app.main` ne soit importé, et les fixtures de client HTTP
ouvrent une vraie session. Les tests traversent ainsi le même chemin qu'un
navigateur — c'est ce qui fait qu'ils prouvent quelque chose.
"""
from __future__ import annotations

import os

from app.authentification import empreinte

PHRASE_TEST = "phrase-de-passe-des-tests"

# Avant tout import de app.main : la configuration est lue au chargement du
# module, pas à chaque requête.
os.environ.setdefault("BTP_MOT_DE_PASSE", empreinte(PHRASE_TEST))


def authentifier(client) -> None:
    """Ouvre une session sur un TestClient — le cookie reste dans son jar."""
    reponse = client.post("/api/session", json={"phrase": PHRASE_TEST})
    assert reponse.status_code == 200, reponse.text
