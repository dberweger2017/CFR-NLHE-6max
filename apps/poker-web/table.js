"use strict";

const $ = (id) => document.getElementById(id);
const STORE = "nseat-local-play-v1";
let saved = {};
try { saved = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (_) { saved = {}; }
let state = null;
let tableInfo = null;
let busy = false;
let autoplay = false;
let timer = null;

function persist() { try { localStorage.setItem(STORE, JSON.stringify(saved)); } catch (_) { /* Session recovery only. */ } }
function bb(chips) { return `${(chips / 100).toFixed(2).replace(/\.00$/, "")} BB`; }
function signed(chips) { return `${chips >= 0 ? "+" : "−"}${bb(Math.abs(chips))}`; }
function node(tag, className, content) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = content;
  return element;
}
function clear(element) { element.replaceChildren(); }
function notice(message, error = false) { $("notice").textContent = message; $("notice").classList.toggle("error", error); $("retry").hidden = !error; }
function connection(message, good = false) { $("connection").textContent = message; $("connection").classList.toggle("online", good); }
function show(id) { for (const name of ["gate", "setup", "game"]) $(name).hidden = name !== id; }
function human() { return state ? state.humanSeat : tableInfo?.seats.findIndex(s => s.agent === "human"); }
function agentName(agent) {
  if (agent === "human") return "You";
  const [kind, name] = agent.split(":");
  return kind === "policy" ? name : { "random": "Random", "check-call": "Check-call", "tight-aggressive": "Tight-aggressive", "pot-pressure": "Pot-pressure" }[name] || name;
}
function seatName(seat) {
  const agent = (state?.table || tableInfo).seats[seat].agent;
  return agent === "human" ? "You" : `Seat ${seat + 1} · ${agentName(agent)}`;
}

