"""La table de correspondance entre les lots du référentiel et les familles de
la base catalogue.

Deux vocabulaires se rencontrent ici, et ils n'ont pas été écrits ensemble :

- les **lots** (`app/referentiel.py`) découpent un *ouvrage* — « pose stratifié »,
  « sous-couche », « tableau électrique ». C'est la langue du chantier, celle que
  le modèle produit et que l'artisan reconnaît.
- les **familles** (`catalogue/catalogue.sqlite3`) regroupent des *matières*
  achetables — « SOL_STRATIFIE », « ELECTRICITE_TABLEAU ». C'est la langue du
  fournisseur, imposée par les sources de `docs/donnees/CHAINE_DONNEES.md`.

Ce fichier est le seul endroit où les deux se touchent, et il est **déclaratif à
dessein** : une correspondance devinée à l'exécution (par ressemblance de nom,
par distance d'édition) donnerait un prix sans jamais dire d'où il vient. Ici,
chaque ligne est écrite, datée par la revue, et porte son état.

**Trois états, pas deux.** Une correspondance est `ETABLIE` quand le lot et la
famille désignent la même chose ; elle est `ARBITRAGE_REQUIS` quand ils n'en
désignent pas tout à fait la même — et dans ce cas **elle ne sert pas**. C'est
la règle qui fait tenir le reste : chiffrer « un tableau électrique » au prix
d'un disjoncteur produirait un devis faux sans le signaler, ce qui est
exactement ce que ce projet refuse (`docs/produit/CADRAGE_MODELE.md` : zéro prix
inventé). Un lot en attente d'arbitrage retombe sur le catalogue simulé, et le
dit.

**Une famille n'est pas toujours homogène.** `ELECTRICITE_APPAREILLAGE` mélange
des prises de courant et des prises de communication : le moins cher du rayon y
est une RJ45, qui ne remplace pas une 2P+T. Un lot peut donc déclarer ce qu'il
`retient` dans sa famille — un filtre **écrit**, jamais deviné, et qui ne rend
rien plutôt que de rendre autre chose.

Trancher un `ARBITRAGE_REQUIS` n'est pas un travail de programmation : c'est
décider ce qu'on vend. Cela appartient à l'artisan, pas au code.
"""
from __future__ import annotations

from dataclasses import dataclass

ETABLIE = "etablie"
ARBITRAGE_REQUIS = "arbitrage_requis"


@dataclass(frozen=True)
class Correspondance:
    lot_code: str
    famille_code: str
    etat: str
    motif: str

    #: Fragments de libellé qui définissent ce que le lot retient dans sa
    #: famille, quand celle-ci n'est pas homogène. Vide = toute la famille.
    #: Si aucun produit ne correspond, le lot **ne prend rien** : une famille
    #: qui ne contient plus ce que le lot désigne doit se signaler, pas se
    #: remplacer par son plus proche voisin.
    retient: tuple[str, ...] = ()


