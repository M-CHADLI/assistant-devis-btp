"""US-25 — le signal qualité sort du produit, jamais de la machine."""
from __future__ import annotations

import json

import pytest

from app.boucle_qualite import (Candidat, DestinationNonLocale, candidats_de_session,
                                candidats_du_disque, cles_existantes, exporter,
                                systeme_de_fichiers, verifier_destination)
from app.persistance import Registre, deserialiser_session, serialiser_session
from app.pipeline import (Correction, LigneEnAttente, Session, confirmer_quantite,
                          corriger_ligne, valider_transcription)


def _candidat(**ecarts) -> Candidat:
    base = dict(horodatage="2026-09-08T02:00:00", projet_id="abcdef0123456789",
                origine="transcription", entree="vingt deux metres carres",
                sortie_modele="22 m² de peinture", corrige="22 m² de peinture au sol",
                description="dictée corrigée")
    base.update(ecarts)
    return Candidat(**base)


# --------------------------------------------------------------------------
# Le triplet : c'est ce qui fait la valeur d'un candidat
# --------------------------------------------------------------------------

def test_correction_de_transcription_porte_le_triplet():
    session = Session()
    valider_transcription(session, propose="22 m2 de peinture",
                          corrige="22 m² de peinture", brut="euh vingt deux m2")
    correction = session.corrections[0]
    assert correction.origine == "transcription"
    assert correction.entree == "euh vingt deux m2"
    assert correction.sortie_modele == "22 m2 de peinture"
    assert correction.corrige == "22 m² de peinture"


def test_sans_dictee_brute_la_proposition_tient_lieu_dentree():
    """Un appelant qui ne transmet pas le brut ne doit pas produire un candidat
    inexploitable : le triplet reste complet, en moins précis."""
    session = Session()
    valider_transcription(session, propose="22 m²", corrige="22 m² au sol")
    assert candidats_de_session("p", session)[0].complet


def test_transcription_validee_sans_changement_ne_cree_rien():
    session = Session()
    valider_transcription(session, propose="22 m²", corrige="22 m²")
    assert session.corrections == []


def test_correction_de_ligne_porte_ce_que_le_modele_avait_produit():
    session = Session()
    session.historique = [{"role": "user", "content": "salon de 22 m²"},
                          {"role": "assistant", "content": "{}"}]
    from app.devis import ajouter_ligne
    ajouter_ligne(session.devis, "PEINT_FINITION", "surface", 55.0)
    corriger_ligne(session, 0, "ce n'est pas 55 m² mais 45")
    correction = session.corrections[0]
    assert correction.origine == "ligne_devis"
    assert correction.entree == "salon de 22 m²"
    assert "PEINT_FINITION" in correction.sortie_modele
    assert correction.corrige == "ce n'est pas 55 m² mais 45"


def test_correction_de_ligne_ne_garde_aucun_prix():
    """Le prix vient du catalogue, jamais du modèle : il n'a rien à faire dans un
    candidat d'entraînement (CLAUDE.md, « le modèle décrit, il ne calcule pas »)."""
    session = Session()
    from app.devis import ajouter_ligne, chiffrer
    ajouter_ligne(session.devis, "PEINT_FINITION", "surface", 30.0)
    chiffrer(session.devis)
    prix = session.devis.lignes[0].prix_ht
    corriger_ligne(session, 0, "trop de peinture")
    assert str(prix) not in session.corrections[0].sortie_modele


def test_quantite_confirmee_porte_un_triplet_dont_la_correction_est_lidentite():
    """L'artisan confirme : le modèle avait raison, ce sont les bornes qui ont
    crié. Le cas reste un signal, `origine` dit lequel."""
    session = Session()
    session.historique = [{"role": "user", "content": "un mur de 900 m²"}]
    session.a_confirmer.append(LigneEnAttente("PEINT_FINITION", "surface", 900.0, 5.0, 500.0))
    assert confirmer_quantite(session, 0)
    correction = session.corrections[0]
    assert correction.origine == "quantite_hors_bornes"
    assert correction.sortie_modele == correction.corrige != ""
    assert correction.entree == "un mur de 900 m²"


def test_candidat_sans_triplet_est_incomplet():
    session = Session()
    session.corrections.append(Correction(horodatage="h", auteur="artisan",
                                          description="ancienne correction"))
    assert candidats_de_session("p", session)[0].complet is False


# --------------------------------------------------------------------------
# L'export : ajout seul, dédoublonné, jamais rétréci
# --------------------------------------------------------------------------

def test_export_ecrit_le_triplet_sur_chaque_ligne(tmp_path):
    cible = tmp_path / "jeu.jsonl"
    rapport = exporter([_candidat()], cible)
    assert rapport["ajoutes"] == 1
    ligne = json.loads(cible.read_text(encoding="utf-8").strip())
    assert ligne["entree"] and ligne["sortie_modele"] and ligne["corrige"]
    assert ligne["cle"]


def test_export_ne_duplique_pas_un_cas_deja_present(tmp_path):
    cible = tmp_path / "jeu.jsonl"
    exporter([_candidat()], cible)
    rapport = exporter([_candidat(horodatage="2026-09-09T09:00:00")], cible)
    assert rapport["ajoutes"] == 0 and rapport["deja_presents"] == 1
    assert len(cible.read_text(encoding="utf-8").splitlines()) == 1


def test_le_jeu_ne_retrecit_jamais(tmp_path):
    """Un cas ajouté n'est pas retiré — même si la source qui l'a produit a
    disparu et qu'on ré-exporte un lot plus petit."""
    cible = tmp_path / "jeu.jsonl"
    exporter([_candidat(entree="a"), _candidat(entree="b")], cible)
    exporter([_candidat(entree="c")], cible)
    entrees = {json.loads(l)["entree"] for l in cible.read_text(encoding="utf-8").splitlines()}
    assert entrees == {"a", "b", "c"}


