"""Export du devis en .docx, avec les mentions obligatoires BTP.

Deux règles gouvernent ce module (docs/CADRAGE_MODELE.md §6, docs/STORIES.md
US-15) :

1. **Une donnée légale manquante bloque l'export.** Produire un document
   incomplet serait produire un devis inopposable — pire qu'un refus, parce que
   l'artisan l'enverrait sans le savoir. L'appelant vérifie
   `app.profil.champs_manquants` avant d'appeler ici ; `generer_docx` lève
   `MentionsIncompletes` si on l'a oublié.
2. **En franchise en base (art. 293 B du CGI), le document ne porte aucune
   TVA** — ni colonne, ni ventilation, ni total TTC — seulement la mention
   légale. Ce n'est pas un détail d'affichage : un devis d'auto-entrepreneur qui
   affiche une TVA est faux.

La structure passe par `add_heading` et un vrai tableau à ligne d'en-tête :
l'export vers PDF produit alors un document balisé, exigence d'accessibilité du
projet (docs/ACCESSIBILITE_DOCUMENTS.md).
"""
from __future__ import annotations

import datetime as dt
import io

from docx import Document
from docx.shared import Pt

from app.devis import Devis
from app.gabarit import GABARIT_PAR_DEFAUT, Gabarit
from app.profil import MENTION_293B, Client, ProfilArtisan, champs_manquants


class MentionsIncompletes(Exception):
    """Il manque des mentions légales : le document ne peut pas être produit."""

    def __init__(self, manquants: list[str]):
        self.manquants = manquants
        super().__init__("mentions légales manquantes : " + ", ".join(manquants))


