/* Cashflow Online — cliente */

let ws = null;
let yourId = null;
let roomId = null;
let isHost = false;
let state = null;
let seenMove = -1;
let animGuard = false;
let myProfessionChosen = false;
let lastCash = {};
let pendingFx = null;

const usd = new Intl.NumberFormat("es-AR", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function $(id) { return document.getElementById(id); }
function playerById(id) { return (state && state.players.find((p) => p.id === id)) || null; }
function me() { return playerById(yourId); }

/* ================= Conexión ================= */

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "joined") {
      yourId = msg.yourId;
      roomId = msg.roomId;
      isHost = msg.isHost;
      state = msg.state;
      $("lobby").classList.add("hidden");
      $("game").classList.remove("hidden");
      render();
    } else if (msg.type === "state") {
      state = msg.state;
      yourId = msg.yourId;
      render();
    } else if (msg.type === "error") {
      showError(msg.message);
    }
  };
  ws.onclose = () => {
    showError("Conexión perdida. Recargá la página.");
  };
}

function send(obj) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj));
}

/* ================= Render principal ================= */

function render() {
  if (!state) return;
  renderHeader();
  buildBoardIfNeeded();
  renderBoard();
  renderPlayers();
  renderLog();
  renderChat();
  renderDice();
  renderTurnPill();
  renderModal();
  state.players.forEach((p) => { lastCash[p.id] = p.cash; });
}

function renderHeader() {
  $("room-id").textContent = roomId;
  $("btn-copy-room").classList.toggle("hidden", !roomId);
  const startBtn = $("btn-start");
  const canStart = isHost && state.phase === "lobby" && state.players.length >= 2;
  startBtn.classList.toggle("hidden", !canStart);
  const hint = $("waiting-hint");
  if (state.phase === "lobby") {
    if (state.players.length < 2) {
      hint.classList.remove("hidden");
      hint.textContent = `Esperando jugadores… (mínimo 2). Compartí el código ${roomId} con un amigo.`;
    } else {
      hint.classList.add("hidden");
    }
  } else {
    hint.classList.add("hidden");
  }
  if (state.phase === "playing" || state.phase === "over") {
    const cur = state.players[state.turnIndex];
    $("turn-info").textContent = state.phase === "over" ? "🏆 ¡Juego terminado!" : (cur ? `Turno de: ${cur.name}` : "");
  } else {
    $("turn-info").textContent = state.phase === "selecting" ? "Eligiendo profesiones…" : "";
  }
}

/* ================= Tablero ================= */

let cellsBuilt = false;

function boardPos(n, i, radius) {
  const el = $("board");
  const W = el.clientWidth, H = el.clientHeight;
  const cx = W * 0.5, cy = H * 0.5;
  const R = radius * Math.min(W, H) * 0.5;
  const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
  return { x: cx + R * Math.cos(ang), y: cy + R * Math.sin(ang) };
}

function cellIcon(type) {
  const map = {
    PAYDAY: "💵", SMALL: "📗", BIG: "📘", MARKET: "📈", DOODAD: "🛍️",
    CHARITY: "🤝", BABY: "👶", DOWNSIZE: "💼", CASHFLOW: "💰", OPPORTUNITY: "💡",
    DREAM: "🌟",
  };
  return map[type] || "•";
}

function conicGradient(board, colors) {
  const n = board.length, seg = 360 / n;
  const stops = board.map((t, i) => `${colors[t]} ${(i * seg).toFixed(2)}deg ${((i + 1) * seg).toFixed(2)}deg`);
  return `conic-gradient(from -90deg, ${stops.join(", ")})`;
}

function buildBoardIfNeeded() {
  if (cellsBuilt) return;
  cellsBuilt = true;
  const board = $("board");

  const rw = document.createElement("div");
  rw.className = "wheel-ring rat";
  rw.style.background = conicGradient(state.ratBoard, state.boardMeta.ratColors);
  board.appendChild(rw);

  const fw = document.createElement("div");
  fw.className = "wheel-ring fast";
  fw.style.background = conicGradient(state.fastBoard, state.boardMeta.fastColors);
  board.appendChild(fw);

  state.ratBoard.forEach((t, i) => {
    const el = document.createElement("div");
    el.className = "wheel-label rl";
    el.dataset.i = i;
    el.innerHTML = `<span class="wli">${cellIcon(t)}</span>`;
    el.title = (state.ratLabels[t] || t).replace(/\n/g, " ");
    board.appendChild(el);
  });
  state.fastBoard.forEach((t, i) => {
    const el = document.createElement("div");
    el.className = "wheel-label fl";
    el.dataset.i = i;
    el.innerHTML = `<span class="wli">${cellIcon(t)}</span>`;
    el.title = (state.fastLabels[t] || t).replace(/\n/g, " ");
    board.appendChild(el);
  });

  const center = document.createElement("div");
  center.className = "wheel-center";
  center.innerHTML = `<div class="ft">PISTA RÁPIDA</div><div class="arrow">➤</div><h2>CASHFLOW</h2>`;
  board.appendChild(center);
}