def test_export_dun_lot_vide_ne_touche_pas_au_fichier(tmp_path):
    cible = tmp_path / "jeu.jsonl"
    exporter([_candidat()], cible)
    avant = cible.read_bytes()
    exporter([], cible)
    assert cible.read_bytes() == avant


def test_export_refuse_un_candidat_incomplet_mais_le_compte(tmp_path):
    cible = tmp_path / "jeu.jsonl"
    rapport = exporter([_candidat(sortie_modele="")], cible)
    assert rapport["ajoutes"] == 0 and rapport["incomplets"] == 1
    assert not cible.exists()


def test_ligne_tronquee_du_jeu_est_ignoree_sans_perdre_les_autres(tmp_path):
    cible = tmp_path / "jeu.jsonl"
    exporter([_candidat()], cible)
    with cible.open("a", encoding="utf-8") as f:
        f.write('{"cle": "coupé au mil')  # arrêt brutal en pleine écriture
    assert len(cles_existantes(cible)) == 1
    rapport = exporter([_candidat(entree="autre")], cible)
    assert rapport["ajoutes"] == 1


# --------------------------------------------------------------------------
# Rien ne quitte la machine
# --------------------------------------------------------------------------

def test_destination_url_refusee():
    with pytest.raises(DestinationNonLocale):
        verifier_destination("https://exemple.fr/jeu.jsonl")


def test_destination_unc_refusee():
    with pytest.raises(DestinationNonLocale):
        verifier_destination("//serveur/partage/jeu.jsonl")
    with pytest.raises(DestinationNonLocale):
        verifier_destination("\\\\serveur\\partage\\jeu.jsonl")


def test_destination_sur_montage_synchronise_refusee(tmp_path):
    """Ce dépôt est sur un montage rclone vers OneDrive : y écrire le jeu le
    ferait sortir de la machine. La table de montages est injectée pour que le
    test ne dépende pas de la machine qui l'exécute."""
    table = tmp_path / "mounts"
    table.write_text(f"onedrive: {tmp_path} fuse.rclone rw 0 0\n", encoding="utf-8")
    with pytest.raises(DestinationNonLocale) as capture:
        verifier_destination(tmp_path / "jeu.jsonl", table=table)
    assert "fuse.rclone" in str(capture.value)


def test_destination_sur_disque_local_acceptee(tmp_path):
    table = tmp_path / "mounts"
    table.write_text(f"/dev/sda1 {tmp_path} ext4 rw 0 0\n", encoding="utf-8")
    assert verifier_destination(tmp_path / "jeu.jsonl", table=table)


def test_exporter_refuse_avant_toute_ecriture(tmp_path):
    table = tmp_path / "mounts"
    table.write_text(f"onedrive: {tmp_path} fuse.rclone rw 0 0\n", encoding="utf-8")
    cible = tmp_path / "jeu.jsonl"
    with pytest.raises(DestinationNonLocale):
        exporter([_candidat()], cible, table=table)
    assert not cible.exists()


def test_table_de_montages_absente_ne_bloque_pas_lexport(tmp_path):
    """Un noyau sans /proc/mounts ne doit pas empêcher un artisan d'exporter :
    les motifs de chemin restent, la vérification de montage se tait."""
    assert systeme_de_fichiers(tmp_path, table=tmp_path / "inexistant") == ""
    assert verifier_destination(tmp_path / "jeu.jsonl", table=tmp_path / "inexistant")


# --------------------------------------------------------------------------
# Persistance : le triplet survit au disque, les projets d'avant restent lisibles
# --------------------------------------------------------------------------

def test_le_triplet_survit_a_un_aller_retour_disque(tmp_path):
    registre = Registre(tmp_path)
    projet_id, session = registre.creer()
    valider_transcription(session, propose="22 m2", corrige="22 m²", brut="vingt deux")
    registre.enregistrer(projet_id, session)
    registre._cache.clear()
    relue = registre.obtenir(projet_id)
    assert relue.corrections[0].entree == "vingt deux"
    assert relue.corrections[0].corrige == "22 m²"
    assert candidats_de_session(projet_id, relue)[0].complet


def test_projet_en_version_3_reste_lisible():
    """Pas de triplet avant la version 4 : on ne l'invente pas, on le compte."""
    session = deserialiser_session({
        "version": 3,
        "corrections": [{"horodatage": "h", "auteur": "artisan", "description": "d"}],
    })
    correction = session.corrections[0]
    assert correction.description == "d" and correction.entree == ""
    assert candidats_de_session("p", session)[0].complet is False


def test_serialisation_annonce_la_version_4():
    assert serialiser_session(Session())["version"] == 4


def test_candidats_du_disque_parcourt_tous_les_projets(tmp_path):
    registre = Registre(tmp_path)
    for brut in ("un", "deux"):
        projet_id, session = registre.creer()
        valider_transcription(session, propose=brut, corrige=brut + " corrigé", brut=brut)
        registre.enregistrer(projet_id, session)
    assert len(candidats_du_disque(tmp_path)) == 2


def test_fichier_projet_illisible_nempeche_pas_les_autres(tmp_path):
    registre = Registre(tmp_path)
    projet_id, session = registre.creer()
    valider_transcription(session, propose="a", corrige="b", brut="a")
    registre.enregistrer(projet_id, session)
    (tmp_path / "casse.json").write_text("{ceci n'est pas du json", encoding="utf-8")
    assert len(candidats_du_disque(tmp_path)) == 1
