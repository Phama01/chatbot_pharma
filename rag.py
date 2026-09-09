"""
Module RAG - repris et adapté du notebook de l'atelier Machine Learnia.
Charge les PDF du dossier `documents/`, les découpe en passages, les vectorise,
et permet de rechercher les passages les plus pertinents pour une question.

Contrairement au notebook (qui recalculait tout à chaque exécution dans Colab),
ici l'index est construit une fois au démarrage du serveur et gardé en mémoire.
"""

import glob
import io
import os
import re
from collections import Counter

from pypdf import PdfReader

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")


def normaliser_texte(texte: str) -> str:
    return re.sub(r"\s+", " ", (texte or "")).strip()


def tokeniser(texte: str) -> list[str]:
    texte = normaliser_texte(texte.lower())
    return re.findall(r"[a-z0-9à-ü]+", texte)


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
    """Encapsule l'index documentaire et la recherche sur les passages PDF."""

    def __init__(self):
        self.documents: list[dict] = []

    def construire_index(self):
        """Lit tous les PDF de `documents/`, les découpe et prépare un index léger."""
        chemins = sorted(glob.glob(os.path.join(DOCUMENTS_DIR, "*.pdf")))
        if not chemins:
            raise RuntimeError(
                f"Aucun PDF trouvé dans {DOCUMENTS_DIR}. "
                "Ajoute tes guides pharmaciens dans ce dossier."
            )

        LIMITE_CARACTERES = 300_000

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
                if not passage.strip():
                    continue
                self.documents.append(
                    {
                        "titre": titre,
                        "texte": passage,
                        "tokens": tokeniser(passage),
                        "titre_tokens": tokeniser(titre),
                    }
                )

        print(f"✅ Index construit : {len(self.documents)} passages issus de {len(chemins)} PDF.")

    def chercher(self, question: str, k: int = 3) -> list[dict]:
        """Renvoie les k passages les plus pertinents en utilisant un score lexical simple."""
        if not self.documents:
            raise RuntimeError("L'index n'a pas été construit. Appelle construire_index() d'abord.")

        question_normalisee = normaliser_texte(question)
        question_tokens = tokeniser(question_normalisee)

        if not question_tokens:
            return [
                {
                    "titre": doc["titre"],
                    "texte": doc["texte"],
                    "score": 0.0,
                }
                for doc in self.documents[:k]
            ]

        question_counter = Counter(question_tokens)
        question_set = set(question_tokens)

        scores: list[dict] = []
        for doc in self.documents:
            passage_tokens = doc["tokens"]
            passage_counter = Counter(passage_tokens)
            titre_counter = Counter(doc["titre_tokens"])

            overlap_mots = sum(min(question_counter[token], passage_counter[token]) for token in question_counter)
            overlap_titre = sum(min(question_counter[token], titre_counter[token]) for token in question_counter)
            mots_communs = len(question_set & set(passage_tokens))
            titre_communs = len(question_set & set(doc["titre_tokens"]))
            phrase_presente = 1 if question_normalisee.lower() in doc["texte"].lower() else 0

            score = (
                overlap_mots * 3
                + overlap_titre * 5
                + mots_communs * 2
                + titre_communs * 4
                + phrase_presente * 3
            )

            scores.append(
                {
                    "titre": doc["titre"],
                    "texte": doc["texte"],
                    "score": float(score),
                }
            )

        scores.sort(key=lambda item: (-item["score"], item["titre"], item["texte"]))
        return scores[:k]
