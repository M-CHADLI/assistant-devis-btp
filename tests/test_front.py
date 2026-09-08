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


def test_les_en_tetes_du_tableau_de_devis_portent_un_scope(html):
    """RGAA 5.7 — sans `scope`, un lecteur d'écran ne rattache pas une cellule à
    sa colonne, et le tableau se lit comme une suite de nombres."""
    entetes = re.findall(r"<th[^>]*>", html)
    assert entetes, "le tableau de devis a disparu"
    sans_scope = [e for e in entetes if "scope=" not in e and not re.match(r"<th\s*>", e)]
    assert not sans_scope, f"en-têtes sans scope : {sans_scope}"


def test_la_colonne_remise_n_apparait_que_s_il_y_a_une_remise(html):
    """Même règle que le .docx : la remise s'affiche pour que la ligne se
    recalcule, mais une colonne vide n'apprendrait rien."""
    assert "remise_pct > 0" in html
    assert "l.remise_pct.toFixed(0)" in html


def test_la_severite_d_une_mention_ne_se_devine_pas_dans_le_texte(html):
    """US-18 — la sévérité arrive du serveur dans `niveau`. La chercher dans la
    phrase (`startsWith('⚠️')`) liait la couleur d'un avertissement
    réglementaire à un caractère de ponctuation."""
    assert "startsWith('⚠️')" not in html
    assert "m.niveau === 'forte'" in html


def test_une_mention_ne_repose_pas_sur_la_seule_couleur(html):
    """RGAA 3.1 — le rouge et l'orange ne disent rien à qui ne les voit pas :
    le niveau est écrit en toutes lettres devant le message."""
    assert "'Réglementé — '" in html
    assert "'Vigilance — '" in html


def test_une_mention_forte_est_annoncee_immediatement(html):
    """RGAA 7.4 — un poste réglementé ne doit pas passer inaperçu : role=alert
    interrompt la lecture, role=status attend une pause."""
    bloc = html[html.index("(data.mentions || []).forEach"):]
    assert "'alert' : 'status'" in bloc[:600]


def test_une_contradiction_ne_se_lit_pas_comme_une_quantite_hors_bornes(html):
    """US-06 — l'artisan choisit entre deux valeurs qu'il a dictées ; lui parler
    de bornes du référentiel n'aurait aucun sens."""
    assert "a.motif === 'contradiction'" in html
    assert "au lieu de ${a.valeur_existante} déjà au devis" in html
    assert "Garder ${a.valeur_existante}" in html


# --- Dictée : ce qui sort de la machine (docs/RGPD.md, traitement T2) --------

def test_la_dictee_demande_le_traitement_sur_l_appareil(html):
    """Par défaut, la Web Speech API n'est pas locale : Chrome envoie l'audio à
    son service. Le front doit réclamer `processLocally` quand il existe, sinon
    la voix de l'artisan et le nom de son client quittent le poste."""
    assert "'processLocally' in reco" in html, "aucune détection du traitement local"
    assert "reco.processLocally = true" in html, "le traitement local n'est pas demandé"


def test_le_recours_au_service_distant_exige_un_accord_explicite(html):
    """Le vrai défaut serait le repli silencieux. L'artisan fait autorité, y
    compris sur ce qu'il accepte d'envoyer hors de sa machine."""
    bloc = html[html.index("const btnDicter"):]
    assert "window.confirm(AVERTISSEMENT_DISTANT)" in bloc
    assert "sortent de cette machine" in bloc, "l'avertissement ne dit pas ce qui sort"
    assert bloc.count("reco.start()") == 1, (
        "un second point de démarrage contournerait la demande d'accord")


# --- Affichage sur téléphone (WCAG 2.1, critère 1.4.10) ---------------------

def test_les_panneaux_s_empilent_sur_un_ecran_etroit(html):
    """L'entrée du produit est la voix, dictée sur chantier : l'écran probable
    est un téléphone. Deux panneaux côte à côte y imposeraient un défilement à
    deux dimensions, que le critère « Reflow » interdit."""
    debut = html.index("@media (max-width: 45rem)")
    bloc = html[debut:html.index("}", html.index(".fil { min-height", debut))]
    assert "flex-direction: column" in bloc, "les panneaux ne s'empilent pas"
    assert "height: auto" in bloc, "une hauteur fixe rognerait le contenu empilé"


def test_les_cibles_tactiles_font_au_moins_44_pixels(html):
    """RGAA 4.1, critère 10.11 : une cible pointée sous 44 px se rate avec des
    gants. La règle vaut pour tous les boutons, pas seulement les principaux."""
    regle = html[html.index("  button { cursor: pointer;"):]
    regle = regle[:regle.index("}")]
    assert "min-height:44px" in regle and "min-width:44px" in regle


# --- Propriétés d'accessibilité annotées sur les maquettes ------------------
# docs/MAQUETTES.md renvoie à ces tests : une annotation de maquette qui n'est
# tenue par rien décrit une intention, pas un contrat.

def test_le_lien_d_evitement_est_le_premier_element_focalisable(html):
    """RGAA 4.1, critère 12.7. Un lien d'évitement placé après la barre
    d'actions ne sert à rien : il faut déjà l'avoir traversée pour l'atteindre."""
    corps = html[html.index("<body"):]
    positions = [corps.index(balise) for balise in
                 ("<a ", "<button", "<input", "<textarea", "<select")
                 if balise in corps]
    premier = corps[min(positions):min(positions) + 120]
    assert "lien-evitement" in premier, (
        f"le premier élément focalisable n'est pas le lien d'évitement : {premier[:60]}")
    assert 'href="#contenu"' in premier, "le lien d'évitement ne vise pas le contenu"