function renderBoard() {
  const board = $("board");
  const W = board.clientWidth, H = board.clientHeight;
  const dim = Math.min(W, H);
  const rw = board.querySelector(".wheel-ring.rat");
  const fw = board.querySelector(".wheel-ring.fast");
  if (rw) { rw.style.width = rw.style.height = (0.92 * dim) + "px"; }
  if (fw) { fw.style.width = fw.style.height = (0.58 * dim) + "px"; }

  board.querySelectorAll(".wheel-label.rl").forEach((el) => {
    const p = boardPos(24, +el.dataset.i, 0.85);
    el.style.left = p.x + "px"; el.style.top = p.y + "px";
  });
  board.querySelectorAll(".wheel-label.fl").forEach((el) => {
    const p = boardPos(12, +el.dataset.i, 0.52);
    el.style.left = p.x + "px"; el.style.top = p.y + "px";
  });
  renderTokens();
}

function tokenKey(p) {
  return p.inFastTrack ? `fast` : `rat`;
}

function positionToken(p, idxOnCell) {
  let t = document.querySelector(`.token[data-pid="${p.id}"]`);
  if (!t) {
    t = document.createElement("div");
    t.className = "token";
    t.dataset.pid = p.id;
    t.innerHTML = `<span class="tdot"></span><span class="tname"></span>`;
    $("board").appendChild(t);
  }
  const ring = p.inFastTrack ? "fast" : "rat";
  const n = ring === "rat" ? 24 : 12;
  const pos = p.inFastTrack ? p.fastTrackPosition : p.position;
  const radius = ring === "rat" ? 0.92 : 0.58;
  const px = boardPos(n, pos, radius);
  const off = (idxOnCell - 0) * 2.5;
  t.style.left = (px.x + off * 3) + "px";
  t.style.top = (px.y - off * 6) + "px";
  const dot = t.querySelector(".tdot");
  dot.style.background = p.color || "";
  dot.style.backgroundImage = "none";
  dot.textContent = p.icon || p.name[0].toUpperCase();
  t.querySelector(".tname").textContent = p.name;
  t.classList.toggle("me", p.id === yourId);
  const cur = state.phase === "playing" && state.players[state.turnIndex];
  t.classList.toggle("active", !!(cur && cur.id === p.id));
  return t;
}

function renderTokens() {
  if (animGuard) return;
  const byCell = {};
  state.players.forEach((p) => {
    const key = tokenKey(p);
    const pos = p.inFastTrack ? p.fastTrackPosition : p.position;
    const k = `${key}-${pos}`;
    (byCell[k] = byCell[k] || []).push(p);
  });
  state.players.forEach((p) => {
    const key = tokenKey(p);
    const pos = p.inFastTrack ? p.fastTrackPosition : p.position;
    const idx = byCell[`${key}-${pos}`].indexOf(p);
    positionToken(p, idx);
  });
}

/* ================= Jugadores / declaraciones ================= */

function fin(p) {
  if (!p.profession) return { salary: 0, passive: 0, expenses: 0, cf: 0 };
  const salary = p.downsizedTurns > 0 ? 0 : p.profession.salary;
  const passive = p.realEstate.reduce((a, x) => a + x.cashFlow, 0) + p.businesses.reduce((a, x) => a + x.cashFlow, 0);
  const expenses = Object.values(p.expenses).reduce((a, x) => a + x, 0) + p.extraExpenses;
  return { salary, passive, expenses, cf: salary + passive - expenses };
}

