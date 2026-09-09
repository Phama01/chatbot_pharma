# Assistant IA missionspharma.pro

RAG maison (comme dans l'atelier), mais persistant et en ligne 24/7.

## Structure du projet

```
missionspharma-chatbot/
├── documents/        ← mets tes PDF pharmaciens ici
├── rag.py            ← chunking + embeddings + recherche sémantique
├── main.py           ← backend FastAPI (endpoint /chat)
├── widget.js          ← widget à intégrer sur ton site
├── requirements.txt
└── .env               ← à créer toi-même (ne PAS committer sur GitHub)
```

## 1. Étape locale — tester avant de déployer

```bash
cd missionspharma-chatbot
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Crée un compte gratuit sur **console.groq.com**, génère une clé API, puis crée un fichier `.env` :

```
GROQ_API_KEY=ta_cle_ici
```

Mets 2-3 PDF de test dans `documents/`, puis lance le serveur :

```bash
uvicorn main:app --reload
```

Teste sur http://localhost:8000/docs (interface Swagger auto-générée par FastAPI) en essayant l'endpoint `/chat`.

## 2. Mettre le code sur GitHub

- Crée un repo (privé si tes documents sont sensibles).
- **Important** : ajoute un fichier `.gitignore` contenant au minimum :
  ```
  .env
  venv/
  __pycache__/
  ```
  Ta clé Groq ne doit **jamais** partir sur GitHub.
- Pousse le code + le dossier `documents/` (tes vrais PDF).

## 3. Déployer le backend gratuitement (Render.com)

1. Crée un compte sur render.com, "New Web Service", connecte ton repo GitHub.
2. Build command : `pip install -r requirements.txt`
3. Start command : `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Dans les "Environment Variables" de Render, ajoute `GROQ_API_KEY` avec ta clé.
5. Déploie. Note l'URL publique (ex. `https://missionspharma-chatbot.onrender.com`).

⚠️ Sur le plan gratuit, le service se met en veille après 15 min d'inactivité : le premier visiteur après une pause attendra ~30s. Normal pour démarrer.

## 4. Intégrer le widget sur ton site

Dans `widget.js`, remplace :
```js
const API_URL = "https://TON-BACKEND.onrender.com/chat";
```
par l'URL Render obtenue à l'étape 3.

Héberge `widget.js` (sur ton site, ou via GitHub Pages / CDN comme jsDelivr en pointant vers ton repo GitHub), puis ajoute sur **chaque page** de missionspharma.pro, juste avant `</body>` :

```html
<script src="https://cdn.jsdelivr.net/gh/TON-USER/TON-REPO@main/widget.js"></script>
```

(Si ton code est sur GitHub, jsDelivr sert automatiquement `widget.js` comme un CDN gratuit — pas besoin de l'héberger toi-même.)

## 5. Vérifier que tout marche

- Ouvre missionspharma.pro, la bulle de chat 💬 doit apparaître en bas à droite.
- Pose une question dont tu connais la réponse dans tes documents.
- Vérifie dans `/health` (ex. `https://ton-backend.onrender.com/health`) que `passages_indexes` n'est pas à 0.

## Pour aller plus loin (une fois que ça marche)

- Rate limiting par IP (éviter qu'un visiteur épuise ton quota Groq gratuit).
- Historique de conversation (actuellement chaque question est indépendante).
- Logs des questions posées, pour voir ce que cherchent réellement tes visiteurs.