def test_le_lien_d_evitement_redevient_visible_a_la_prise_de_focus(html):
    """Masqué hors focus, il doit réapparaître au clavier — sinon c'est un lien
    invisible pour tout le monde, y compris pour qui en a besoin."""
    assert ".lien-evitement:focus" in html
    regle = html[html.index(".lien-evitement:focus"):]
    assert "position:static" in regle[:regle.index("}")]


def test_le_fil_de_conversation_est_une_region_vivante(html):
    """Les réponses arrivent après coup. Sans `aria-live`, un lecteur d'écran
    ne les annonce jamais : l'artisan parle dans le vide."""
    ligne = [l for l in html.splitlines() if 'id="fil"' in l][0]
    assert 'aria-live="polite"' in ligne, "le fil n'est pas annoncé"
    assert 'aria-atomic="false"' in ligne, "tout le fil serait relu à chaque ajout"


def test_la_modale_piege_le_focus_et_le_rend(html):
    """RGAA 4.1, critère 7.3. Un focus qui s'échappe derrière une modale laisse
    l'utilisateur au clavier sans moyen de revenir."""
    assert 'aria-modal="true"' in html
    bloc = html[html.index("function fermerModal"):]
    assert "elementAvantModal" in bloc, "le focus n'est pas rendu à son origine"
    assert "e.key === 'Escape'" in html, "Échappement ne ferme pas la modale"
    piege = html[html.index("if (e.key === 'Escape')"):]
    assert "e.preventDefault(); last.focus()" in piege, "le focus sort par le haut"
    assert "e.preventDefault(); first.focus()" in piege, "le focus sort par le bas"


# --------------------------------------------------------------------------
# US-01 — pré-remplissage par SIRET : l'accessibilité au même rang que le reste
# --------------------------------------------------------------------------

def test_le_champ_siret_est_relie_a_son_aide_et_a_son_erreur(html):
    """RGAA 11.10 / WCAG 3.3.3 — un message d'erreur non rattaché au champ
    n'est jamais lu au bon moment par un lecteur d'écran."""
    champ = re.search(r'<input[^>]*id="p-siret"[^>]*>', html)
    assert champ, "le champ SIRET a disparu"
    decrit = re.search(r'aria-describedby="([^"]+)"', champ.group(0))
    assert decrit, "le champ SIRET ne cite ni aide ni erreur"
    for identifiant in decrit.group(1).split():
        assert f'id="{identifiant}"' in html, (
            f"aria-describedby cite « {identifiant} », qui n'existe pas")


def test_la_bascule_en_saisie_manuelle_est_annoncee(html):
    """WCAG 4.1.3 — le passage en saisie manuelle change ce que l'artisan doit
    faire ; l'afficher sans l'annoncer laisse un utilisateur non voyant devant
    un formulaire qui ne se remplira jamais."""
    region = re.search(r'<p[^>]*id="siret-retour"[^>]*>', html)
    assert region, "pas de zone de retour pour la recherche SIRET"
    assert 'aria-live="polite"' in region.group(0)


def test_l_erreur_de_siret_est_une_alerte_et_ne_tient_pas_a_la_couleur(html):
    """RGAA 3.1 — la couleur seule ne porte jamais une information."""
    erreur = re.search(r'<p[^>]*id="siret-erreur"[^>]*>', html)
    assert erreur and 'role="alert"' in erreur.group(0)
    # Le script préfixe le message d'un signe : le texte suffit à lui seul.
    assert "'⚠ ' + message" in html


def test_le_champ_invalide_est_marque_pour_les_technologies_d_assistance(html):
    assert "setAttribute('aria-invalid'" in html


def test_un_champ_prerempli_reste_modifiable(html):
    """Critère d'US-01 : « tout champ pré-rempli reste modifiable ». Un
    `readonly` posé pour « protéger » la donnée d'annuaire retirerait à
    l'artisan l'autorité que le cadrage lui donne."""
    for identifiant in ("p-raison", "p-siret", "p-adresse", "p-rcs", "p-ape",
                        "p-tvaintra"):
        champ = re.search(rf'<input[^>]*id="{identifiant}"[^>]*>', html)
        assert champ, f"champ {identifiant} introuvable"
        assert "readonly" not in champ.group(0)
        assert "disabled" not in champ.group(0)
    # Ni le balisage ni le script ne verrouillent l'un de ces six champs.
    # (Les boutons, eux, se désactivent le temps d'un appel : c'est autre chose.)
    for identifiant in ("p-raison", "p-siret", "p-adresse", "p-rcs", "p-ape",
                        "p-tvaintra"):
        assert f"'{identifiant}').readOnly" not in html
        assert f"'{identifiant}').disabled" not in html


def test_le_front_ignore_le_nom_de_l_annuaire(html):
    """Le navigateur parle au serveur, jamais au tiers : c'est ce qui garde la
    clé d'API hors de portée du client."""
    assert "pappers" not in html.lower()
    assert "api_token" not in html


def test_l_origine_d_un_champ_prerempli_est_visible_sans_etre_bloquante(html):
    assert "dataset.origine" in html
    assert "votre correction fait autorité" in html
