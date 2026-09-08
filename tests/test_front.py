"""Contrôles d'accessibilité sur le front mono-fichier (RGAA 4.1).

Ces tests ne remplacent pas un audit — ils attrapent les régressions les moins
coûteuses à détecter : un champ sans étiquette, un groupe de boutons radio sans
`<fieldset>`, un bouton dépliant sans `aria-expanded`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"


@pytest.fixture(scope="module")
def html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_la_langue_de_la_page_est_declaree(html):
    assert '<html lang="fr">' in html


def test_chaque_champ_de_saisie_porte_une_etiquette(html):
    """RGAA 11.1 — un champ sans <label for> n'est pas annoncé par un lecteur
    d'écran."""
    etiquetes = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', html))
    for balise in re.findall(r"<input[^>]*>", html):
        if 'type="hidden"' in balise:
            continue
        identifiant = re.search(r'\bid="([^"]+)"', balise)
        assert identifiant, f"champ sans id : {balise}"
        assert identifiant.group(1) in etiquetes or "aria-label" in balise, (
            f"champ sans étiquette : {identifiant.group(1)}")


def test_les_boutons_radio_sont_groupes_dans_un_fieldset_titre(html):
    """RGAA 11.5 — le choix du régime de TVA n'a de sens que groupé."""
    groupes = re.findall(r"<fieldset>(.*?)</fieldset>", html, re.S)
    radios = [g for g in groupes if 'type="radio"' in g]
    assert radios, "aucun groupe de boutons radio trouvé"
    for groupe in radios:
        assert "<legend>" in groupe


def test_le_depliant_du_profil_annonce_son_etat(html):
    """RGAA 7.1 — un bouton qui montre ou cache du contenu doit le dire."""
    bouton = re.search(r'<button id="btn-profil"[^>]*>', html)
    assert bouton and "aria-expanded" in bouton.group(0)
    assert 'aria-controls="profil-form"' in bouton.group(0)


def test_l_alerte_des_mentions_manquantes_est_une_region_de_statut(html):
    balise = re.search(r'<p class="alerte" id="alerte-mentions"[^>]*>', html)
    assert balise, "la zone d'alerte des mentions a disparu"
    assert 'role="status"' in balise.group(0)
    assert 'tabindex="-1"' in balise.group(0)  # pour y amener le focus après un 409


def test_aucun_champ_du_profil_n_est_laisse_sans_nom_cote_api(html):
    """Le formulaire est lu champ par champ en JavaScript : si un id change ici
    sans changer là, le profil part vide sans que rien ne le signale."""
    formulaire = re.search(r'<form class="profil".*?</form>', html, re.S).group(0)
    ids = set(re.findall(r'<input[^>]*\bid="(p-[^"]+)"', formulaire))
    script = html[html.index("<script>"):]
    lus = set(re.findall(r"'(p-[^']+)'", script))
    assert ids <= lus, f"champs jamais lus par le script : {sorted(ids - lus)}"


def test_la_dictee_est_relue_dans_un_textarea_etiquete(html):
    """US-05 — RGAA 11.1 : un `<textarea>` étiqueté, pas un `contenteditable`."""
    assert "contenteditable" not in html
    section = re.search(r'<section class="relecture".*?</section>', html, re.S)
    assert section, "la zone de relecture HITL-0 a disparu"
    zone = section.group(0)
    identifiant = re.search(r'<textarea[^>]*\bid="([^"]+)"', zone)
    assert identifiant, "le texte à relire doit être dans un textarea"
    assert f'for="{identifiant.group(1)}"' in zone
    assert "rows=" in zone  # dimensionné en lignes : suit le zoom texte à 200 %


def test_la_dictee_ne_part_pas_au_pipeline_sans_relecture(html):
    """La sortie de la reconnaissance vocale passe par /api/transcription."""
    script = html[html.index("<script>"):]
    onresult = re.search(r"reco\.onresult\s*=\s*\(e\)\s*=>\s*\{(.*?)\};", script, re.S)
    assert onresult, "le gestionnaire de dictée a changé de forme — à revérifier"
    corps = onresult.group(1)
    assert "relireDictee" in corps
    assert "/api/message" not in corps


def test_l_ecran_de_structure_ne_comporte_aucune_colonne_prix(html):
    """US-12 — « aucune colonne prix, même vide » avant validation."""
    script = html[html.index("<script>"):]
    entete = re.search(r"validee\s*\?\s*`(<table>.*?)`\s*:\s*'(<table>.*?)'",
                       script, re.S)
    assert entete, "les deux en-têtes de tableau ont changé de forme — à revérifier"
    structure = entete.group(2)
    for interdit in ("PU", "Total", "€", "TVA"):
        assert interdit not in structure, (
            f"l'écran de structure ne doit rien porter de monétaire : {interdit}")