function renderPlayers() {
  const el = $("players");
  el.innerHTML = "";
  state.players.forEach((p) => {
    const f = fin(p);
    const card = document.createElement("div");
    card.className = "player-card";
    card.style.setProperty("--pc", p.color || "");
    const cur = state.players[state.turnIndex];
    if (state.phase === "playing" && cur && cur.id === p.id) card.classList.add("turn");
    if (p.won) card.classList.add("winner");
    const esc = !p.inFastTrack && f.passive > f.expenses && state.phase === "playing";
    const escPct = f.expenses > 0 ? Math.min(100, Math.round((f.passive / f.expenses) * 100)) : 0;
    const pct = p.inFastTrack ? 100 : Math.max(0, escPct);
    card.innerHTML = `
      <div class="pc-top">
        <span class="pc-dot">${p.icon || ""}</span>
        <span class="pc-name">${p.name} ${p.id === yourId ? "(vos)" : ""}</span>
        <span class="badge ${p.inFastTrack ? "ft" : ""}">${p.inFastTrack ? "🚀 Pista rápida" : "🐀 Ratas"}${p.downsizedTurns > 0 ? " · 💼" : ""}</span>
      </div>
      <div class="pc-sub">${p.profession ? p.profession.name : "—"} · Hijos: ${p.children}${esc ? " · <b style='color:var(--green)'>¡ESCAPA!</b>" : ""}</div>
      <div class="pc-hero">
        <div class="pc-hero-label">Efectivo</div>
        <div class="pc-hero-cash">${usd.format(p.cash)}</div>
        <div class="pc-hero-cf ${f.cf >= 0 ? "pos" : "neg"}">${f.cf >= 0 ? "▲" : "▼"} ${usd.format(Math.abs(f.cf))}/mes</div>
      </div>
      <div class="esc-track ${p.inFastTrack ? "ft" : ""}"><div class="esc-fill" style="width:${pct}%"></div></div>
      <div class="statement">
        <span class="label">Salario</span><span class="value ${f.salary ? "pos" : "neg"}">${usd.format(f.salary)}</span>
        <span class="label">Pasivo</span><span class="value pos">+${usd.format(f.passive)}</span>
        <span class="label">Gastos</span><span class="value neg">-${usd.format(f.expenses)}</span>
      </div>
      <details class="pc-assets">
        <summary>Activos y pasivos</summary>
        <div class="item">💵 Efectivo: <b class="cash">${usd.format(p.cash)}</b></div>
        ${p.realEstate.map((a) => `<div class="item">🏠 ${a.name} · flujo +${usd.format(a.cashFlow)}</div>`).join("")}
        ${p.businesses.map((b) => `<div class="item">🏢 ${b.name} · flujo +${usd.format(b.cashFlow)}</div>`).join("")}
        ${p.stocks.map((s) => `<div class="item">📊 ${s.symbol}: ${s.shares} acc. a ${usd.format(Math.round(s.buyPrice))}</div>`).join("")}
        <div class="item">🏦 Pasivos: ${usd.format(Object.values(p.liabilities).reduce((a, x) => a + x, 0))}</div>
        <div class="item">🌟 Sueño: ${p.dream ? `${p.dream.name} (${usd.format(p.dream.cost)})` : "—"}</div>
      </details>
    `;
    el.appendChild(card);
  });
}

/* ================= Log y chat ================= */

function logClass(line) {
  const emoji = line.trim()[0];
  if (emoji === "💰") return "money";
  if (emoji === "📈" || emoji === "📉") return "market";
  if (emoji === "👶") return "baby";
  if (emoji === "💼" || emoji === "📉") return "bad";
  if (emoji === "🏆") return "win";
  if (emoji === "🚀") return "fast";
  if (emoji === "🎲" || emoji === "🏃") return "move";
  if (emoji === "📊" || emoji === "📗" || emoji === "📘" || emoji === "🏠" || emoji === "🏢") return "deal";
  if (emoji === "🤝") return "charity";
  if (emoji === "▶") return "turn";
  return "";
}