#: Une entrée par lot du référentiel. Un lot absent de cette table n'a pas de
#: famille du tout — cas qui doit rester impossible, et qu'un test tient.
TABLE: dict[str, Correspondance] = {
    # --- Peinture : les trois lots ont leur famille, sans ambiguïté ---------
    "PEINT_PREP": Correspondance(
        "PEINT_PREP", "PEINTURE_PREPARATION", ETABLIE,
        "Enduits et rebouchage : même objet des deux côtés."),
    "PEINT_SOUS_COUCHE": Correspondance(
        "PEINT_SOUS_COUCHE", "PEINTURE_SOUS_COUCHE", ETABLIE,
        "Sous-couche : même objet des deux côtés."),
    "PEINT_FINITION": Correspondance(
        "PEINT_FINITION", "PEINTURE_FINITION", ETABLIE,
        "Peinture de finition : même objet des deux côtés."),

    # --- Sols ---------------------------------------------------------------
    "SOL_PREP": Correspondance(
        "SOL_PREP", "SOL_PREPARATION", ETABLIE,
        "Ragréage et primaire : même objet des deux côtés."),
    "SOL_SOUS_COUCHE": Correspondance(
        "SOL_SOUS_COUCHE", "SOL_SOUS_COUCHE", ETABLIE,
        "Sous-couche isolante : même objet des deux côtés."),
    "SOL_POSE_STRATIFIE": Correspondance(
        "SOL_POSE_STRATIFIE", "SOL_STRATIFIE", ETABLIE,
        "Stratifié au m². La famille SOL_PARQUET existe aussi, mais un "
        "parquet contrecollé n'est pas un stratifié : les deux ne se "
        "confondent pas, et le lot ne vise que le second."),
    "SOL_POSE_CARRELAGE": Correspondance(
        "SOL_POSE_CARRELAGE", "SOL_CARRELAGE", ETABLIE,
        "Carrelage au m² : même objet des deux côtés."),

    # --- Plomberie ----------------------------------------------------------
    "PLOMB_ALIM": Correspondance(
        "PLOMB_ALIM", "PLOMBERIE_ALIMENTATION", ETABLIE,
        "Tube d'alimentation au ml : même objet des deux côtés."),
    "PLOMB_EVAC": Correspondance(
        "PLOMB_EVAC", "PLOMBERIE_EVACUATION", ETABLIE,
        "Évacuation PVC au ml : même objet des deux côtés."),
    "PLOMB_APPAREIL": Correspondance(
        "PLOMB_APPAREIL", "PLOMBERIE_ROBINETTERIE", ARBITRAGE_REQUIS,
        "Le lot pose un **appareil sanitaire** (lavabo, WC, receveur) ; la "
        "famille ne contient que des **mitigeurs**. Chiffrer la pose d'un "
        "lavabo au prix d'un mitigeur donnerait un montant faux sans le dire. "
        "À trancher : soit la famille reçoit les appareils, soit le lot se "
        "scinde en « appareil » et « robinetterie »."),

    # --- Électricité --------------------------------------------------------
    "ELEC_GAINE": Correspondance(
        "ELEC_GAINE", "ELECTRICITE_CABLE", ETABLIE,
        "Gainage et câblage au ml. La matière chiffrée est le câble ; la "
        "gaine figure aux consommables du lot, pas à la ligne."),
    "ELEC_PRISE": Correspondance(
        "ELEC_PRISE", "ELECTRICITE_APPAREILLAGE", ETABLIE,
        "Prises à l'unité. La famille n'est pas homogène : elle mélange le "
        "courant fort (2P+T, étanche) et la communication (RJ45, USB-C). Le "
        "moins cher du rayon est une RJ45 à 7,60 €, qui n'alimente rien — la "
        "prendre pour une prise de courant serait une substitution muette. "
        "D'où le filtre : le lot ne retient que le courant fort.",
        retient=("2P+T", "étanche")),
    "ELEC_TABLEAU": Correspondance(
        "ELEC_TABLEAU", "ELECTRICITE_TABLEAU", ARBITRAGE_REQUIS,
        "Le lot pose **un tableau équipé** ; la famille ne contient que des "
        "**disjoncteurs** à l'unité. Le moins cher de la famille vaut 8,49 € : "
        "un devis qui annonce un tableau à ce prix est faux. À trancher : "
        "soit la famille reçoit les coffrets, soit le lot compte les modules."),
}

#: Familles de la base qu'aucun lot ne réclame. Les nommer évite de croire que
#: la base est intégralement exploitée : `SOL_PARQUET` est bien peuplée, mais le
#: référentiel n'a pas de lot « pose parquet ». Ouvrir ce lot est une décision
#: de périmètre métier, pas un correctif.
FAMILLES_SANS_LOT: tuple[str, ...] = ("SOL_PARQUET",)


def famille_de(lot_code: str) -> str | None:
    """La famille à interroger pour ce lot, ou `None`.

    `None` a deux causes, et elles se valent pour l'appelant : le lot est
    inconnu, ou sa correspondance attend un arbitrage. Dans les deux cas, la
    base ne doit pas être interrogée — et le prix ne viendra pas d'elle.
    """
    entree = TABLE.get(lot_code)
    if entree is None or entree.etat != ETABLIE:
        return None
    return entree.famille_code


def retenus_par(lot_code: str) -> tuple[str, ...]:
    """Les fragments de libellé que ce lot retient dans sa famille.

    Vide quand le lot prend toute la famille — le cas ordinaire, celui d'une
    famille homogène où seule la taille ou la finition varie.
    """
    entree = TABLE.get(lot_code)
    return entree.retient if entree is not None else ()


def convient(libelle: str, retient: tuple[str, ...]) -> bool:
    """Ce libellé entre-t-il dans ce que le lot retient ?

    Comparaison insensible à la casse, sur le libellé publié par la source :
    c'est la seule chaîne que le catalogue garantisse. Un filtre vide accepte
    tout, ce qui est la règle pour une famille homogène.
    """
    if not retient:
        return True
    minuscule = libelle.casefold()
    return any(fragment.casefold() in minuscule for fragment in retient)


def en_attente_d_arbitrage() -> list[Correspondance]:
    """Ce qui reste à trancher, pour le dire plutôt que de le laisser dormir."""
    return [c for c in TABLE.values() if c.etat == ARBITRAGE_REQUIS]
