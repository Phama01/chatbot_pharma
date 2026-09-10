/*
 * Widget de l'assistant IA missionspharma.pro
 * Intégration : ajoute simplement <script src="chemin/vers/widget.js"></script>
 * juste avant </body> sur chaque page (landing + page annexe).
 */
(function () {
  // En local, la page de test est souvent servie sur http://localhost:5500,
  // tandis que le backend FastAPI tourne sur http://localhost:8000.
  // On pointe donc vers le bon backend selon le port utilisé.
  const API_URL = window.location.port === "5500"
    ? "http://localhost:8000/chat"
    : "/chat";
  const QUICK_PROMPTS = [
    "Comment ça marche ?",
    "Quel est le prix ?",
    "Quelles sont les fonctionnalités ?",
    "C’est quoi l’essai gratuit ?"
  ];

  const fonts = document.createElement("link");
  fonts.rel = "stylesheet";
  fonts.href = "https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Inter:wght@400;500;600&display=swap";
  document.head.appendChild(fonts);

  const style = document.createElement("style");
  style.textContent = `
    :root {
      --mp-forest-900: #14332A;
      --mp-forest-700: #1F4D3D;
      --mp-forest-600: #2B6A4F;
      --mp-mint-100: #E7F1E9;
      --mp-cream-50: #FBFAF6;
      --mp-ink-900: #17241D;
      --mp-ink-600: #4A594F;
      --mp-line: #DEE6DF;
      --mp-amber-500: #C98A2C;
    }

    #mp-launcher {
      position: fixed; bottom: 22px; right: 22px; width: 64px; height: 64px;
      border-radius: 50%; border: none; cursor: pointer; z-index: 9999;
      background: linear-gradient(155deg, var(--mp-forest-600), var(--mp-forest-900));
      box-shadow: 0 6px 20px rgba(20, 51, 42, 0.35);
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    #mp-launcher:hover { transform: scale(1.06) rotate(-2deg); box-shadow: 0 8px 24px rgba(20, 51, 42, 0.45); }
    #mp-launcher:focus-visible { outline: 2px solid var(--mp-amber-500); outline-offset: 3px; }
    #mp-launcher svg { width: 26px; height: 26px; }
    .mp-launcher-robot {
      position: absolute; right: 5px; bottom: 5px; width: 18px; height: 18px;
      border-radius: 50%; background: rgba(255,255,255,0.18);
      border: 1px solid rgba(255,255,255,0.5); display: flex;
      align-items: center; justify-content: center; font-size: 9px; line-height: 1;
      transition: transform 0.18s ease, background 0.18s ease;
    }
    #mp-launcher:hover .mp-launcher-robot {
      animation: mp-robot-bob 0.5s ease-in-out infinite alternate;
      background: rgba(255,255,255,0.28);
    }

    #mp-window {
      position: fixed; bottom: 92px; right: 22px; width: 480px; max-width: calc(100vw - 32px);
      height: 700px; max-height: 85vh; background: var(--mp-cream-50);
      border-radius: 18px; overflow: hidden; z-index: 9999;
      box-shadow: 0 20px 48px rgba(20, 51, 42, 0.22);
      display: none; flex-direction: column;
      font-family: 'Inter', system-ui, sans-serif;
      border: 1px solid var(--mp-line);
      transition: width 0.2s ease, height 0.2s ease;
    }

    #mp-window.mp-window-expanded {
      width: min(760px, calc(100vw - 32px));
      height: min(860px, calc(100vh - 40px));
    }

    #mp-header {
      background: var(--mp-forest-900); color: white;
      padding: 16px 18px; display: flex; align-items: center; gap: 10px;
      flex-shrink: 0;
    }
    #mp-header-mark {
      width: 30px; height: 30px; border-radius: 8px; background: rgba(255,255,255,0.12);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    #mp-header-mark svg { width: 16px; height: 16px; }
    #mp-header-text { flex: 1; min-width: 0; }
    #mp-header-title { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 14.5px; line-height: 1.2; }
    #mp-header-subtitle { font-size: 12px; color: rgba(255,255,255,0.68); margin-top: 2px; }
    #mp-close {
      background: none; border: none; color: rgba(255,255,255,0.75); cursor: pointer;
      width: 28px; height: 28px; border-radius: 6px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
    }
    #mp-close:hover { background: rgba(255,255,255,0.1); color: white; }

    #mp-toggle-size {
      background: none; border: none; color: rgba(255,255,255,0.75); cursor: pointer;
      width: 28px; height: 28px; border-radius: 6px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      margin-right: 4px;
    }
    #mp-toggle-size:hover { background: rgba(255,255,255,0.1); color: white; }

    #mp-messages {
      flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px;
    }
    #mp-suggestions {
      display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 12px 0;
      border-bottom: 1px solid var(--mp-line); background: white;
    }
    .mp-suggestion {
      border: 1px solid var(--mp-line); background: var(--mp-mint-100);
      color: var(--mp-forest-900); border-radius: 999px; padding: 7px 10px;
      font-size: 12px; cursor: pointer; transition: background 0.15s ease;
    }
    .mp-suggestion:hover { background: #dfeee2; }
    .mp-row { display: flex; }
    .mp-row.mp-user { justify-content: flex-end; }
    .mp-row.mp-bot { justify-content: flex-start; }

    .mp-bubble {
      max-width: 82%; padding: 10px 13px; font-size: 13.5px; line-height: 1.48;
      white-space: pre-wrap; word-wrap: break-word;
    }
    .mp-user .mp-bubble {
      background: var(--mp-forest-700); color: white;
      border-radius: 14px 14px 3px 14px;
    }
    .mp-bot .mp-bubble {
      background: var(--mp-mint-100); color: var(--mp-ink-900);
      border: 1px solid #D7E7DC;
      border-radius: 14px 14px 14px 3px;
    }

    .mp-sources {
      display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px; padding-left: 2px;
    }
    .mp-source-chip {
      font-size: 10.5px; color: var(--mp-ink-600); background: white;
      border: 1px solid var(--mp-line); border-radius: 20px; padding: 2px 9px;
    }

    .mp-typing { display: flex; gap: 4px; padding: 4px 2px; }
    .mp-typing span {
      width: 6px; height: 6px; border-radius: 50%; background: var(--mp-forest-600);
      opacity: 0.4; animation: mp-bounce 1.1s infinite ease-in-out;
    }
    .mp-typing span:nth-child(2) { animation-delay: 0.15s; }
    .mp-typing span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes mp-bounce {
      0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
      30% { transform: translateY(-4px); opacity: 1; }
    }
    @keyframes mp-robot-bob {
      0% { transform: translateY(0) rotate(-8deg); }
      100% { transform: translateY(-2px) rotate(8deg); }
    }

    #mp-input-row {
      display: flex; align-items: center; gap: 8px; padding: 12px;
      border-top: 1px solid var(--mp-line); background: white; flex-shrink: 0;
    }
    #mp-input {
      flex: 1; border: 1px solid var(--mp-line); border-radius: 22px;
      padding: 10px 15px; font-size: 13.5px; font-family: inherit; outline: none;
      background: var(--mp-cream-50); color: var(--mp-ink-900);
    }
    #mp-input:focus { border-color: var(--mp-forest-600); }
    #mp-send {
      width: 38px; height: 38px; border-radius: 50%; border: none; cursor: pointer;
      background: var(--mp-forest-700); color: white; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      transition: background 0.15s ease;
    }
    #mp-send:hover { background: var(--mp-forest-900); }
    #mp-send:disabled { background: #B7C4BC; cursor: default; }
    #mp-send svg { width: 15px; height: 15px; }

    @media (prefers-reduced-motion: reduce) {
      #mp-launcher, #mp-send { transition: none; }
      .mp-typing span { animation: none; opacity: 0.7; }
    }
  `;
  document.head.appendChild(style);

  const CROSS_ICON = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 3v18M3 12h18" stroke="currentColor" stroke-width="4.2" stroke-linecap="round"/>
  </svg>`;

  const launcher = document.createElement("button");
  launcher.id = "mp-launcher";
  launcher.setAttribute("aria-label", "Ouvrir l'assistant missionspharma.pro");
  launcher.innerHTML = `
    <span style="position:relative; display:flex; align-items:center; justify-content:center; width:100%; height:100%; color:white;">
      ${CROSS_ICON}
      <span class="mp-launcher-robot">🤖</span>
    </span>
  `;
  document.body.appendChild(launcher);

  if (document.querySelector(".scene-wrap")) {
    launcher.style.display = "none";
  }

  window.mpChatToggle = function () {
    if (launcher) {
      launcher.click();
    }
  };

  const win = document.createElement("div");
  win.id = "mp-window";
  win.setAttribute("role", "dialog");
  win.setAttribute("aria-label", "Assistant missionspharma.pro");
  win.innerHTML = `
    <div id="mp-header">
      <div id="mp-header-mark"><span style="color:white">${CROSS_ICON}</span></div>
      <div id="mp-header-text">
        <div id="mp-header-title">Assistant missionspharma.pro</div>
      </div>
      <button id="mp-toggle-size" aria-label="Agrandir ou réduire le chatbot">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M8 4h12v12M16 4L4 16M20 20H8V8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
      <button id="mp-close" aria-label="Fermer">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
    </div>
    <div id="mp-messages"></div>
    <div id="mp-suggestions"></div>
    <div id="mp-input-row">
      <input id="mp-input" type="text" placeholder="Pose ta question…" aria-label="Ta question" />
      <button id="mp-send" aria-label="Envoyer">
        <svg viewBox="0 0 24 24" fill="none"><path d="M4 12h15M13 6l6 6-6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </div>
  `;
  document.body.appendChild(win);

  const messagesEl = win.querySelector("#mp-messages");
  const suggestionsEl = win.querySelector("#mp-suggestions");
  const inputEl = win.querySelector("#mp-input");
  const sendBtn = win.querySelector("#mp-send");
  const closeBtn = win.querySelector("#mp-close");
  const toggleSizeBtn = win.querySelector("#mp-toggle-size");

  let ouvert = false;
  let premiereOuverture = true;
  let tailleEtendue = false;

  function ouvrirFermer() {
    ouvert = !ouvert;
    win.style.display = ouvert ? "flex" : "none";
    if (ouvert && premiereOuverture) {
      premiereOuverture = false;
      ajouterBulle(
        "bot",
        "Bonjour ! Je suis l'assistant PharmaBilan Pro. Je peux vous aider à découvrir la plateforme, ses fonctionnalités, l'essai gratuit, la sécurité et les tarifs. Que voulez-vous savoir ?"
      );
    }
    if (ouvert) inputEl.focus();
  }

  renderSuggestions();

  launcher.addEventListener("click", ouvrirFermer);
  closeBtn.addEventListener("click", ouvrirFermer);

  function basculerTaille() {
    tailleEtendue = !tailleEtendue;
    win.classList.toggle("mp-window-expanded", tailleEtendue);
    toggleSizeBtn.setAttribute("aria-label", tailleEtendue ? "Réduire le chatbot" : "Agrandir le chatbot");
  }

  toggleSizeBtn.addEventListener("click", basculerTaille);

  function ajouterBulle(role, texte, sources) {
    const row = document.createElement("div");
    row.className = `mp-row mp-${role === "user" ? "user" : "bot"}`;

    const wrapper = document.createElement("div");
    const bubble = document.createElement("div");
    bubble.className = "mp-bubble";
    bubble.textContent = texte;
    wrapper.appendChild(bubble);

    // Les sources restent côté backend pour la recherche, mais elles ne sont pas affichées dans le chat.

    row.appendChild(wrapper);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
  }

  function renderSuggestions() {
    suggestionsEl.innerHTML = QUICK_PROMPTS.map((prompt) => `
      <button type="button" class="mp-suggestion" data-prompt="${prompt}">${prompt}</button>
    `).join("");

    suggestionsEl.querySelectorAll(".mp-suggestion").forEach((button) => {
      button.addEventListener("click", () => {
        inputEl.value = button.dataset.prompt;
        envoyerQuestion();
      });
    });
  }

  function afficherFrappe() {
    const row = document.createElement("div");
    row.className = "mp-row mp-bot";
    row.id = "mp-typing-row";
    row.innerHTML = `<div class="mp-bubble"><div class="mp-typing"><span></span><span></span><span></span></div></div>`;
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function retirerFrappe() {
    const row = document.getElementById("mp-typing-row");
    if (row) row.remove();
  }

  async function envoyerQuestion() {
    const question = inputEl.value.trim();
    if (!question) return;
    ajouterBulle("user", question);
    inputEl.value = "";
    sendBtn.disabled = true;
    afficherFrappe();

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      retirerFrappe();
      if (res.ok) {
        ajouterBulle("bot", data.reponse, data.sources);
      } else {
        ajouterBulle("bot", "Désolé, une erreur est survenue. Réessaie plus tard.");
      }
    } catch (err) {
      retirerFrappe();
      ajouterBulle("bot", "Impossible de contacter l'assistant pour le moment.");
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener("click", envoyerQuestion);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") envoyerQuestion();
    if (e.key === "Escape") ouvrirFermer();
  });
})();
