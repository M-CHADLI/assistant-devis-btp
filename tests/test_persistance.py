"""Tests du registre de projets — isolement, persistance, robustesse."""
from __future__ import annotations

import pytest

from app.devis import ajouter_ligne
from app.persistance import (MOTIF_ID, ProjetIntrouvable, Registre,
                             deserialiser_session, serialiser_session)
from app.pipeline import Correction, Escalade, Session, valider_structure


@pytest.fixture
def registre(tmp_path):
    return Registre(racine=tmp_path)


def test_deux_projets_sont_isoles(registre):
    """Le défaut corrigé : une Session de module partagée par tous."""
    id_a, sess_a = registre.creer()
    id_b, sess_b = registre.creer()
    assert id_a != id_b

    ajouter_ligne(sess_a.devis, "PEINT_FINITION", "surface", 22.0)
    registre.enregistrer(id_a, sess_a)

    assert len(registre.obtenir(id_a).devis.lignes) == 1
    assert len(registre.obtenir(id_b).devis.lignes) == 0


def test_un_projet_survit_au_redemarrage(tmp_path):
    registre = Registre(racine=tmp_path)
    projet_id, session = registre.creer()
    ajouter_ligne(session.devis, "SOL_POSE_STRATIFIE", "surface", 18.0)
    session.pieces.append("salon")
    registre.enregistrer(projet_id, session)

    # Nouveau registre = nouveau processus : le cache mémoire est vide.
    relu = Registre(racine=tmp_path).obtenir(projet_id)
    assert relu.pieces == ["salon"]
    assert len(relu.devis.lignes) == 1
    assert relu.devis.total_ht == session.devis.total_ht


def test_les_totaux_survivent_a_l_aller_retour(tmp_path):
    session = Session()
    ajouter_ligne(session.devis, "PEINT_FINITION", "surface", 22.0)
    ajouter_ligne(session.devis, "SOL_POSE_STRATIFIE", "surface", 22.0)
    relu = deserialiser_session(serialiser_session(session))
    assert relu.devis.total_ht == session.devis.total_ht
    assert relu.devis.total_ttc == session.devis.total_ttc
    assert relu.devis.acompte_30_pct == session.devis.acompte_30_pct
    assert relu.devis.ventilation_tva == session.devis.ventilation_tva


def test_mentions_corrections_et_escalades_survivent(tmp_path):
    session = Session()
    ajouter_ligne(session.devis, "ELEC_TABLEAU", "unite", 1.0)
    session.corrections.append(Correction("2026-09-08T10:00:00", "artisan", "ligne retirée"))
    session.escalades.append(Escalade("2026-09-08T10:01:00", "json_invalide", "détail"))
    relu = deserialiser_session(serialiser_session(session))
    assert relu.devis.mentions == session.devis.mentions
    assert relu.corrections[0].description == "ligne retirée"
    assert relu.escalades[0].motif == "json_invalide"


def test_identifiant_forge_est_refuse(registre):
    """Un identifiant finit en nom de fichier : pas de remontée d'arborescence."""
    for forge in ("../../etc/passwd", "a/b", "court", "AVEC-MAJ", ""):
        with pytest.raises(ValueError):
            registre.obtenir(forge)


def test_identifiant_genere_respecte_le_motif(registre):
    projet_id, _ = registre.creer()
    assert MOTIF_ID.match(projet_id)


def test_projet_inexistant_leve_une_erreur_claire(registre):
    with pytest.raises(ProjetIntrouvable):
        registre.obtenir("abcdef0123456789")


def test_obtenir_ou_creer_repart_a_neuf_sur_identifiant_perime(registre):
    """Un cookie qui traîne après un nettoyage du disque ne doit pas planter."""
    projet_id, _ = registre.obtenir_ou_creer("abcdef0123456789")
    assert projet_id != "abcdef0123456789"
    projet_id_forge, _ = registre.obtenir_ou_creer("../../etc/passwd")
    assert MOTIF_ID.match(projet_id_forge)


def test_reinitialiser_vide_le_projet_sans_le_supprimer(registre):
    projet_id, session = registre.creer()
    ajouter_ligne(session.devis, "PEINT_FINITION", "surface", 10.0)
    registre.enregistrer(projet_id, session)
    neuve = registre.reinitialiser(projet_id)
    assert neuve.devis.lignes == []
    assert registre.obtenir(projet_id).devis.lignes == []
    assert projet_id in registre.lister()


def test_l_etat_de_validation_de_structure_survit_au_disque(tmp_path):
    """US-12 + US-16 : un devis non validé se relit non chiffré, et un devis
    validé se relit chiffré."""
    registre = Registre(racine=tmp_path)
    projet_id, session = registre.creer()
    ajouter_ligne(session.devis, "PEINT_FINITION", "surface", 22.0,
                  chiffrer_maintenant=False)
    registre.enregistrer(projet_id, session)

    registre._cache.clear()
    relue = registre.obtenir(projet_id)
    assert relue.structure_validee is False
    assert relue.devis.lignes[0].chiffree is False
    assert relue.devis.lignes[0].quantite_technique > 0
    assert relue.devis.total_ht == 0.0  # rien n'a été chiffré

    valider_structure(relue)
    registre.enregistrer(projet_id, relue)
    registre._cache.clear()
    apres = registre.obtenir(projet_id)
    assert apres.structure_validee is True
    assert apres.devis.total_ht > 0


def test_un_projet_version_2_se_relit_comme_deja_chiffre():
    """Repli de compatibilité : avant la version 3, le devis était chiffré dès
    l'ajout de la ligne. Le relire comme « non validé » masquerait ses prix."""
    v2 = {
        "version": 2,
        "devis": {"mentions": [], "lignes": [
            {"lot_code": "PEINT_FINITION", "nom_lot": "Peinture de finition",
             "produit": None, "quantite_achat": 3, "prix_unitaire_ht": 34.9,
             "prix_ht": 104.7, "taux_tva": "10", "origine": "modèle"}]},
    }
    session = deserialiser_session(v2)
    assert session.structure_validee is True
    assert session.devis.total_ht == 104.7


def test_une_contradiction_survit_au_rechargement(tmp_path):
    """US-06 — relue du disque sans son motif, elle redeviendrait une quantité
    hors bornes, et la valeur qu'elle remplace serait perdue."""
    from app.pipeline import LigneEnAttente
    registre = Registre(racine=tmp_path)
    projet_id, session = registre.creer()
    session.a_confirmer.append(LigneEnAttente(
        "PEINT_FINITION", "surface", 25.0, 0.5, 400.0,
        motif="contradiction", valeur_existante=22.0))
    registre.enregistrer(projet_id, session)
    relu = deserialiser_session(serialiser_session(session))
    assert relu.a_confirmer[0].motif == "contradiction"
    assert relu.a_confirmer[0].valeur_existante == 22.0
