"""US-25 — faire sortir le signal qualité du produit, sans le faire sortir de la machine.

Deux points de capture alimentent la boucle (`docs/produit/DISPOSITIF_AGENT.md` §5.2) :
la relecture de la dictée (HITL-0) et la correction de l'artisan (HITL-2). Tant
qu'ils restent en mémoire de session, ils ne servent à rien : §4.2 demande que
tout défaut constaté devienne un cas de non-régression, et §5.2 en fait la
matière première du réentraînement.

Ce module transforme donc les corrections en **candidats d'entraînement**, chacun
portant le triplet exigé par la story : ce que l'artisan a fourni, ce que la
chaîne a produit, ce que l'artisan a retenu. Sans les trois, un candidat n'a
aucune valeur d'entraînement : il est compté, pas exporté, et jamais jeté en
silence.

Deux invariants, tenus par le code et vérifiés par les tests :

1. **Le jeu ne rétrécit jamais.** L'export est en `append` seul, dédupliqué par
   empreinte du triplet. Un cas ajouté un vendredi est encore là le vendredi
   suivant, même si la session qui l'a produit a disparu.
2. **Rien ne quitte la machine.** La destination est vérifiée avant écriture :
   ni URL, ni chemin UNC, ni système de fichiers qui recopie ailleurs ce qu'on y
   écrit. Ce dépôt est lui-même sur un montage `fuse.rclone` synchronisé vers
   OneDrive — la destination par défaut est donc **hors du dépôt**, sur le disque
   local, et une destination dans le dépôt est refusée. Le refus est la bonne
   réponse : ces corrections portent des dictées de chantier et des noms de
   clients.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.pipeline import Session

# Systèmes de fichiers qui recopient ailleurs ce qu'on y écrit — réseau, montage
# distant, ou client de synchronisation. La liste est volontairement large : en
# cas de doute sur un montage, mieux vaut refuser un export que le laisser partir.
FS_NON_LOCAUX = {
    "nfs", "nfs4", "cifs", "smbfs", "smb3", "afs", "9p", "ceph", "glusterfs",
    "fuse.sshfs", "sshfs", "fuse.rclone", "fuse.davfs", "davfs", "davfs2",
    "ftpfs", "curlftpfs", "fuse.s3fs", "s3fs", "fuse.gcsfuse", "fuse.gvfsd-fuse",
    "fuse.mergerfs-remote",
}

# Hors du dépôt : le dépôt est synchronisé, le disque local ne l'est pas.
DESTINATION_DEFAUT = Path(
    os.environ.get("BTP_SIGNAL_QUALITE")
    or Path.home() / ".local" / "share" / "the-project" / "signal_qualite.jsonl"
)

TABLE_MONTAGES = Path("/proc/mounts")


class DestinationNonLocale(RuntimeError):
    """La destination demandée ferait sortir les corrections de la machine."""


# --------------------------------------------------------------------------
# Garde-fou de destination
# --------------------------------------------------------------------------

def _montages(table: Path | None = None) -> list[tuple[str, str]]:
    """(point de montage, type) lus dans /proc/mounts, du plus long au plus court.

    Absent ou illisible (autre système, conteneur restreint) : on rend une liste
    vide, et la vérification se rabat sur les seuls motifs de chemin."""
    chemin = table or TABLE_MONTAGES
    try:
        lignes = chemin.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    montages = []
    for ligne in lignes:
        champs = ligne.split()
        if len(champs) >= 3:
            # /proc/mounts échappe les espaces en \040.
            montages.append((champs[1].replace("\\040", " "), champs[2]))
    return sorted(montages, key=lambda m: len(m[0]), reverse=True)


def systeme_de_fichiers(chemin: Path, table: Path | None = None) -> str:
    """Type du système de fichiers portant ce chemin, « » si indéterminable.

    On remonte au premier parent existant : la destination n'est pas encore
    créée au moment où on la vérifie, c'est même le cas normal."""
    cible = Path(chemin).expanduser().resolve()
    while not cible.exists() and cible != cible.parent:
        cible = cible.parent
    texte = str(cible)
    for point, type_fs in _montages(table):
        if texte == point or texte.startswith(point.rstrip("/") + "/"):
            return type_fs
    return ""