def test_le_bouton_de_validation_porte_un_libelle_explicite(html):
    """RGAA 11.9 / WCAG 2.4.6 : compréhensible hors contexte, pas « Valider »."""
    assert "Valider la structure du devis" in html


def test_les_messages_de_cadrage_sont_annonces_en_role_alert(html):
    """US-20 — le message de cadrage doit être entendu, pas seulement affiché."""
    assert "data.cadrages" in html
    assert "'alert'" in html


def test_le_cadrage_reste_lisible_sans_couleur(html):
    """Préfixe en toutes lettres + repère de forme : la couleur ne porte
    aucune information à elle seule (RGAA 4.1, critère 3.1)."""
    assert "'Cadrage \u2014 '" in html
    debut = html.index(".msg.cadrage")
    style = html[debut:debut + 200]
    assert "border-left" in style or "font-style" in style


def test_la_demande_de_confirmation_est_annoncee_et_reliee_au_champ(html):
    """US-11 — RGAA 8.9 et 11.10 : role="alert" + aria-describedby sur la saisie."""
    assert 'id="zone-a-confirmer" role="alert"' in html
    assert "setAttribute('aria-describedby', 'zone-a-confirmer')" in html
    assert "removeAttribute('aria-describedby')" in html


def test_apres_rechargement_le_focus_va_sur_le_titre_du_devis(html):
    """US-16 — WCAG 2.4.3 : sinon l'artisan repart en tête de document."""
    assert '<h1 id="titre-devis" tabindex="-1">' in html
    assert "document.getElementById('titre-devis').focus()" in html


# --- tableau de bord d'exploitation (US-24) --------------------------------

PAGE_METRIQUES = PAGE.parent / "metriques.html"


@pytest.fixture(scope="module")
def metriques() -> str:
    return PAGE_METRIQUES.read_text(encoding="utf-8")


def test_le_tableau_de_bord_declare_sa_langue(metriques):
    assert '<html lang="fr">' in metriques


def test_les_donnees_sont_un_tableau_et_pas_un_graphique(metriques):
    """RGAA 1.x — pas d'image de graphe sans équivalent : ici, la donnée *est*
    le tableau, et chaque tableau porte un résumé et des en-têtes de portée."""
    assert metriques.count("<caption>") >= 2
    assert 'scope="col"' in metriques and 'scope="row"' in metriques
    assert "<canvas" not in metriques and "<img" not in metriques


def test_l_etat_d_une_metrique_est_ecrit_pas_seulement_colore(metriques):
    """La colonne « État » porte le mot ; la couleur n'est qu'un rappel."""
    assert "${m.statut}" in metriques
    assert "RGAA 3.1" in metriques


def test_l_echec_de_lecture_du_journal_est_annonce(metriques):
    assert 'role="alert"' in metriques
    assert ".catch(" in metriques


def test_l_assistant_donne_acces_au_tableau_de_bord(html):
    assert 'href="/metriques"' in html


# --------------------------------------------------------------------------
# US-23 — le panneau de connexion
# --------------------------------------------------------------------------

def test_le_panneau_de_connexion_est_un_formulaire(html):
    """Un vrai <form> : la touche Entrée le soumet, ce qui compte pour qui
    navigue au clavier (RGAA 4.1, critère 11.9)."""
    assert '<form class="connexion" id="connexion"' in html
    assert 'type="submit"' in html


def test_l_erreur_de_connexion_est_annoncee(html):
    """L'échec est porté par role="alert" et par du texte, jamais par la seule
    couleur (RGAA 4.1, critère 3.1)."""
    assert 'id="connexion-erreur" role="alert"' in html
    assert "Phrase de passe refusée" in html


def test_le_champ_de_phrase_est_etiquete_et_masque(html):
    assert 'for="connexion-phrase"' in html
    assert 'id="connexion-phrase"' in html and 'type="password"' in html
    assert 'autocomplete="current-password"' in html


def test_le_401_ramene_au_formulaire_quel_que_soit_l_appel(html):
    """L'interception est posée sur fetch lui-même : un appel ajouté plus tard
    ne peut pas oublier de la faire (US-23)."""
    assert "window.fetch = async" in html
    assert "reponse.status === 401" in html


def test_la_limite_de_tentatives_est_expliquee_a_l_ecran(html):
    assert "resp.status === 429" in html
    assert "Trop de tentatives" in html
