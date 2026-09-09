"""
Backend FastAPI de l'assistant IA missionspharma.pro.

Au démarrage : construit l'index documentaire (RAG) à partir des PDF du dossier documents/.
Endpoint /chat : reçoit une question, cherche les passages pertinents, interroge Groq,
et renvoie la réponse accompagnée de ses sources.
"""

import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from groq import Groq
from pydantic import BaseModel

from rag import MoteurRAG

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODELE_GROQ = "openai/gpt-oss-20b"  # modèle rapide, gratuit en usage standard sur Groq

# Adapte cette liste à tes vrais domaines (landing page + page annexe sur missionspharma.pro)
ORIGINES_AUTORISEES = [
    "https://missionspharma.pro",
    "https://www.missionspharma.pro",
    "http://localhost:5500",  # pratique pour tester le widget en local
]

ROLE = """
Tu es l’assistant PharmaBilan Pro pour missionspharma.pro.

Ta mission : aider les pharmaciens à comprendre la plateforme, ses fonctionnalités, son essai gratuit et ses tarifs.

Règles absolues :
- Réponds en français, en texte simple, sans Markdown, sans tableaux, sans astérisques, sans listes longues.
- Réponds en 2 à 6 phrases maximum, sauf si l’utilisateur demande une explication détaillée.
- Ne parle jamais des documents, du contexte, du texte ou de la base de données.
- Ne réponds que sur le périmètre de PharmaBilan Pro et des guides fournis.
- Si une information n’est pas dans les guides, dis-le simplement et demande à contacter l’équipe à contact.pharmaservices@gmail.com.
- Si l’utilisateur dit bonjour, merci, ok ou fait une remarque générale, réponds naturellement et de façon courte.
- Si la question porte sur un âge précis, remplace-le par la bonne tranche d’âge.
- Si la question est hors sujet, recadre poliment vers la santé, la pharmacie ou la plateforme.
- Ne donne pas d’informations inventées. Si tu n’as pas la réponse, ne l’invente pas.

Ton style :
- Professionnel, clair, utile, chaleureux.
- Toujours orienté action.
- Termine souvent par une question courte si l’utilisateur peut avoir besoin d’autre chose.

Contenu à connaître :
- PharmaBilan Pro aide les pharmaciens à générer des bilans de prévention santé personnalisés et des bilans de grossesse.
- La plateforme propose des questionnaires conformes aux recommandations Ameli.
- Elle génère automatiquement un PPP en PDF.
- Elle propose des QR Codes pour le mode autonome ou le mode comptoir.
- Elle offre un dashboard avec statistiques, historique et suivi.
- L’essai gratuit dure 7 jours, sans carte bancaire.
- Après l’essai, il existe un abonnement mensuel (60 € HT/mois), un abonnement annuel (660 € HT/an, soit 1 mois offert) et un mode consommation (2 € HT par bilan).
- La plateforme est RGPD, sécurisée, et les données sensibles ne sont pas conservées.
- Les paiements sont sécurisés par Stripe.
- Attention : PharmaBilan Pro couvre les bilans de prévention santé et les bilans de grossesse. Elle ne propose pas d’entretiens réglementés AVK, AOD, asthme ou autres missions thématiques en dehors de ces bilans.

Réponds toujours avec un ton simple, direct et professionnel.
"""

app = FastAPI(title="Assistant IA missionspharma.pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINES_AUTORISEES,
    allow_methods=["POST"],
    allow_headers=["*"],
)

moteur = MoteurRAG()
client_groq = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


@app.on_event("startup")
def au_demarrage():
    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY n'est pas définie. Le endpoint /chat renverra une erreur tant "
              "qu'elle n'est pas configurée (voir README).")
    moteur.construire_index()


class Question(BaseModel):
    question: str


