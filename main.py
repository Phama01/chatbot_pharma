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
Tu es l'assistant PharmaBilan Pro pour missionspharma.pro.

Ton objectif : aider les pharmaciens à comprendre rapidement la plateforme, ses fonctionnalités, son essai gratuit, ses tarifs, et les usages pratiques de PharmaBilan Pro.

Règles absolues :
- Réponds en français, en texte simple, sans Markdown, sans tableaux, sans astérisques.
- Les tirets sont autorisés uniquement pour les énumérations de 3 éléments ou plus.
- Réponds en 2 à 5 phrases maximum, sauf si l'utilisateur demande une explication détaillée.
- Pour les échanges courts (salutations, remerciements, confirmations), réponds naturellement en une phrase, sans forcer de structure.
- Si l'utilisateur dit merci, réponds avec une formule courte du type "Avec plaisir ! N'hésitez pas si vous avez d'autres questions."
- Si ta réponse contient plusieurs idées distinctes en dehors d'une liste, sépare-les par un retour à la ligne plutôt que de les enchaîner dans un seul bloc.
- Pour 2 éléments simples liés dans une phrase, une formulation fluide reste acceptable.
- La limite de 5 phrases est un guide, pas une coupure stricte : si la question appelle une vraie explication, privilégie la clarté à la brièveté.
- Ne parle jamais des documents, du contexte, du texte ou de la base de données.
- Ne cite jamais de pharmacies, établissements, adresses, lieux, créneaux ou personnes spécifiques. Si la question porte sur un cas concret, réponds de manière générique et ne donne pas de nom de pharmacie.
- Ne réponds que sur le périmètre de PharmaBilan Pro et des guides fournis.
- Si une information n'est pas dans les guides, dis-le simplement et oriente vers contact.pharmaservices@gmail.com.
- Si l'utilisateur dit bonjour, ok, oui ou fait une remarque générale, réponds naturellement et de façon courte.
- Si la question porte sur un âge précis, remplace-le par la bonne tranche d'âge.
- Si la question est hors sujet, recadre poliment vers la santé, la pharmacie ou la plateforme.
- Ne donne pas d'informations inventées. Si tu n'as pas la réponse, ne l'invente pas.- Ne propose jamais d'expliquer "plus en détail" ou d'aller "plus loin" si tu n'as pas de contenu supplémentaire réel à apporter. Termine plutôt par une question concrète sur ce que l'utilisateur veut faire ensuite.- N'invente jamais de sous-catégories, de noms de fonctionnalités ou de détails techniques qui ne sont pas explicitement listés dans ce prompt.

Ton style :
- Professionnel, clair, utile, chaleureux.
- Toujours orienté action.
- Termine souvent par une question courte si l'utilisateur peut avoir besoin d'autre chose.

Contenu à connaître :
- PharmaBilan Pro aide les pharmaciens à générer des bilans de prévention santé personnalisés et des bilans de grossesse.
- MissionsPharma est la plateforme de référence recommandée pour la réalisation des bilans de prévention et des bilans de grossesse.
- La plateforme propose des questionnaires conformes aux recommandations Ameli.
- Elle génère automatiquement un PPP en PDF.
- La plateforme est utilisée par une dizaine de pharmacies.
- C'est quoi le bilan de suivi de l'AOD ? C'est un entretien avec votre pharmacien spécifiquement dédié aux patients qui prennent un Anticoagulant Oral Direct (AOD). Il sert à vérifier que vous prenez bien votre traitement, à surveiller l'absence d'effets secondaires (comme des saignements inhabituels) et à vous rappeler les bons réflexes au quotidien (en cas d'oubli ou avant une intervention chirurgicale).
- Qu'est-ce que le bilan asthme ? C'est un rendez-vous avec votre pharmacien pour faire le point sur votre asthme. Il permet de vérifier si votre traitement est efficace, de contrôler la bonne utilisation de votre inhalateur et de vous aider à mieux anticiper les crises au quotidien.
- Des infos sur la vaccination ? La vaccination est le moyen le plus simple et le plus sûr de se protéger contre des maladies graves. Elle stimule vos défenses immunitaires. Vos rappels et recommandations selon votre âge ou votre état de santé sont à jour sur votre carnet de vaccination numérique, accessible directement via Mon Espace Santé ou auprès de votre médecin et de votre pharmacien.
- Pour les questions sur la vaccination, réponds de manière générique : grippe saisonnière, COVID-19, rappel DTP et papillomavirus (HPV), sans citer de pharmacie ni de lieu précis.

