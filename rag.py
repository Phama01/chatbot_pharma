"""
Module RAG - repris et adapté du notebook de l'atelier Machine Learnia.
Charge les PDF du dossier `documents/`, les découpe en passages, les vectorise,
et permet de rechercher les passages les plus pertinents pour une question.

Contrairement au notebook (qui recalculait tout à chaque exécution dans Colab),
ici l'index est construit une fois au démarrage du serveur et gardé en mémoire.
"""

import io
import glob
import os

import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")
MODELE_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def extraire_texte_pdf(chemin_pdf: str) -> str:
    """Extrait tout le texte d'un PDF."""
    with open(chemin_pdf, "rb") as f:
        reader = PdfReader(io.BytesIO(f.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)


def decouper(texte: str, taille: int = 500, chevauchement: int = 80) -> list[str]:
    """Découpe un texte en passages d'environ `taille` caractères,
    en coupant de préférence en fin de phrase. (identique au notebook,
    avec un garde-fou anti-boucle-infinie en plus)"""
    texte = " ".join(texte.split())
    passages, debut = [], 0
    while debut < len(texte):
        fin = min(debut + taille, len(texte))
        if fin < len(texte):
            coupe = texte.rfind(". ", debut + taille // 2, fin)
            if coupe != -1:
                fin = coupe + 1
        passages.append(texte[debut:fin].strip())
        nouveau_debut = fin - chevauchement
        # Garde-fou : si le curseur n'avance pas (texte pathologique), on force l'avancée
        # pour éviter une boucle infinie qui remplirait la mémoire.
        debut = nouveau_debut if nouveau_debut > debut else debut + max(taille, 1)
    return [p for p in passages if p]


class MoteurRAG:
    """Encapsule l'index documentaire et la recherche sémantique."""

    def __init__(self):
        self.encodeur = SentenceTransformer(MODELE_EMBEDDINGS)
        self.documents: list[dict] = []
        self.vecteurs: np.ndarray | None = None

    def construire_index(self):
        """Lit tous les PDF de `documents/`, les découpe et calcule les embeddings."""
        chemins = sorted(glob.glob(os.path.join(DOCUMENTS_DIR, "*.pdf")))
        if not chemins:
            raise RuntimeError(
                f"Aucun PDF trouvé dans {DOCUMENTS_DIR}. "
                "Ajoute tes guides pharmaciens dans ce dossier."
            )

        LIMITE_CARACTERES = 300_000  # garde-fou : au-delà, un PDF est très probablement corrompu

        self.documents = []
        for chemin in chemins:
            titre = os.path.splitext(os.path.basename(chemin))[0]
            print(f"… lecture de {titre}", flush=True)
            try:
                texte = extraire_texte_pdf(chemin)
            except Exception as e:
                print(f"⚠️  Impossible de lire {titre} ({e}) — ce PDF est ignoré.")
                continue

            if len(texte) > LIMITE_CARACTERES:
                print(
                    f"⚠️  {titre} contient {len(texte):,} caractères extraits, ce qui est "
                    "anormalement élevé (PDF probablement corrompu ou mal scanné). "
                    f"Le texte est tronqué aux {LIMITE_CARACTERES:,} premiers caractères. "
                    "Envisage de remplacer ce fichier."
                )
                texte = texte[:LIMITE_CARACTERES]

            print(f"   → {len(texte):,} caractères extraits", flush=True)
            for passage in decouper(texte):
                self.documents.append({"titre": titre, "texte": passage})

        textes_a_encoder = [f"{d['titre']} - {d['texte']}" for d in self.documents]
        self.vecteurs = self.encodeur.encode(textes_a_encoder, normalize_embeddings=True)
        print(f"✅ Index construit : {len(self.documents)} passages issus de {len(chemins)} PDF.")

    def chercher(self, question: str, k: int = 3) -> list[dict]:
        """Renvoie les k passages les plus proches de la question."""
        if self.vecteurs is None:
            raise RuntimeError("L'index n'a pas été construit. Appelle construire_index() d'abord.")
        v_question = self.encodeur.encode(question, normalize_embeddings=True)
        similarites = self.vecteurs @ v_question
        indices = np.argsort(-similarites)[:k]
        return [
            {
                "titre": self.documents[i]["titre"],
                "texte": self.documents[i]["texte"],
                "score": float(similarites[i]),
            }
            for i in indices
        ]