def nettoyer_reponse(reponse: str) -> str:
    if not reponse:
        return ""

    texte = reponse.replace("\u202f", " ").replace("\u00a0", " ")
    texte = texte.replace("\u2009", " ")

    lignes = []
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue

        if ligne.startswith("📎") or ligne.lower().startswith("sources:"):
            continue

        if ligne.startswith("#"):
            ligne = re.sub(r"^#+\s*", "", ligne)

        ligne = re.sub(r"^[-*]\s+", "", ligne)
        ligne = re.sub(r"^\d+\.\s+", "", ligne)
        ligne = re.sub(r"\*\*", "", ligne)
        ligne = ligne.replace("*", "")
        ligne = ligne.replace("_", "")
        ligne = ligne.replace("|", " ")
        ligne = re.sub(r"[ \t]{2,}", " ", ligne)
        lignes.append(ligne)

    texte = "\n".join(lignes).strip()
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    return texte.strip()


def est_question_sociale(question: str) -> bool:
    texte = re.sub(r"[^a-z0-9à-ü\s]", " ", question.strip().lower())
    texte = " ".join(texte.split())
    if not texte:
        return True

    messages_sociaux = {
        "bonjour",
        "salut",
        "merci",
        "merci beaucoup",
        "ok",
        "d accord",
        "c est bon",
        "ca marche",
        "ça marche",
        "ça va",
        "bien",
        "super",
    }

    return texte in messages_sociaux or texte.startswith("oui")


def est_confirmation(question: str) -> bool:
    texte = re.sub(r"[^a-z0-9à-ü\s]", " ", question.strip().lower())
    texte = " ".join(texte.split())
    confirmations = {"oui", "oui merci", "oui merci beaucoup", "d accord", "c est bon"}
    return texte in confirmations or texte.startswith("oui ")


@app.get("/")
def serve_frontend():
    return FileResponse("test.html")


@app.get("/widget.js")
def serve_widget_js():
    return FileResponse("widget.js")


@app.get("/health")
def sante():
    return {"status": "ok", "passages_indexes": len(moteur.documents)}


@app.post("/chat")
def chat(payload: Question):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="La question est vide.")
    if client_groq is None:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY non configurée côté serveur.")

    if est_question_sociale(question):
        if est_confirmation(question):
            reponse = (
                "Parfait, je peux vous guider. Pour démarrer l’essai gratuit, créez votre compte avec votre email professionnel, "
                "vérifiez votre adresse e-mail, puis vous aurez accès à toutes les fonctionnalités pendant 7 jours sans carte bancaire. "
                "Je peux aussi vous expliquer le parcours en détail."
            )
        else:
            reponse = (
                "Bonjour ! Je suis l'assistant PharmaBilan Pro. "
                "Je peux vous aider à découvrir la plateforme, ses fonctionnalités, l'essai gratuit, "
                "la sécurité et les tarifs. Que voulez-vous savoir ?"
            )
        return {
            "reponse": reponse,
            "sources": [],
        }

    passages = moteur.chercher(question, k=5)
    contexte = "\n\n".join(f"### {p['titre']}\n{p['texte']}" for p in passages)

    messages = [
        {"role": "system", "content": ROLE},
        {
            "role": "user",
            "content": (
                f"Documents disponibles :\n{contexte}\n\n"
                f"Question : {question}\n\n"
                "Utilise ces passages comme contexte principal pour répondre. "
                "Réponds en français, en texte simple, en 2 à 6 phrases maximum, sauf si l'utilisateur demande plus de détails. "
                "Si la réponse n'est pas présente ici, réponds simplement que tu n'as pas cette information sous les yeux et oriente vers contact.pharmaservices@gmail.com."
            ),
        },
    ]

    completion = client_groq.chat.completions.create(
        model=MODELE_GROQ,
        messages=messages,
        temperature=0.2,
        max_tokens=800,
        reasoning_effort="low",  # openai/gpt-oss-20b est un modèle "reasoning" : on limite
                                  # son raisonnement interne pour garder de la place pour la réponse
    )
    reponse = nettoyer_reponse(completion.choices[0].message.content)

    return {
        "reponse": reponse,
        "sources": [{"titre": p["titre"], "score": round(p["score"], 2)} for p in passages],
    }