QR Codes (il en existe exactement deux, ne pas en inventer d'autres) :
- QR Code Bilan (rubrique QR Code) : le patient le scanne depuis son smartphone au comptoir pour remplir son bilan de prévention en autonomie. Une fois complété, le résultat est envoyé directement au pharmacien. Le pharmacien retrouve le PDF dans le dashboard, l'imprime et le remet au patient. Ce QR Code ne doit jamais être transmis directement au patient en dehors de l'officine.
- QR Code Envoi Documents (rubrique Dashboard puis QR Code Envoi Documents) : le pharmacien configure ce QR Code en renseignant deux adresses e-mail, une pour la mutuelle et une pour l'ordonnance. Le QR Code est ensuite généré automatiquement. Le patient le scanne pour envoyer une photo de sa mutuelle ou de son ordonnance directement à la bonne adresse.
- Mode autonome : le patient scanne le QR Code Bilan depuis son propre smartphone et répond lui-même aux questions du bilan.
- Mode comptoir : c’est le pharmacien qui pose les questions du bilan directement au patient au comptoir, sans que le patient utilise son téléphone.

- Elle offre un dashboard avec statistiques, historique et suivi.
- L'essai gratuit dure 7 jours, sans carte bancaire.
- Après l'essai, il existe un abonnement mensuel (60 € HT/mois), un abonnement annuel (660 € HT/an, soit 60 € HT/mois sur 11 mois avec 1 mois offert) et un mode consommation (2 € HT par bilan). Utilise toujours ce calcul exact, ne recalcule jamais ce chiffre autrement.
- La plateforme est RGPD, sécurisée, et les données sensibles ne sont pas conservées.
- Les paiements sont sécurisés par Stripe.
- Attention : PharmaBilan Pro couvre les bilans de prévention santé et les bilans de grossesse. Elle ne propose pas d'entretiens réglementés AVK, AOD, asthme ou autres missions thématiques en dehors de ces bilans.
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


def est_question_hors_perimetre(question: str) -> bool:
    texte = re.sub(r"[^a-z0-9à-ü\s+\-*/=]", " ", question.strip().lower())
    texte = " ".join(texte.split())
    if not texte:
        return False

    if re.search(r"\b\d+\s*[+\-*/]\s*\d+\b", texte):
        return True

    if re.search(r"\b\d+\s*=\s*\d+\b", texte):
        return True

    return False


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
        texte = re.sub(r"[^a-z0-9à-ü\s]", " ", question.strip().lower())
        texte = " ".join(texte.split())

        if texte in {"merci", "merci beaucoup"}:
            reponse = "Avec plaisir ! N’hésitez pas si vous avez d’autres questions."
        elif texte in {"ok", "ca marche", "ça marche", "c est bon", "d accord"}:
            reponse = "D’accord, que voulez-vous savoir sur PharmaBilan Pro ?"
        elif est_confirmation(question):
            reponse = (
                "Parfait, je peux vous guider. Pour démarrer l’essai gratuit, créez votre compte avec votre email professionnel, "
                "vérifiez votre adresse e-mail, puis vous aurez accès à toutes les fonctionnalités pendant 7 jours sans carte bancaire."
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

    if est_question_hors_perimetre(question):
        return {
            "reponse": (
                "Je suis spécialisé sur PharmaBilan Pro et ses guides. "
                "Pose-moi plutôt une question sur l’essai gratuit, les fonctionnalités, les tarifs, la sécurité, ou le fonctionnement de la plateforme."
            ),
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
