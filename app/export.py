"""Export du devis en .docx — reprend les mentions obligatoires BTP
(docs/CADRAGE_MODELE.md §6). Le SIRET/RCS/décennale sont des placeholders ici :
en production ils viennent du profil artisan, auto-remplis via l'API Pappers,
jamais produits par le modèle.
"""
from __future__ import annotations

import datetime as dt
import io

from docx import Document
from docx.shared import Pt

from app.devis import Devis

PLACEHOLDER_ARTISAN = {
    "raison_sociale": "[Raison sociale artisan — à renseigner]",
    "siret": "[SIRET — auto-rempli via API Pappers]",
    "assurance_decennale": "[Assureur et n° de contrat décennale]",
}


def generer_docx(devis: Devis, pieces: list[str]) -> bytes:
    doc = Document()

    titre = doc.add_heading("Devis", level=1)
    titre.runs[0].font.size = Pt(20)

    doc.add_paragraph(f"N° de devis : DEV-{dt.date.today():%Y%m%d}-001")
    doc.add_paragraph(f"Date d'émission : {dt.date.today():%d/%m/%Y}")
    doc.add_paragraph(f"Date de validité : {dt.date.today() + dt.timedelta(days=30):%d/%m/%Y}")
    doc.add_paragraph(f"Prestataire : {PLACEHOLDER_ARTISAN['raison_sociale']}")
    doc.add_paragraph(f"SIRET : {PLACEHOLDER_ARTISAN['siret']}")
    doc.add_paragraph(f"Assurance décennale : {PLACEHOLDER_ARTISAN['assurance_decennale']}")
    if pieces:
        doc.add_paragraph(f"Chantier : {', '.join(pieces)}")

    doc.add_heading("Détail des postes", level=2)
    table = doc.add_table(rows=1, cols=5)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, texte in enumerate(["Poste", "Quantité", "Prix unitaire HT", "TVA", "Total HT"]):
        hdr[i].text = texte

    for ligne in devis.lignes:
        row = table.add_row().cells
        row[0].text = ligne.produit.designation if ligne.produit else ligne.nom_lot
        row[1].text = f"{ligne.quantite_achat} {ligne.produit.unite_vente if ligne.produit else ''}"
        row[2].text = f"{ligne.prix_unitaire_ht:.2f} €"
        row[3].text = f"{ligne.taux_tva} %"
        row[4].text = f"{ligne.prix_ht:.2f} €"

    doc.add_heading("Ventilation TVA", level=2)
    for taux, montant in devis.ventilation_tva.items():
        doc.add_paragraph(f"TVA à {taux} % : {montant:.2f} €")

    doc.add_paragraph()
    doc.add_paragraph(f"Total HT : {devis.total_ht:.2f} €").runs[0].bold = True
    doc.add_paragraph(f"Total TVA : {devis.total_tva:.2f} €")
    doc.add_paragraph(f"Total TTC : {devis.total_ttc:.2f} €").runs[0].bold = True
    doc.add_paragraph(f"Acompte demandé (30 %) : {devis.acompte_30_pct:.2f} €")

    if devis.mentions:
        doc.add_heading("Mentions particulières", level=2)
        if "forte" in devis.mentions:
            doc.add_paragraph("Certains postes relèvent d'un domaine réglementé "
                               "(gaz, électricité, structure) : à faire valider par un "
                               "professionnel qualifié avant intervention.")
        if "simple" in devis.mentions:
            doc.add_paragraph("Points de vigilance signalés sur certains postes — "
                               "voir échanges avec l'artisan.")

    doc.add_paragraph()
    doc.add_paragraph("Bon pour accord (date et signature) : _______________________")

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