def verifier_destination(chemin: Path | str, table: Path | None = None) -> Path:
    """Rend le chemin si — et seulement si — écrire dedans reste local."""
    texte = str(chemin)
    if "://" in texte:
        raise DestinationNonLocale(
            f"destination réseau refusée : {texte!r} — le signal qualité reste sur la machine")
    if texte.startswith("\\\\") or texte.startswith("//"):
        raise DestinationNonLocale(
            f"chemin UNC refusé : {texte!r} — le signal qualité reste sur la machine")
    type_fs = systeme_de_fichiers(Path(texte), table)
    if type_fs in FS_NON_LOCAUX:
        raise DestinationNonLocale(
            f"destination sur un montage synchronisé ou distant ({type_fs}) : {texte!r} — "
            "choisis un chemin sur le disque local (variable BTP_SIGNAL_QUALITE)")
    return Path(texte).expanduser()


# --------------------------------------------------------------------------
# Candidats
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Candidat:
    """Une correction rendue exploitable pour le réentraînement.

    Le triplet `entree` / `sortie_modele` / `corrige` est ce que la story exige :
    sans lui, on sait qu'un artisan a corrigé quelque chose, pas quoi."""
    horodatage: str
    projet_id: str
    origine: str
    entree: str
    sortie_modele: str
    corrige: str
    description: str

    @property
    def complet(self) -> bool:
        return bool(self.entree and self.sortie_modele and self.corrige)

    @property
    def cle(self) -> str:
        """Empreinte du triplet — ni horodatage ni projet.

        Deux artisans qui corrigent la même erreur du modèle produisent le même
        cas d'entraînement : le dédoublonner n'est pas perdre un signal, c'est
        éviter de peser deux fois le même exemple dans le jeu."""
        brut = "\x00".join([self.origine, self.entree, self.sortie_modele, self.corrige])
        return hashlib.sha256(brut.encode("utf-8")).hexdigest()[:32]

    def en_dict(self) -> dict:
        return {"cle": self.cle, "horodatage": self.horodatage,
                "projet_id": self.projet_id, "origine": self.origine,
                "entree": self.entree, "sortie_modele": self.sortie_modele,
                "corrige": self.corrige, "description": self.description}


def candidats_de_session(projet_id: str, session: Session) -> list[Candidat]:
    return [Candidat(horodatage=c.horodatage, projet_id=projet_id,
                     origine=c.origine or "inconnue", entree=c.entree,
                     sortie_modele=c.sortie_modele, corrige=c.corrige,
                     description=c.description)
            for c in session.corrections]


def candidats_du_disque(racine: Path | None = None) -> list[Candidat]:
    """Toutes les corrections de tous les projets persistés.

    Un fichier illisible ou tronqué ne fait pas échouer l'export : il est ignoré,
    les autres projets passent."""
    from app.persistance import RACINE_DONNEES, deserialiser_session

    dossier = Path(racine) if racine else RACINE_DONNEES
    if not dossier.is_dir():
        return []
    trouves: list[Candidat] = []
    for fichier in sorted(dossier.glob("*.json")):
        try:
            brut = json.loads(fichier.read_text(encoding="utf-8"))
            session = deserialiser_session(brut)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        trouves.extend(candidats_de_session(fichier.stem, session))
    return trouves


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

def cles_existantes(destination: Path) -> set[str]:
    try:
        lignes = Path(destination).read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    cles = set()
    for ligne in lignes:
        try:
            cles.add(json.loads(ligne)["cle"])
        except (ValueError, KeyError, TypeError):
            continue  # ligne tronquée par un arrêt brutal : on la laisse en place
    return cles


def exporter(candidats: list[Candidat], destination: Path | str | None = None,
             table: Path | None = None) -> dict:
    """Ajoute les candidats complets et inédits au jeu, sans jamais rien retirer.

    Ouverture en `append` seul : il n'existe aucun chemin de code qui tronque le
    fichier. Un cas entré au jeu y reste, même si le projet qui l'a produit est
    supprimé."""
    cible = verifier_destination(destination or DESTINATION_DEFAUT, table)
    connues = cles_existantes(cible)
    a_ecrire, incomplets, deja = [], 0, 0
    for candidat in candidats:
        if not candidat.complet:
            incomplets += 1
            continue
        if candidat.cle in connues:
            deja += 1
            continue
        connues.add(candidat.cle)
        a_ecrire.append(candidat)
    if a_ecrire:
        cible.parent.mkdir(parents=True, exist_ok=True)
        with cible.open("a", encoding="utf-8") as f:
            for candidat in a_ecrire:
                f.write(json.dumps(candidat.en_dict(), ensure_ascii=False) + "\n")
    return {"destination": str(cible), "ajoutes": len(a_ecrire),
            "deja_presents": deja, "incomplets": incomplets,
            "total_jeu": len(connues)}