def generer_docx(devis: Devis, pieces: list[str], profil: ProfilArtisan,
                  client: Client, delai_execution: str,
                  aujourd_hui: dt.date | None = None,
                  gabarit: Gabarit | None = None,
                  numero_devis: str = "") -> bytes:
    """Le devis en `.docx`, dans l'ordre et sous les intitulés de l'artisan.

    Le `gabarit` (US-03) ne fait que **réordonner et renommer** les sections.
    Il ne peut pas en retirer : `Gabarit.ordre()` complète toujours par les
    blocs absents, sans quoi un ancien devis mal fichu ferait disparaître des
    mentions obligatoires du devis suivant.
    """
    gabarit = gabarit or GABARIT_PAR_DEFAUT
    manquants = champs_manquants(profil, client, delai_execution)
    if manquants:
        raise MentionsIncompletes(manquants)

    jour = aujourd_hui or dt.date.today()
    franchise = profil.en_franchise
    doc = Document()

    titre = doc.add_heading("Devis", level=1)
    titre.runs[0].font.size = Pt(20)

    def bloc_identification() -> None:
        doc.add_heading(gabarit.libelle("identification"), level=2)
        # Le numéro vient du projet (US-17). À défaut — un appel direct, hors
        # de l'application — on en dérive un du jour plutôt que d'en inventer
        # un fixe : deux devis du même jour portaient le même « -001 ».
        doc.add_paragraph(
            f"N° de devis : {numero_devis or f'DEV-{jour:%Y%m%d}-000000'}")
        doc.add_paragraph(f"Date d'émission : {jour:%d/%m/%Y}")
        doc.add_paragraph(
            f"Date de validité : {jour + dt.timedelta(days=30):%d/%m/%Y}")

    def bloc_prestataire() -> None:
        doc.add_heading(gabarit.libelle("prestataire"), level=2)
        doc.add_paragraph(f"Raison sociale : {profil.raison_sociale}")
        doc.add_paragraph(f"Adresse : {profil.adresse}")
        doc.add_paragraph(f"SIRET : {profil.siret}")
        doc.add_paragraph(f"RCS : {profil.rcs}")
        doc.add_paragraph(f"Code APE/NAF : {profil.ape_naf}")
        if not franchise:
            doc.add_paragraph(
                f"N° de TVA intracommunautaire : {profil.tva_intracommunautaire}")
        decennale = profil.decennale
        doc.add_paragraph(
            f"Assurance décennale : {decennale.assureur}, contrat "
            f"{decennale.numero_contrat} — couverture : {decennale.couverture_geographique}"
        )
        if decennale.perimee(jour):
            # On signale sans bloquer : l'artisan reste maître de l'émission
            # (docs/STORIES.md US-02, scénario 3).
            doc.add_paragraph(
                f"Attention : attestation décennale expirée depuis le "
                f"{decennale.valide_jusqu_au:%d/%m/%Y}."
            )

    def bloc_client() -> None:
        doc.add_heading(gabarit.libelle("client"), level=2)
        doc.add_paragraph(f"Client : {client.nom}")
        doc.add_paragraph(f"Adresse du chantier : {client.adresse_chantier}")
        if pieces:
            doc.add_paragraph(f"Pièces concernées : {', '.join(pieces)}")
        doc.add_paragraph(f"Délai d'exécution : {delai_execution}")

    def bloc_postes() -> None:
        doc.add_heading(gabarit.libelle("postes"), level=2)
        # Une remise du catalogue s'applique au total sans se voir dans le prix
        # unitaire : le lecteur verrait 2 × 79,90 € donner 135,83 € sans
        # explication. Un devis dont une ligne ne se recalcule pas se lit comme
        # une erreur, et le client est en droit de vérifier chaque ligne. La
        # colonne n'apparaît que s'il y a une remise — sinon elle n'apprendrait
        # rien.
        remises = {id(l): (l.produit.promo_pct if l.produit else 0.0)
                   for l in devis.lignes}
        afficher_remise = any(remises.values())
        colonnes = ["Poste", "Quantité", "Prix unitaire" + ("" if franchise else " HT")]
        if afficher_remise:
            colonnes.append("Remise")
        if not franchise:
            colonnes.append("TVA")
        colonnes.append("Total" + ("" if franchise else " HT"))

        table = doc.add_table(rows=1, cols=len(colonnes))
        table.style = "Light Grid Accent 1"
        for i, texte in enumerate(colonnes):
            table.rows[0].cells[i].text = texte

        for ligne in devis.lignes:
            cellules = table.add_row().cells
            unite = ligne.produit.unite_vente if ligne.produit else ""
            valeurs = [
                ligne.produit.designation if ligne.produit else ligne.nom_lot,
                f"{ligne.quantite_achat} {unite}".strip(),
                f"{ligne.prix_unitaire_ht:.2f} €",
            ]
            if afficher_remise:
                remise = remises[id(ligne)]
                valeurs.append(f"− {remise * 100:.0f} %" if remise else "—")
            if not franchise:
                valeurs.append(f"{ligne.taux_tva} %")
            valeurs.append(f"{ligne.prix_ht:.2f} €")
            for i, valeur in enumerate(valeurs):
                cellules[i].text = valeur

    def bloc_montants() -> None:
        doc.add_heading(gabarit.libelle("montants"), level=2)
        if franchise:
            doc.add_paragraph(f"Total : {devis.total_ht:.2f} €").runs[0].bold = True
            doc.add_paragraph(MENTION_293B)
            acompte = round(devis.total_ht * 0.30, 2)
        else:
            for taux, montant in devis.ventilation_tva.items():
                doc.add_paragraph(f"TVA à {taux} % : {montant:.2f} €")
            doc.add_paragraph(f"Total HT : {devis.total_ht:.2f} €").runs[0].bold = True
            doc.add_paragraph(f"Total TVA : {devis.total_tva:.2f} €")
            doc.add_paragraph(f"Total TTC : {devis.total_ttc:.2f} €").runs[0].bold = True
            acompte = devis.acompte_30_pct
        doc.add_paragraph(f"Acompte demandé (30 %) : {acompte:.2f} €")

    def bloc_mentions() -> None:
        # Seul bloc qui peut ne rien émettre : il n'a de sens que s'il y a une
        # mention à porter. Un titre suivi de rien se lirait comme un oubli.
        if not devis.mentions:
            return
        doc.add_heading(gabarit.libelle("mentions"), level=2)
        if "forte" in devis.mentions:
            doc.add_paragraph("Certains postes relèvent d'un domaine réglementé "
                               "(gaz, électricité, structure) : à faire valider par un "
                               "professionnel qualifié avant intervention.")
        if "simple" in devis.mentions:
            doc.add_paragraph("Points de vigilance signalés sur certains postes — "
                               "voir échanges avec l'artisan.")

    def bloc_accord() -> None:
        doc.add_heading(gabarit.libelle("accord"), level=2)
        doc.add_paragraph(
            "Bon pour accord (date et signature) : _______________________")

    # L'ordre vient du gabarit ; les blocs qu'il ignore restent émis à leur
    # place par défaut, un devis amputé n'étant plus un devis.
    ecrivains = {
        "identification": bloc_identification,
        "prestataire": bloc_prestataire,
        "client": bloc_client,
        "postes": bloc_postes,
        "montants": bloc_montants,
        "mentions": bloc_mentions,
        "accord": bloc_accord,
    }
    for nom in gabarit.ordre():
        ecrivains[nom]()

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