function renderLog() {
  const el = $("log-list");
  el.innerHTML = "";
  (state.logs || []).forEach((line) => {
    const d = document.createElement("div");
    d.className = "entry " + logClass(line);
    d.innerHTML = line.replace(/`/g, "");
    el.appendChild(d);
  });
  el.scrollTop = el.scrollHeight;
}

function renderChat() {
  const el = $("chat-list");
  el.innerHTML = "";
  (state.chat || []).forEach((m) => {
    const d = document.createElement("div");
    d.className = "msg";
    d.innerHTML = `<b>${m.name}:</b> ${m.text.replace(/</g, "&lt;")}`;
    el.appendChild(d);
  });
  el.scrollTop = el.scrollHeight;
}

/* ================= Dados ================= */

function renderDice() {
  const el = $("dice-display");
  const mv = state.lastMove;
  if (mv && mv.moveId !== seenMove) {
    seenMove = mv.moveId;
    const mover = playerById(mv.playerId);
    pendingFx = mover
      ? { pid: mv.playerId, delta: mover.cash - (lastCash[mv.playerId] ?? mover.cash) }
      : null;
    if (!animGuard) animateTurn(mv);
  }
  if (!mv) { el.innerHTML = ""; el.classList.add("hidden"); }
  else el.classList.remove("hidden");
}

async function animateDice(values) {
  const el = $("dice-display");
  el.innerHTML = values.map(() => `<div class="die">…</div>`).join("");
  const dice = [...el.querySelectorAll(".die")];
  const t0 = performance.now();
  while (performance.now() - t0 < 650) {
    dice.forEach((d) => { d.textContent = 1 + Math.floor(Math.random() * 6); d.classList.add("rolling"); });
    await sleep(60);
  }
  dice.forEach((d, i) => {
    d.textContent = values[i];
    d.classList.remove("rolling");
    d.classList.add("settled");
  });
}

/* ================= Animación de movimiento ================= */

function flashCell(ring, i, cls = "flash") {
  const n = ring === "rat" ? 24 : 12;
  const radius = ring === "rat" ? 0.92 : 0.58;
  const px = boardPos(n, i, radius);
  const board = $("board");
  const ind = document.createElement("div");
  ind.className = "cell-indicator " + cls;
  ind.style.left = px.x + "px";
  ind.style.top = px.y + "px";
  board.appendChild(ind);
  setTimeout(() => ind.remove(), cls === "landing" ? 1100 : 220);
}

async function animateMove(move) {
  const p = playerById(move.playerId);
  if (!p) return;
  const n = move.fast ? 12 : 24;
  const ring = move.fast ? "fast" : "rat";
  const radius = move.fast ? 0.58 : 0.92;
  const steps = move.dice.reduce((a, x) => a + x, 0);
  const t = document.querySelector(`.token[data-pid="${p.id}"]`);
  if (t) t.classList.add("moving");
  let cur = move.from;
  for (let s = 1; s <= steps; s++) {
    cur = (cur + 1) % n;
    const px = boardPos(n, cur, radius);
    if (t) { t.style.left = px.x + "px"; t.style.top = px.y + "px"; }
    flashCell(ring, cur);
    await sleep(170);
  }
  if (t) { t.classList.remove("moving"); t.classList.add("landed"); }
  flashCell(ring, move.to, "landing");
  setTimeout(() => t && t.classList.remove("landed"), 700);
}

/* ================= Banner de aterrizaje ================= */

const LANDING_TEXT = {
  PAYDAY:    { icon: "💵", text: "Cobraste tu día de pago. ¡Salario y flujo de caja a la bolsa!" },
  SMALL:     { icon: "📗", text: "Hay una oportunidad menor para invertir. ¿Te animás?" },
  BIG:       { icon: "📘", text: "Gran oportunidad de negocio en la mira. ¡No la dejes pasar!" },
  MARKET:    { icon: "📈", text: "El mercado se movió. Mirá las cartas y decidí." },
  DOODAD:    { icon: "🛍️", text: "Baratijas por todos lados. ¡Ojo con el efectivo!" },
  CHARITY:   { icon: "🤝", text: "Casilla de caridad. Doná 10% y tirá con 1 dado el próximo turno." },
  BABY:      { icon: "👶", text: "¡Felicitaciones! Tuviste un hijo y subieron tus gastos." },
  DOWNSIZE:  { icon: "💼", text: "¡Te despidieron! No cobrás salario durante unos turnos." },
  CASHFLOW:  { icon: "💰", text: "Día de flujo de efectivo en la pista rápida. ¡A cobrar!" },
  OPPORTUNITY: { icon: "💡", text: "Oportunidad a tu alcance. ¡Invertí para crecer!" },
  DREAM:     { icon: "🌟", text: "Tu sueño te espera. ¿Te alcanza el efectivo para comprarlo?" },
};

function showLandingBanner(move) {
  const ring = move.fast ? state.fastBoard : state.ratBoard;
  const labels = move.fast ? state.fastLabels : state.ratLabels;
  const type = ring[move.to];
  const info = LANDING_TEXT[type] || { icon: "•", text: "" };
  const name = (labels[type] || type).replace(/\n/g, " ");
  const player = playerById(move.playerId);
  const banner = $("landing-banner");
  banner.classList.remove("hidden");
  banner.innerHTML = `<div class="lb-icon">${info.icon}</div>
    <div class="lb-body">
      <div class="lb-name">${name}</div>
      <div class="lb-text">${info.text}</div>
      <div class="lb-player" style="--c:${player ? player.color : "#fff"}">${player ? player.name : ""}</div>
    </div>`;
  banner.style.borderColor = state.boardMeta[(move.fast ? "fast" : "rat") + "Colors"][type];
  banner.classList.remove("pop");
  void banner.offsetWidth;
  banner.classList.add("pop");
  clearTimeout(showLandingBanner._t);
  showLandingBanner._t = setTimeout(() => banner.classList.add("hidden"), 4200);
}

/* ================= Efecto de dinero flotante ================= */

function floatMoneyFx() {
  if (!pendingFx || pendingFx.delta === 0) return;
  const { pid, delta } = pendingFx;
  pendingFx = null;
  const t = document.querySelector(`.token[data-pid="${pid}"]`);
  if (!t) return;
  const fx = document.createElement("div");
  fx.className = "fx-money " + (delta > 0 ? "gain" : "lose");
  fx.textContent = (delta > 0 ? "+" : "-") + usd.format(Math.abs(delta));
  const r = t.getBoundingClientRect();
  const boardR = $("board").getBoundingClientRect();
  fx.style.left = (r.left - boardR.left + r.width / 2 - 30) + "px";
  fx.style.top = (r.top - boardR.top - 6) + "px";
  $("money-fx").appendChild(fx);
  setTimeout(() => fx.remove(), 1600);
}

async function animateTurn(move) {
  animGuard = true;
  try {
    await animateDice(move.dice);
    await animateMove(move);
    showLandingBanner(move);
    floatMoneyFx();
  } finally {
    animGuard = false;
    renderTokens();
  }
}

/* ================= Turno (pill no bloqueante) ================= */

function renderTurnPill() {
  const pill = $("turn-pill");
  if (state.phase !== "playing" || !state.pending) {
    pill.classList.add("hidden");
    pill.innerHTML = "";
    return;
  }
  const pend = state.pending;
  pill.classList.remove("hidden");
  if (pend.playerId === yourId) {
    if (pend.kind === "roll") {
      pill.innerHTML = `<div class="pill-box mine"><span>🎲 <b>Es tu turno</b></span>
        <button class="primary" onclick="send({type:'roll'})">Tirar dados</button></div>`;
    } else {
      pill.innerHTML = `<div class="pill-box mine"><span>📋 <b>Tomá una decisión</b> en la tarjeta</span></div>`;
    }
  } else {
    const p = playerById(pend.playerId);
    pill.innerHTML = `<div class="pill-box wait"><span>⏳ <b>${p ? p.name : "Jugador"}</b> está jugando…</span></div>`;
  }
}

/* ================= Modales ================= */

let _infoCardKey = null;

function renderModal() {
  const modal = $("modal");
  if (state.phase === "lobby") { modal.classList.add("hidden"); modal.innerHTML = ""; _infoCardKey = null; return; }

  if (state.phase === "selecting") { showSelection(modal); _infoCardKey = null; return; }
  if (state.phase === "over") { showWin(modal); _infoCardKey = null; return; }

  const pending = state.pending;
  if (pending && pending.playerId === yourId) {
    if (pending.kind === "roll") { _infoCardKey = null; modal.classList.add("hidden"); modal.innerHTML = ""; return; }
    _infoCardKey = state.lastCard ? JSON.stringify(state.lastCard) : null;
    showChoice(modal);
    return;
  }

  const lc = state.lastCard;
  if (!pending && lc) {
    const key = JSON.stringify(lc);
    if (key !== _infoCardKey) {
      _infoCardKey = key;
      showInfoCard(modal);
    }
    return;
  }

  modal.classList.add("hidden");
  modal.innerHTML = "";
}

function showSelection(modal) {
  modal.classList.remove("hidden");
  const taken = state.players.filter((p) => p.profession).map((p) => p.profession.id);
  const mine = me() && me().profession;
  if (mine) {
    modal.innerHTML = `<div class="modal-box waiting">${mine.icon || ""} Elegiste <b>${mine.name}</b>. Esperando a los demás…</div>`;
    return;
  }
  modal.innerHTML = `<div class="modal-box"><h2>Elegí tu profesión</h2>
    <div class="prof-list">
      ${state.availableProfessions.map((p) => `
        <div class="prof-item ${taken.includes(p.id) ? "taken" : ""}" onclick="${taken.includes(p.id) ? "" : `chooseProf('${p.id}')`}"
             style="${taken.includes(p.id) ? "" : `border-left: 4px solid ${p.color}`}">
          <div class="prof-header">
            <span class="prof-icon">${p.icon || ""}</span>
            <b>${p.name}</b>
          </div>
          <span>Salario ${usd.format(p.salary)} · Gastos ${usd.format(Object.values(p.expenses).reduce((a, x) => a + x, 0))}</span>
          <span>Ahorros ${usd.format(p.savings)}</span>
        </div>`).join("")}
    </div></div>`;
}

function showWin(modal) {
  const winner = state.players.find((p) => p.won) || state.players[0];
  modal.classList.remove("hidden");
  modal.innerHTML = `<div class="modal-box win-box">
    <h1>🏆</h1><h1>¡${winner.name} GANA!</h1>
    <p>${winner.name} escapó de la carrera de ratas y compró su sueño: <b>${winner.dream.name}</b>.</p>
  </div>`;
}

function showInfoCard(modal) {
  const lc = state.lastCard;
  if (!lc) { modal.classList.add("hidden"); modal.innerHTML = ""; return; }
  modal.classList.remove("hidden");

  if (lc.deck === "small" || lc.deck === "big") {
    const card = lc.card;
    if (card.kind === "stock") {
      modal.innerHTML = `<div class="modal-box">
        <div class="card-type">📗 Oportunidad · Acciones</div>
        <div class="card-name">${card.name}</div>
        <div class="card-text">Precio: <b>${usd.format(card.price)}</b> por acción.</div>
        <div class="hint" style="color:var(--red)">⚠️ No tenés efectivo para comprar acciones.</div>
        <div class="modal-actions"><button onclick="this.closest('.modal').classList.add('hidden')">Cerrar</button></div>
      </div>`;
      return;
    }
    const kind = card.kind === "realEstate" ? "🏠 Inmueble" : "🏢 Negocio";
    modal.innerHTML = `<div class="modal-box">
      <div class="card-type">${lc.deck === "small" ? "📗 Oportunidad menor" : "📘 Oportunidad mayor"} · ${kind}</div>
      <div class="card-name">${card.name}</div>
      <div class="price-row"><span>Valor</span><span class="val">${usd.format(card.cost)}</span></div>
      <div class="price-row"><span>Anticipo</span><span class="val">${usd.format(card.down)}</span></div>
      <div class="price-row"><span>Flujo mensual</span><span class="val" style="color:var(--green)">+${usd.format(card.cashFlow)}</span></div>
      <div class="hint" style="color:var(--red)">⚠️ No tenés efectivo suficiente para el anticipo.</div>
      <div class="modal-actions"><button onclick="this.closest('.modal').classList.add('hidden')">Cerrar</button></div>
    </div>`;
    return;
  }

  if (lc.deck === "doodad") {
    const card = lc.card;
    modal.innerHTML = `<div class="modal-box">
      <div class="card-type">🛍️ Baratija</div>
      <div class="card-name">${card.name}</div>
      <div class="price-row"><span>Precio</span><span class="val">${usd.format(card.cost)}</span></div>
      <div class="hint" style="color:var(--red)">⚠️ No tenés efectivo suficiente.</div>
      <div class="modal-actions"><button onclick="this.closest('.modal').classList.add('hidden')">Cerrar</button></div>
    </div>`;
    return;
  }

  if (lc.deck === "market") {
    const card = lc.card;
    modal.innerHTML = `<div class="modal-box">
      <div class="card-type">📈 Mercado · Consejo del broker</div>
      <div class="card-name">${card.title}</div>
      <div class="card-text">${card.text}</div>
      <div class="hint" style="color:var(--red)">⚠️ No tenés efectivo para aprovechar la oferta.</div>
      <div class="modal-actions"><button onclick="this.closest('.modal').classList.add('hidden')">Cerrar</button></div>
    </div>`;
    return;
  }

  modal.classList.add("hidden");
}

function showChoice(modal) {
  const lc = state.lastCard;
  modal.classList.remove("hidden");
  if (!lc) { modal.innerHTML = `<div class="modal-box waiting">Esperá…</div>`; return; }

  if (lc.deck === "small" || lc.deck === "big") {
    const card = lc.card;
    if (card.kind === "stock") {
      const max = lc.maxShares || 0;
      modal.innerHTML = `<div class="modal-box">
        <div class="card-type">📗 Oportunidad · Acciones</div>
        <div class="card-name">${card.name}</div>
        <div class="card-text">Precio: <b>${usd.format(card.price)}</b> por acción.</div>
        <div class="hint">¿Cuántas acciones comprás? (máx ${max})</div>
        <input id="shares-in" type="number" min="0" max="${max}" value="0">
        <div class="modal-actions">
          <button onclick="send({type:'choice',value:{shares:0}})">Pasar</button>
          <button class="primary" onclick="send({type:'choice',value:{shares:+$('shares-in').value}})">Comprar</button>
        </div>
      </div>`;
      return;
    }
    const afford = lc.afford;
    const kind = card.kind === "realEstate" ? "🏠 Inmueble" : "🏢 Negocio";
    modal.innerHTML = `<div class="modal-box">
      <div class="card-type">${lc.deck === "small" ? "📗 Oportunidad menor" : "📘 Oportunidad mayor"} · ${kind}</div>
      <div class="card-name">${card.name}</div>
      <div class="price-row"><span>Valor</span><span class="val">${usd.format(card.cost)}</span></div>
      <div class="price-row"><span>Anticipo</span><span class="val">${usd.format(card.down)}</span></div>
      <div class="price-row"><span>Flujo mensual</span><span class="val" style="color:var(--green)">+${usd.format(card.cashFlow)}</span></div>
      ${card.resale ? `<div class="price-row"><span>Precio reventa</span><span class="val">${usd.format(card.resale[0])}–${usd.format(card.resale[1])}</span></div>` : ""}
      <div class="modal-actions">
        <button onclick="send({type:'choice',value:{buy:false}})">Pasar</button>
        ${afford ? `<button class="primary" onclick="send({type:'choice',value:{buy:true}})">Comprar</button>` : `<button disabled>Comprar</button>`}
      </div>
    </div>`;
    return;
  }

  if (lc.deck === "doodad") {
    const card = lc.card;
    const afford = lc.afford;
    modal.innerHTML = `<div class="modal-box">
      <div class="card-type">🛍️ Baratija</div>
      <div class="card-name">${card.name}</div>
      <div class="price-row"><span>Precio</span><span class="val">${usd.format(card.cost)}</span></div>
      ${card.expense ? `<div class="price-row"><span>Gasto mensual</span><span class="val neg">-${usd.format(card.expense)}</span></div>` : ""}
      <div class="modal-actions">
        <button onclick="send({type:'choice',value:{buy:false}})">No comprar</button>
        ${afford ? `<button class="primary" onclick="send({type:'choice',value:{buy:true}})">Comprar</button>` : `<button disabled>Comprar</button>`}
      </div>
    </div>`;
    return;
  }

  if (lc.deck === "charity") {
    modal.innerHTML = `<div class="modal-box">
      <div class="card-type">🤝 Caridad</div>
      <div class="card-name">Doná 10% de tu salario</div>
      <div class="card-text">Donando <b>${usd.format(lc.amount)}</b>, el próximo turno tirás <b>1 solo dado</b> para llegar a mejores casillas.</div>
      <div class="modal-actions">
        <button onclick="send({type:'choice',value:{pay:false}})">No donar</button>
        <button class="primary" onclick="send({type:'choice',value:{pay:true}})">Donar</button>
      </div>
    </div>`;
    return;
  }

  if (lc.deck === "market" && lc.card.kind === "stockBuy") {
    const card = lc.card;
    const max = lc.maxShares || 0;
    modal.innerHTML = `<div class="modal-box">
      <div class="card-type">📈 Mercado · Consejo del broker</div>
      <div class="card-name">${card.title}</div>
      <div class="card-text">${card.text}</div>
      <div class="hint">¿Cuántas acciones de <b>${card.symbol}</b> comprás a ${usd.format(card.price)}? (máx ${max})</div>
      <input id="shares-in" type="number" min="0" max="${max}" value="0">
      <div class="modal-actions">
        <button onclick="send({type:'choice',value:{shares:0}})">Ignorar</button>
        <button class="primary" onclick="send({type:'choice',value:{shares:+$('shares-in').value}})">Comprar</button>
      </div>
    </div>`;
    return;
  }

  if (lc.deck === "marketSell") {
    if (lc.kind === "stock") {
      modal.innerHTML = `<div class="modal-box">
        <div class="card-type">📈 Mercado · Acciones</div>
        <div class="card-name">${lc.card.title}</div>
        <div class="card-text">${lc.card.text}</div>
        <div class="hint">Tenés <b>${lc.shares}</b> acciones de <b>${lc.symbol}</b>. Elegí precio de venta (${usd.format(lc.priceRange[0])}–${usd.format(lc.priceRange[1])}):</div>
        <input id="price-in" type="number" min="${lc.priceRange[0]}" max="${lc.priceRange[1]}" value="${lc.priceRange[1]}">
        <div class="modal-actions">
          <button onclick="send({type:'choice',value:{pass:true}})">No vender</button>
          <button class="primary" onclick="send({type:'choice',value:{price:+$('price-in').value}})">Vender todo</button>
        </div>
      </div>`;
      return;
    }
    if (lc.kind === "realEstate") {
      const list = lc.assets.map((a) => `
        <div style="border:1px solid var(--border);border-radius:8px;padding:8px;margin-top:6px">
          <div class="card-name" style="font-size:14px">🏠 ${a.name}</div>
          <div class="hint">Flujo: +${usd.format(a.cashFlow)}/mes · Reventa ${usd.format(a.resale[0])}–${usd.format(a.resale[1])}</div>
          <div style="display:flex;gap:6px;margin-top:6px">
            <input type="number" min="${a.resale[0]}" max="${a.resale[1]}" value="${a.resale[1]}" id="price-${a.id}">
            <button onclick="send({type:'choice',value:{assetId:'${a.id}',price:+$('price-${a.id}').value}})">Vender</button>
          </div>
        </div>`).join("");
      modal.innerHTML = `<div class="modal-box">
        <div class="card-type">📈 Mercado · Comprador de inmuebles</div>
        <div class="card-name">${lc.card.title}</div>
        <div class="card-text">${lc.card.text}</div>
        ${list}
        <div class="modal-actions"><button onclick="send({type:'choice',value:{pass:true}})">No vender nada</button></div>
      </div>`;
      return;
    }
    if (lc.kind === "business") {
      const lo = lc.card.multiplier[0], hi = lc.card.multiplier[1];
      const list = lc.assets.map((a) => `
        <div style="border:1px solid var(--border);border-radius:8px;padding:8px;margin-top:6px">
          <div class="card-name" style="font-size:14px">🏢 ${a.name}</div>
          <div class="hint">Flujo: +${usd.format(a.cashFlow)}/mes · Precio ≈ flujo × 12 × multiplicador</div>
          <div style="display:flex;gap:6px;margin-top:6px">
            <input type="number" step="0.1" min="${lo}" max="${hi}" value="${hi}" id="mult-${a.id}">
            <button onclick="send({type:'choice',value:{assetId:'${a.id}',multiplier:+$('mult-${a.id}').value}})">Vender</button>
          </div>
        </div>`).join("");
      modal.innerHTML = `<div class="modal-box">
        <div class="card-type">📈 Mercado · Comprador de negocios</div>
        <div class="card-name">${lc.card.title}</div>
        <div class="card-text">${lc.card.text}</div>
        ${list}
        <div class="modal-actions"><button onclick="send({type:'choice',value:{pass:true}})">No vender nada</button></div>
      </div>`;
      return;
    }
  }

  modal.classList.add("hidden");
  modal.innerHTML = "";
}

/* ================= Acciones ================= */

function chooseProf(id) {
  send({ type: "choose_profession", value: id });
}

/* ================= Eventos UI ================= */

function showError(text) {
  if ($("lobby").classList.contains("hidden")) {
    const el = $("game-error");
    el.textContent = text;
    el.classList.remove("hidden");
    clearTimeout(showError._t);
    showError._t = setTimeout(() => el.classList.add("hidden"), 4000);
  } else {
    $("lobby-error").textContent = text;
  }
}

function lobbyMsg(text, isError) {
  const el = $("lobby-error");
  el.textContent = text;
  el.classList.toggle("error", !!isError);
  el.classList.toggle("info", !isError);
  clearTimeout(lobbyMsg._t);
  lobbyMsg._t = setTimeout(() => { el.textContent = ""; }, isError ? 5000 : 0);
}

$("btn-create").onclick = () => {
  const name = $("lobby-name").value.trim();
  if (!name) { lobbyMsg("Escribí tu nombre.", true); $("lobby-name").focus(); return; }
  lobbyMsg("Conectando…", false);
  connect();
  ws.onopen = () => send({ type: "join", name, roomId: "" });
  $("lobby-name").disabled = true;
};

$("btn-join").onclick = () => {
  const name = $("lobby-name").value.trim();
  const room = $("lobby-room").value.trim();
  if (!name) { lobbyMsg("Escribí tu nombre.", true); $("lobby-name").focus(); return; }
  if (!room) { lobbyMsg("Ingresá el código de sala.", true); $("lobby-room").focus(); return; }
  lobbyMsg("Conectando…", false);
  connect();
  ws.onopen = () => send({ type: "join", name, roomId: room });
  $("lobby-name").disabled = true;
};

$("btn-start").onclick = () => send({ type: "start" });
$("btn-copy-room").onclick = () => navigator.clipboard && navigator.clipboard.writeText(roomId);
$("chat-send").onclick = () => {
  const t = $("chat-text");
  if (t.value.trim()) { send({ type: "chat", text: t.value }); t.value = ""; }
};
$("chat-text").addEventListener("keydown", (e) => { if (e.key === "Enter") $("chat-send").click(); });

window.addEventListener("resize", () => { if (state) renderBoard(); });
