"""Chaîne MLOps — le validateur de dataset, et l'exécuteur d'étapes.

Ce que ces tests défendent surtout, c'est le **jeu d'essai**. Le projet ne
tiendra devant un jury que si sa mesure est honnête, et la mesure cesse de
l'être à la seconde où un exemple d'essai réapparaît à l'entraînement. La
détection de fuite est donc testée pour ce qu'elle doit attraper *et* pour ce
qu'elle ne doit pas confondre.

Le second garde-fou est le gabarit fautif : six exemples portant chacun un
défaut et son motif de refus attendu. Un validateur dont un détecteur casse en
silence est pire que pas de validateur — il promet une garantie qu'il ne tient
plus.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mlops import executer as exe
from tools.mlops import preparer, valider_dataset as vd

RACINE = Path(__file__).resolve().parent.parent


def _ecrire(chemin: Path, exemples: list[dict]) -> Path:
    chemin.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in exemples)
                      + "\n", encoding="utf-8")
    return chemin


@pytest.fixture
def exemple_valide() -> dict:
    return {"id": "t-01", "capacite": "reponse", "user": "c'est quoi une sous-couche ?",
            "final": {"intent": "reponse", "mention": None,
                      "payload": {"texte": "Un apprêt qui uniformise le support."}}}


# --- Le gabarit : le validateur détecte-t-il encore ? ------------------------

def test_le_gabarit_de_reference_est_accepte_et_les_fautifs_refuses():
    """C'est le test qui doit rougir en premier si un détecteur casse."""
    assert vd.verifier_gabarit(RACINE / "dataset/gabarit.jsonl",
                               RACINE / "dataset/gabarit_fautifs.jsonl") == []