async function request(path, { method = "GET", body, key } = {}) {
  const headers = { "X-Play-Token": saved.token || "" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (key) headers["Idempotency-Key"] = key;
  const response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store" });
  const result = await response.json();
  if (!response.ok) {
    const error = new Error(result.error || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  connection("Connected to local table", true);
  return result;
}

async function mutate(path, body) {
  if (busy) return null;
  busy = true; render();
  const operation = saved.pending || { path, body, key: crypto.randomUUID() };
  saved.pending = operation; persist();
  try {
    const response = await request(operation.path, { method: "POST", body: operation.body, key: operation.key });
    saved.pending = null;
    saved.sessionId = response.sessionId;
    persist();
    state = response;
    notice("");
    return response;
  } catch (error) {
    if (error.status >= 400 && error.status < 500) { saved.pending = null; persist(); }
    if (error.status === 403) { saved.token = ""; persist(); }
    autoplay = false;
    connection("Disconnected or request failed");
    notice(`${error.message}. ${saved.pending ? "Retry the same operation" : "Refresh table state"}; no action will be chosen for you.`, true);
    throw error;
  } finally {
    busy = false; render();
  }
}

async function recover() {
  if (!saved.token) { show("gate"); connection("Access token needed"); return; }
  try {
    tableInfo = await request("/api/model");
    if (saved.pending) await mutate(saved.pending.path, saved.pending.body);
    if (!saved.sessionId) { setup(); return; }
    state = await request(`/api/sessions/${saved.sessionId}`);
    render();
    schedule();
  } catch (error) {
    connection("Disconnected");
    notice(error.message, true);
    if (error.status === 403) { saved.token = ""; persist(); show("gate"); return; }
    if (error.status === 404 || error.status === 409) { saved.sessionId = null; persist(); setup(); }
  }
}

function setup() {
  state = null;
  show("setup");
  const t = tableInfo.table;
  const n = t.agents.length;
  $("brand-seats").textContent = `${n} SEATS`;
  const you = tableInfo.seats.some(s => s.agent === "human");
  $("setup-title").textContent = you ? `Play a ${n}-seat table` : `Watch a ${n}-seat bot table`;
  $("table-configuration").textContent = `${n} seats, ${t.stack / 100} BB stacks, 0.5 / 1 BB blinds. Stacks reset after every hand and the button moves one seat clockwise each hand.`;
  const list = $("seat-list"); clear(list);
  for (const seat of tableInfo.seats) {
    const row = node("div", "seat-row");
    row.append(node("strong", "", `Seat ${seat.seat + 1} · ${agentName(seat.agent)}`));
    row.append(node("small", "", seat.pin ? `${seat.pin.strategy} · ${(seat.pin.rows / 1e6).toFixed(1)}M rows · SHA-256 ${seat.pin.sha256.slice(0, 12)}…` : seat.agent === "human" ? "human" : "scripted"));
    list.append(row);
  }
  const models = tableInfo.seats.some(s => s.agent.startsWith("policy:"));
  $("human-options").hidden = !you;
  $("free-mode").disabled = models;
  $("free-hint").textContent = models
    ? "Unavailable with model seats: a model only knows its training menu’s bet sizes."
    : "Make any legal wager.";
  if (models) document.querySelector('input[name="playMode"][value="restricted"]').checked = true;
}

function card(value, hidden = false) {
  const c = node("span", `card ${hidden ? "hidden-card" : (value.endsWith("h") || value.endsWith("d") ? "red" : "")}`, hidden ? "◆" : `${value[0]}${{ c: "♣", d: "♦", h: "♥", s: "♠" }[value[1]]}`);
  c.setAttribute("aria-label", hidden ? "Hidden card" : value);
  return c;
}
function cards(target, values, backCount = 0) {
  clear(target);
  for (const value of values) target.append(card(value));
  for (let i = 0; i < backCount; i++) target.append(card("", true));
}
function position(seat, n, you) {
  // The viewer (or seat 1) sits at the bottom; later seats follow clockwise.
  const angle = Math.PI / 2 + 2 * Math.PI * ((seat - (you ?? 0) + n) % n) / n;
  return [50 + 41 * Math.cos(angle), 50 + 38 * Math.sin(angle)];
}
function blinds(hand, n) {
  const sb = n === 2 ? hand.button : (hand.button + 1) % n;
  return { sb, bb: (sb + 1) % n };
}
function renderSeats(hand) {
  const target = $("seats"); clear(target);
  const n = state.table.seats.length;
  const you = state.humanSeat;
  const roles = hand ? blinds(hand, n) : null;
  for (let seat = 0; seat < n; seat++) {
    const player = hand?.players[seat];
    const box = node("div", `seat${hand?.actor === seat ? " acting" : ""}${player?.folded ? " folded" : ""}${seat === you ? " you" : ""}`);
    const [x, y] = position(seat, n, you);
    box.style.left = `${x}%`; box.style.top = `${y}%`;
    const head = node("div", "seat-head");
    head.append(node("strong", "", seat === you ? "You" : `Seat ${seat + 1}`));
    if (hand) {
      const tags = [hand.button === seat ? "D" : "", roles.sb === seat ? "SB" : "", roles.bb === seat ? "BB" : ""].filter(Boolean);
      if (tags.length) head.append(node("span", "badge", tags.join(" · ")));
    }
    box.append(head);
    if (seat !== you) box.append(node("span", "seat-agent", agentName(state.table.seats[seat].agent)));
    box.append(node("div", "stack", bb(player ? player.stack : state.table.table.stack)));
    if (player) {
      const shown = player.holeCards || player.shownCards;
      const deck = node("div", "cards seat-cards");
      cards(deck, shown, shown.length || player.folded ? 0 : 2);
      box.append(deck);
      if (player.streetBet) box.append(node("span", "seat-bet", bb(player.streetBet)));
      if (player.folded || player.allIn) box.append(node("small", "seat-detail", player.folded ? "Folded" : "All-in"));
      if (hand.result) {
        const net = hand.result[seat];
        box.append(node("div", `seat-net ${net > 0 ? "up" : net < 0 ? "down" : ""}`, signed(net)));
      }
    }
    target.append(box);
  }
}
function button(label, action, emphasis = false) {
  const control = node("button", emphasis ? "primary" : "action-button", label);
  control.type = "button";
  control.disabled = busy || !!saved.pending;
  control.addEventListener("click", action);
  return control;
}
async function act(kind, raiseTo = null) {
  try {
    await mutate(`/api/sessions/${state.sessionId}/actions`, { handId: state.hand.id, revision: state.revision, kind, raiseTo });
    schedule();
  } catch (_) { /* The pending operation is retained for an exact retry. */ }
}
function exactChips(raw) {
  if (!/^\d+(?:\.\d{1,2})?$/.test(raw.trim())) return null;
  const [whole, fraction = ""] = raw.trim().split(".");
  const chips = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  return Number.isSafeInteger(chips) ? chips : null;
}
function renderControls(hand) {
  const target = $("controls"); clear(target);
  if (!hand?.legal) return;
  if (state.playMode === "restricted") {
    const group = node("div", "button-grid");
    for (const item of hand.menu) {
      const label = item.kind === "raise" ? `${item.label} · to ${bb(item.raiseTo)}` : item.kind === "call" ? `Call ${bb(hand.legal.call)}` : item.label;
      group.append(button(label, () => act(item.kind, item.raiseTo), item.kind === "check" || item.kind === "call"));
    }
    target.append(group);
    return;
  }
  const base = node("div", "button-grid");
  for (const kind of ["fold", "check", "call"]) if (hand.legal.kinds.includes(kind)) {
    base.append(button(kind === "call" ? `Call ${bb(hand.legal.call)}` : kind, () => act(kind), kind !== "fold"));
  }
  target.append(base);
  if (!hand.legal.kinds.includes("raise")) return;
  const panel = node("div", "raise-panel");
  panel.append(node("div", "raise-title", `Raise to · ${bb(hand.legal.minRaiseTo)} min / ${bb(hand.legal.maxRaiseTo)} max`));
  const row = node("div", "raise-row");
  const slider = node("input"); slider.type = "range"; slider.min = hand.legal.minRaiseTo; slider.max = hand.legal.maxRaiseTo; slider.step = "1"; slider.value = hand.legal.minRaiseTo;
  slider.setAttribute("aria-label", "Exact raise-to amount in chips");
  const field = node("input"); field.type = "text"; field.inputMode = "decimal"; field.value = (hand.legal.minRaiseTo / 100).toFixed(2);
  field.setAttribute("aria-label", "Exact raise-to amount in BB");
  slider.addEventListener("input", () => { field.value = (Number(slider.value) / 100).toFixed(2); });
  field.addEventListener("input", () => { const value = exactChips(field.value); if (value !== null && value >= Number(slider.min) && value <= Number(slider.max)) slider.value = value; });
  const submit = button("Raise", () => {
    const chips = exactChips(field.value);
    if (chips === null || chips < hand.legal.minRaiseTo || chips > hand.legal.maxRaiseTo) { notice("Enter an exact amount within the displayed legal bounds.", true); return; }
    act("raise", chips);
  }, true);
  row.append(slider, field, node("span", "unit", "BB"), submit); panel.append(row);
  const presets = node("div", "presets button-grid");
  for (const preset of hand.presets) {
    const item = button(`${preset.label} · ${bb(preset.raiseTo)}`, () => { field.value = (preset.raiseTo / 100).toFixed(2); slider.value = preset.raiseTo; });
    item.disabled = busy || !preset.available;
    presets.append(item);
  }
  panel.append(presets); target.append(panel);
}
function eventText(event) {
  const you = event.seat !== undefined && event.seat === state.humanSeat;
  const who = event.seat === undefined ? "" : seatName(event.seat);
  const verb = (base, third) => (you ? base : third);
  if (event.event === "blind") return `${who} ${verb("post", "posts")} ${bb(event.amount)}`;
  if (event.event === "action") {
    if (event.kind === "raise") return `${who} ${verb("raise", "raises")} to ${bb(event.raiseTo)}`;
    if (event.kind === "call") return `${who} ${verb("call", "calls")} ${bb(event.paid)}`;
    return `${who} ${event.kind === "fold" ? verb("fold", "folds") : verb("check", "checks")}`;
  }
  if (event.event === "board") return `${event.street}: ${event.cards.join(" ")}`;
  if (event.event === "shown") return `${who} ${verb("show", "shows")} ${event.cards.join(" ")}`;
  if (event.event === "mucked") return `${who} ${verb("muck", "mucks")}`;
  return "";
}
function renderDecisions(hand) {
  const panel = $("decisions-panel");
  panel.hidden = !hand?.decisions?.length;
  if (panel.hidden) return;
  const target = $("decisions"); clear(target);
  for (const d of hand.decisions) {
    const row = node("div", "decision");
    const chosen = `${d.action[0]}${d.action[0] === "raise" ? ` to ${bb(d.action[1])}` : ""}`;
    row.append(node("strong", "", `${seatName(d.seat)} · ${d.street}: ${chosen}`));
    if (d.probabilities) {
      row.append(node("span", "", d.trained ? " · trained" : " · unseen spot, uniform"));
      const mix = node("div", "");
      d.menu.forEach(([kind, to], i) => {
        const item = node("div", "");
        const bar = node("span", "bar"); bar.style.width = `${Math.round(120 * d.probabilities[i])}px`;
        item.append(bar, node("span", "", `${kind}${kind === "raise" ? ` ${bb(to)}` : ""} ${(100 * d.probabilities[i]).toFixed(1)}%`));
        mix.append(item);
      });
      row.append(mix);
    }
    target.append(row);
  }
}
function render() {
  if (!saved.token) { show("gate"); return; }
  if (!state) return;
  show("game");
  const you = state.humanSeat;
  const n = state.table.seats.length;
  const botOnly = you === null;
  $("brand-seats").textContent = `${n} SEATS`;
  $("mode").textContent = botOnly ? "BOT TABLE · ALL CARDS VISIBLE" : state.playMode === "free" ? "FREE SIZING" : "RESTRICTED RESEARCH";
  $("summary").textContent = `${n} seats · ${state.table.table.stack / 100} BB · ${state.handsPlayed} ${state.handsPlayed === 1 ? "hand" : "hands"} played`;
  $("session-label").textContent = botOnly ? "SESSION · SEAT 1" : "YOUR SESSION RESULT";
  $("session-bb").textContent = signed(state.totals[botOnly ? 0 : you]);
  $("details").textContent = `Session ${state.sessionId} · ${state.table.apiVersion} · ${state.table.schema} · ${state.table.menu} · totals ${state.totals.map((c, i) => `seat ${i + 1} ${signed(c)}`).join(", ")} · ${state.table.seats.filter(s => s.pin).map(s => `seat ${s.seat + 1} SHA-256 ${s.pin.sha256}`).join(" · ")}`;
  $("autoplay").hidden = !botOnly;
  $("auto-play").disabled = autoplay; $("auto-pause").disabled = !autoplay;
  $("auto-step").disabled = busy || autoplay;
  $("new-session").disabled = busy || state.phase === "playing";
  const hand = state.hand;
  renderSeats(hand);
  renderControls(hand);
  renderDecisions(hand);
  const events = $("events"); clear(events);
  if (!hand) {
    $("turn").textContent = "Ready to deal";
    $("result").textContent = "";
    $("new-hand").hidden = false; $("new-hand").disabled = busy || !!saved.pending;
    clear($("board")); $("street").textContent = "PRE-FLOP"; $("pot").textContent = "POT · 0 BB";
    return;
  }
  cards($("board"), hand.board, 5 - hand.board.length);
  $("street").textContent = hand.street.toUpperCase();
  $("pot").textContent = `POT · ${bb(hand.pot)}`;
  $("turn").textContent = state.phase === "finished" ? "Hand complete" : hand.actor === you ? "Your turn" : `${seatName(hand.actor)} is acting…`;
  $("result").textContent = hand.result && !botOnly ? `This hand: ${signed(hand.result[you])} · Session: ${signed(state.totals[you])}` : "";
  $("new-hand").hidden = state.phase !== "finished" || (botOnly && autoplay); $("new-hand").disabled = busy || !!saved.pending;
  for (const event of hand.events) events.append(node("div", "event", eventText(event)));
  events.scrollTop = events.scrollHeight;
}

async function step() {
  if (!state || busy || saved.pending) return;
  if (!state.hand || state.phase === "finished") {
    await mutate(`/api/sessions/${state.sessionId}/hands`, { revision: state.revision });
  } else if (state.hand.actor !== state.humanSeat) {
    await mutate(`/api/sessions/${state.sessionId}/advance`, { handId: state.hand.id, revision: state.revision });
  }
}
function schedule() {
  clearTimeout(timer);
  if (!state?.hand || saved.pending) return;
  const botTurn = state.phase === "playing" && state.hand.actor !== state.humanSeat;
  const nextHand = state.humanSeat === null && autoplay && state.phase === "finished";
  if ((botTurn && (state.humanSeat !== null || autoplay)) || nextHand) {
    timer = setTimeout(async () => {
      try { await step(); schedule(); } catch (_) { /* Retry remains available. */ }
    }, Number($("speed").value) * (nextHand ? 2 : 1));
  }
}

$("gate-form").addEventListener("submit", async (event) => {
  event.preventDefault(); saved.token = $("token").value.trim(); persist();
  await recover();
});
$("create").addEventListener("click", async () => {
  const playMode = document.querySelector('input[name="playMode"]:checked').value;
  try { await mutate("/api/sessions", { playMode }); } catch (_) { /* Notice shown. */ }
});
$("new-hand").addEventListener("click", async () => {
  try { await mutate(`/api/sessions/${state.sessionId}/hands`, { revision: state.revision }); schedule(); } catch (_) { /* Notice shown. */ }
});
$("new-session").addEventListener("click", () => { autoplay = false; clearTimeout(timer); saved.sessionId = null; persist(); setup(); });
$("auto-play").addEventListener("click", () => { autoplay = true; render(); if (!state.hand) step().then(schedule, () => {}); else schedule(); });
$("auto-pause").addEventListener("click", () => { autoplay = false; clearTimeout(timer); render(); });
$("auto-step").addEventListener("click", () => { step().catch(() => {}); });
$("retry").addEventListener("click", () => { notice(""); recover(); });
recover();