def test_le_gabarit_fautif_couvre_des_motifs_distincts():
    """Six exemples qui déclencheraient le même refus ne prouveraient qu'un
    détecteur sur six."""
    motifs = {json.loads(l)["_motif_attendu"] for l in
              (RACINE / "dataset/gabarit_fautifs.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()}
    assert len(motifs) >= 5


# --- Ce que le validateur doit refuser --------------------------------------

@pytest.mark.parametrize("defaut, motif", [
    ({"id": ""}, "identifiant absent"),
    ({"capacite": "bricolage"}, "capacité inconnue"),
    ({"user": ""}, "message utilisateur vide"),
    ({"final": None}, "sortie absente"),
    ({"final": {"intent": "reponse", "payload": {}, "mention": "peut-être"}},
     "enveloppe non conforme"),
])
def test_un_exemple_fautif_est_refuse_avec_son_motif(exemple_valide, defaut, motif):
    rapport = vd.Rapport()
    rapport.lus = 1
    assert not vd.valider_exemple(exemple_valide | defaut, rapport, "essai:1")
    assert motif in rapport.refus


def test_une_capacite_raisonnee_sans_raisonnement_est_refusee():
    """Le `reasoning` porte l'expertise métier. Sans lui, on n'entraîne qu'un
    formateur de JSON — c'est écrit dans le cadrage, et c'est vérifié ici."""
    rapport = vd.Rapport()
    rapport.lus = 1
    exemple = {"id": "t-02", "capacite": "devis", "user": "peinture du couloir, 30 m²",
               "final": {"intent": "devis", "mention": None,
                         "payload": {"pieces": ["couloir"], "lignes": []}}}
    assert not vd.valider_exemple(exemple, rapport, "essai:1")
    assert "raisonnement absent sur une capacité raisonnée" in rapport.refus


def test_une_capacite_courte_sans_raisonnement_est_acceptee(exemple_valide):
    """`reponse` et `clarification` sont courtes par nature : leur imposer un
    raisonnement produirait du remplissage."""
    rapport = vd.Rapport()
    rapport.lus = 1
    assert vd.valider_exemple(exemple_valide, rapport, "essai:1")
    assert not rapport.refus


def test_une_ligne_illisible_est_un_refus_compte_pas_une_exception(tmp_path):
    chemin = tmp_path / "x.jsonl"
    chemin.write_text('{"id": "ok"\n', encoding="utf-8")
    rapport = vd.Rapport()
    vd.lire(chemin, rapport)
    assert rapport.refus["JSON illisible"] == 1


def test_rien_ne_disparait_en_silence(tmp_path, exemple_valide):
    """Retenus + refusés = lus. Le même contrôle que la chaîne de données
    catalogue, pour la même raison."""
    chemin = _ecrire(tmp_path / "x.jsonl",
                     [exemple_valide, exemple_valide | {"id": ""},
                      exemple_valide | {"capacite": "n'importe quoi"}])
    rapport = vd.Rapport()
    vd.lire(chemin, rapport)
    assert rapport.lus == 3
    assert rapport.coherent


# --- La fuite entre entraînement et essai -----------------------------------

def test_un_exemple_d_essai_present_a_l_entrainement_est_une_fuite(exemple_valide):
    entrainement = [exemple_valide | {"id": "train-1"}]
    essai = [exemple_valide | {"id": "test-1"}]
    fuites = vd.detecter_fuite(entrainement, essai)
    assert len(fuites) == 1
    assert "test-1" in fuites[0] and "train-1" in fuites[0]


def test_la_fuite_se_detecte_malgre_la_casse_et_les_espaces(exemple_valide):
    """Renommer un exemple ou changer sa ponctuation ne le rend pas nouveau."""
    entrainement = [exemple_valide | {"id": "train-1"}]
    essai = [exemple_valide | {"id": "test-1",
                               "user": "  C'EST QUOI   une Sous-Couche ?  "}]
    assert vd.detecter_fuite(entrainement, essai)


def test_deux_exemples_differents_ne_sont_pas_une_fuite(exemple_valide):
    entrainement = [exemple_valide | {"id": "train-1"}]
    essai = [exemple_valide | {"id": "test-1", "user": "et une sous-couche sur du bois ?"}]
    assert vd.detecter_fuite(entrainement, essai) == []


def test_une_fuite_invalide_le_dataset_entier(tmp_path, exemple_valide):
    _ecrire(tmp_path / "e.jsonl", [exemple_valide | {"id": "train-1"}])
    _ecrire(tmp_path / "t.jsonl", [exemple_valide | {"id": "test-1"}])
    rapport = vd.valider(tmp_path / "e.jsonl", tmp_path / "t.jsonl")
    assert not rapport.valide and rapport.fuites


# --- L'écart à la répartition cible -----------------------------------------

def test_l_ecart_a_la_cible_est_ecrit_sans_faire_echouer(tmp_path, exemple_valide):
    """Un dataset déséquilibré est un avertissement, pas une erreur : il se
    rééquilibre en écrivant des exemples, pas en bloquant la chaîne."""
    _ecrire(tmp_path / "e.jsonl",
            [exemple_valide | {"id": f"t-{n}"} for n in range(10)])
    rapport = vd.valider(tmp_path / "e.jsonl", tmp_path / "absent.jsonl")
    assert rapport.valide, "aucun exemple n'est fautif"
    assert any("devis" in ecart for ecart in rapport.ecarts)


# --- La préparation ne transforme rien --------------------------------------

def test_la_preparation_separe_le_raisonnement_de_la_reponse_finale():
    exemple = json.loads((RACINE / "dataset/gabarit.jsonl")
                         .read_text(encoding="utf-8").splitlines()[0])
    messages = preparer.convertir(exemple)["messages"]
    canaux = [m.get("channel") for m in messages if m["role"] == "assistant"]
    assert canaux == ["analysis", "final"]
    assert json.loads(messages[-1]["content"]) == exemple["final"]


def test_la_preparation_omet_le_canal_analysis_quand_il_n_y_a_pas_de_raisonnement(
        exemple_valide):
    messages = preparer.convertir(exemple_valide)["messages"]
    assert [m.get("channel") for m in messages if m["role"] == "assistant"] == ["final"]


# --- L'exécuteur ------------------------------------------------------------

def test_la_declaration_du_depot_se_lit_et_nomme_ses_etapes():
    chaine, etapes = exe.lire_declaration(RACINE / "mlops/pipeline.toml")
    assert chaine["nom"]
    assert [e.nom for e in etapes] == ["donnees", "preparation", "entrainement",
                                       "validation"]


def test_une_etape_dont_le_prerequis_manque_est_ignoree_pas_echouee(tmp_path):
    """La distinction porte tout le sens de la chaîne : l'entraînement n'a pas
    encore eu lieu, ce n'est pas un échec."""
    etape = exe.Etape("x", "d", "tools.mlops.preparer", [], ["absent.jsonl"], True)
    resultats = exe.executer([etape], tmp_path)
    assert resultats[0].etat == exe.IGNORE
    assert "absent.jsonl" in resultats[0].motif


def test_un_code_3_est_lu_comme_un_prerequis_absent(tmp_path):
    """Les étapes signalent elles-mêmes un prérequis manquant par le code 3 ;
    l'exécuteur ne doit pas le confondre avec un échec."""
    etape = exe.Etape("prep", "d", "tools.mlops.preparer",
                      ["--source", "absent.jsonl"], [], True)
    resultats = exe.executer([etape], RACINE)
    assert resultats[0].etat == exe.IGNORE
    assert resultats[0].code == 3


def test_une_etape_bloquante_en_echec_arrete_la_chaine(tmp_path):
    echec = exe.Etape("echec", "d", "tools.mlops.executer",
                      ["--declaration", "absent.toml"], [], True)
    suivante = exe.Etape("suite", "d", "tools.mlops.preparer", [], [], True)
    resultats = exe.executer([echec, suivante], RACINE)
    assert [r.etape for r in resultats] == ["echec"]
    assert resultats[0].etat == exe.ECHOUE


def test_la_simulation_ne_lance_rien(tmp_path):
    etape = exe.Etape("x", "d", "tools.mlops.preparer", [], [], True)
    resultats = exe.executer([etape], RACINE, simulation=True)
    assert resultats[0].etat == exe.IGNORE
    assert "simulation" in resultats[0].motif


def test_le_rapport_dit_si_la_chaine_a_tenu():
    chaine, _ = exe.lire_declaration(RACINE / "mlops/pipeline.toml")
    ignore = [exe.Resultat("a", exe.IGNORE, None, 0.0, "prérequis")]
    echoue = [exe.Resultat("a", exe.ECHOUE, 1, 0.0, "boum")]
    assert exe.rapport(chaine, ignore)["reussi"]
    assert not exe.rapport(chaine, echoue)["reussi"]


def test_les_hyperparametres_vivent_hors_du_code():
    """Les changer ne doit pas demander de modifier un script, et leur
    historique doit se lire dans git."""
    from tools.mlops.entrainer import lire_configuration
    reglages = lire_configuration(RACINE / "mlops/lora.toml")["lora"]
    for cle in ("modele_base", "rang", "alpha", "epoques", "graine"):
        assert cle in reglages
    assert reglages["alpha"] == 2 * reglages["rang"], "réglage usuel rompu sans note"


def test_l_entrainement_nomme_chaque_prerequis_manquant(tmp_path):
    """« Ça ne marche pas » n'aide personne : chaque manque est nommé."""
    from tools.mlops.entrainer import prerequis_manquants
    manquants = prerequis_manquants(tmp_path / "absente.toml", tmp_path / "absentes.jsonl")
    assert len(manquants) >= 2
    assert any("configuration" in m for m in manquants)
    assert any("données préparées" in m for m in manquants)


# --- La validation du modèle ------------------------------------------------

@pytest.mark.parametrize("sortie, invente", [
    ({"intent": "reponse", "payload": {"texte": "Un apprêt."}}, False),
    ({"intent": "reponse", "payload": {"texte": "Comptez 34,90 € le seau."}}, True),
    ({"intent": "devis", "payload": {"lignes": [{"prix: 12": 1}]}}, True),
    ({"intent": "devis", "payload": {"texte": "réf : ABC12345"}}, True),
    ({"intent": "devis", "payload": {"pieces": ["salon 20 m²"]}}, False),
])
def test_un_prix_ou_une_reference_dans_la_sortie_est_reperee(sortie, invente):
    """Métrique nº 7, seuil zéro : le modèle décrit, il ne chiffre pas. On
    cherche large — un faux positif à examiner coûte moins qu'un prix inventé
    qui passe."""
    from tools.mlops.evaluer import contient_prix_ou_reference
    assert contient_prix_ou_reference(sortie) is invente


def test_le_verdict_distingue_un_seuil_bloquant_d_un_seuil_indicatif():
    from tools.mlops.evaluer import verdict
    sous_le_seuil_bloquant = {"metriques": {1: 90.0}}      # nº 1 : min 98 %, bloquant
    sous_un_seuil_indicatif = {"metriques": {5: 50.0}}     # nº 5 : min 95 %, non bloquant
    tenu, manquements = verdict(sous_le_seuil_bloquant)
    assert not tenu and manquements
    tenu, manquements = verdict(sous_un_seuil_indicatif)
    assert tenu and manquements, "l'écart doit être écrit même s'il ne bloque pas"


def test_une_metrique_non_mesuree_ne_produit_aucun_verdict():
    """Un blanc assumé vaut mieux qu'un chiffre flatteur : une métrique absente
    ne doit ni passer, ni échouer."""
    from tools.mlops.evaluer import verdict
    tenu, manquements = verdict({"metriques": {1: None, 5: None}})
    assert tenu and manquements == []
