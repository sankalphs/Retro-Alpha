// Retro Alpha — Browser-local frontend.
// Game state lives in the browser (see engine.js). Server is called only
// for LLM-backed features: chat, mentor, insight.

(function () {
  const E = window.RetroEngine;
  const Ev = window.RetroEvents;
  const DISPLAY = E.ASSET_DISPLAY_NAMES;
  const TRADABLE_DISPLAY = E.TRADABLE_KEYS.map((k) => DISPLAY[k]);

  // --- DOM refs ---
  const $ = (id) => document.getElementById(id);
  const els = {
    date: $("date-display"),
    llmStatus: $("llm-status"),
    llmBadge: $("llm-badge"),
    chatLlmBadge: $("chat-llm-badge"),
    indices: $("indices"),
    watchBody: $("watch-body"),
    insightText: $("insight-text"),
    positionsBody: $("positions-body"),
    newsContent: $("news-content"),
    agentLog: $("agent-log"),
    chartTitle: $("chart-title"),
    chart: $("price-chart"),
    cashLine: $("cash-line"),
    netWorth: $("net-worth"),
    investedLine: $("invested-line"),
    pnlLine: $("pnl-line"),
    returnLine: $("return-line"),
    goalLine: $("goal-line"),
    tradeForm: $("trade-form"),
    tradeBtn: $("trade-btn"),
    advanceBtn: $("advance-btn"),
    mentorBtn: $("mentor-btn"),
    resetBtn: $("reset-btn"),
    statusLine: $("status-line"),
    modal: $("mentor-modal"),
    closeModal: $("close-modal"),
    mentorRoast: $("mentor-roast"),
    mentorLesson: $("mentor-lesson"),
    mentorSuggestion: $("mentor-suggestion"),
    chatLog: $("chat-log"),
    chatForm: $("chat-form"),
    chatInput: $("chat-input"),
  };

  // --- local state ---
  let state = E.newGame();
  let chartMode = "networth";
  let prevPrices = { ...state.prices };
  let chatHistory = []; // [{role, content, fallback}]

  // --- formatters ---
  const fmtMoney = (n) => {
    const sign = n < 0 ? "-" : "";
    return sign + "₹" + Math.abs(Math.round(n)).toLocaleString("en-IN");
  };
  const fmtPct = (n) => (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
  const chgClass = (n) => (n > 0 ? "up" : n < 0 ? "down" : "flat");

  // --- API (LLM only) ---
  async function apiLLM(path, body) {
    try {
      const r = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error("HTTP " + r.status);
      return await r.json();
    } catch (e) {
      console.error("LLM API failed:", e);
      return null;
    }
  }

  async function fetchHealth() {
    try {
      const r = await fetch("/api/health");
      return await r.json();
    } catch (e) {
      return { llm: "error" };
    }
  }

  // --- rendering ---
  function render() {
    const s = state;
    const total = E.totalValue(s);
    const invested = E.investedValue(s);
    const pnl = E.totalPnl(s);
    const startVal = E.STARTING_CASH;
    const ret = ((total - startVal) / startVal) * 100;

    els.date.textContent = `${s.year}-${String(s.month).padStart(2, "0")}`;
    els.cashLine.textContent = fmtMoney(s.cash_balance);
    els.netWorth.textContent = fmtMoney(total);
    els.investedLine.textContent = fmtMoney(invested);
    els.pnlLine.textContent = fmtMoney(pnl);
    els.pnlLine.className = pnl >= 0 ? "up" : "down";
    els.returnLine.textContent = fmtPct(ret);
    els.returnLine.className = chgClass(ret);
    els.goalLine.textContent = `₹${(E.WIN_THRESHOLD/1e5).toFixed(0)}L by ${E.STARTING_YEAR + Math.floor(E.GAME_LENGTH_MONTHS/12)}-04`;

    renderIndices();
    renderWatch();
    renderPositions();
    renderChart();

    if (s.game_over) {
      els.advanceBtn.disabled = true;
      els.tradeBtn.disabled = true;
      els.statusLine.textContent = s.won
        ? "CONGRATULATIONS — You survived the markets."
        : "GAME OVER — Margin call.";
    }
  }

  function renderIndices() {
    const s = state;
    const top = [
      { name: "NIFTY", price: s.prices.nifty_50, prev: prevPrices.nifty_50 },
      { name: "NIFTYIT", price: s.prices.nifty_it, prev: prevPrices.nifty_it },
      { name: "GOLD", price: s.prices.gold, prev: prevPrices.gold },
      { name: "RE", price: s.prices.real_estate, prev: prevPrices.real_estate },
      { name: "CRYPTO", price: s.prices.crypto, prev: prevPrices.crypto },
    ];
    els.indices.innerHTML = top.map((i) => {
      const chg = (i.price - i.prev) / Math.max(i.prev, 1e-9) * 100;
      const cls = chg >= 0 ? "up" : "down";
      return `<span class="idx"><span class="name">${i.name}</span><span class="val">${fmtMoney(i.price*1000)}</span><span class="chg ${cls}">${fmtPct(chg)}</span></span>`;
    }).join("");
  }

  function renderWatch() {
    const s = state;
    const rows = E.TRADABLE_KEYS.map((key) => {
      const display = DISPLAY[key];
      const price = s.prices[key];
      const prev = prevPrices[key] ?? price;
      const chg = (price - prev) / Math.max(prev, 1e-9) * 100;
      const absChg = price - prev;
      const cls = chgClass(chg);
      const active = chartMode === key ? "active" : "";
      return `<tr class="${active}" data-asset="${key}">
        <td>${display}</td>
        <td>${fmtMoney(price)}</td>
        <td class="${cls}">${absChg >= 0 ? "+" : ""}${absChg.toFixed(3)}</td>
        <td class="${cls}">${fmtPct(chg)}</td>
      </tr>`;
    }).join("");
    els.watchBody.innerHTML = rows;
    els.watchBody.querySelectorAll("tr").forEach((tr) => {
      tr.addEventListener("click", () => {
        const asset = tr.dataset.asset;
        chartMode = asset;
        els.chartTitle.textContent = DISPLAY[asset];
        document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        const chip = document.querySelector(`.chip[data-chart="${asset}"]`);
        if (chip) chip.classList.add("active");
        else document.querySelector('.chip[data-chart="networth"]').classList.add("active");
        if (chartMode !== "networth") {
          els.chartTitle.textContent = DISPLAY[asset];
        }
        renderWatch();
        renderChart();
      });
    });
  }

  function renderPositions() {
    const s = state;
    const rows = [];
    for (const asset of E.TRADABLE_KEYS) {
      const qty = s.portfolio[asset];
      if (qty <= 0) continue;
      const price = s.prices[asset];
      const basis = s.cost_basis[asset];
      const current = qty * price;
      const pnl = current - basis;
      const pnlPct = basis > 0 ? (pnl / basis) * 100 : 0;
      const pnlCls = pnl >= 0 ? "pnl-pos" : "pnl-neg";
      rows.push(`<tr>
        <td>${DISPLAY[asset]}</td>
        <td>${qty.toFixed(4)}</td>
        <td>${fmtMoney(basis/qty)}</td>
        <td>${fmtMoney(price)}</td>
        <td>${fmtMoney(basis)}</td>
        <td>${fmtMoney(current)}</td>
        <td class="${pnlCls}">${fmtMoney(pnl)}</td>
        <td class="${pnlCls}">${fmtPct(pnlPct)}</td>
      </tr>`);
    }
    if (rows.length === 0) {
      els.positionsBody.innerHTML = `<tr><td colspan="8" class="muted center">No positions yet.</td></tr>`;
    } else {
      els.positionsBody.innerHTML = rows.join("");
    }
  }

  // --- chart (with axis labels) ---
  function renderChart() {
    const canvas = els.chart;
    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth;
    const cssH = canvas.clientHeight;
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, cssW, cssH);

    const padL = 50, padR = 12, padT = 10, padB = 22;
    const plotW = cssW - padL - padR;
    const plotH = cssH - padT - padB;

    let series;
    if (chartMode === "networth") {
      series = state.value_history;
    } else {
      series = (state.price_history || []).map((snap) => snap[chartMode] || 0);
    }
    if (series.length < 2) return;

    const min = Math.min(...series);
    const max = Math.max(...series);
    const range = (max - min) || 1;
    const yLo = min - range * 0.05;
    const yHi = max + range * 0.05;
    const yRange = yHi - yLo;

    const xStep = plotW / Math.max(series.length - 1, 1);

    // Grid
    ctx.strokeStyle = "rgba(51,255,51,0.08)";
    ctx.lineWidth = 1;
    ctx.font = '10px "Share Tech Mono", monospace';
    ctx.fillStyle = "rgba(51,255,51,0.4)";
    for (let i = 0; i <= 4; i++) {
      const y = padT + (plotH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(cssW - padR, y);
      ctx.stroke();
      const val = yHi - (yRange / 4) * i;
      const label = chartMode === "networth"
        ? fmtMoney(val).replace("₹", "")
        : val.toFixed(3);
      ctx.textAlign = "right";
      ctx.fillText(label, padL - 4, y + 3);
    }

    // X-axis labels (months)
    const totalMonths = series.length;
    const labelEvery = Math.max(Math.floor(totalMonths / 6), 1);
    ctx.textAlign = "center";
    for (let i = 0; i < totalMonths; i += labelEvery) {
      const x = padL + i * xStep;
      const mIdx = state.months_elapsed - (totalMonths - 1 - i);
      const yStart = E.STARTING_YEAR;
      const absMonth = mIdx + E.STARTING_MONTH - 1;
      const yr = yStart + Math.floor(absMonth / 12);
      const mo = (absMonth % 12) + 1;
      ctx.fillText(`${String(mo).padStart(2,"0")}/${yr%100}`, x, cssH - 4);
    }

    // Line
    ctx.strokeStyle = chartMode === "networth" ? "#33ff33" : "#00e5ff";
    ctx.lineWidth = 2;
    ctx.shadowColor = ctx.strokeStyle;
    ctx.shadowBlur = 6;
    ctx.beginPath();
    series.forEach((v, i) => {
      const x = padL + i * xStep;
      const y = padT + plotH - ((v - yLo) / yRange) * plotH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Last-point dot
    const last = series[series.length - 1];
    const lx = padL + (series.length - 1) * xStep;
    const ly = padT + plotH - ((last - yLo) / yRange) * plotH;
    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.arc(lx, ly, 3, 0, Math.PI * 2);
    ctx.fill();

    // Title
    if (chartMode === "networth") {
      els.chartTitle.textContent = "Net Worth";
    }
  }

  // --- news & agent wire ---
  function addNews(headline, year, month) {
    if (!headline) return;
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = `<span class="ts">[${year}-${String(month).padStart(2,"0")}]</span>${headline}`;
    els.newsContent.prepend(item);
    while (els.newsContent.children.length > 30) {
      els.newsContent.lastChild.remove();
    }
  }

  function addAgentActions(actions) {
    els.agentLog.innerHTML = "";
    if (!actions || !actions.length) {
      els.agentLog.innerHTML = '<div class="muted">No agent chatter this month.</div>';
      return;
    }
    actions.forEach((a) => {
      const t = (a.actions && a.actions[0]) || {};
      const entry = document.createElement("div");
      entry.className = "agent-entry";
      entry.innerHTML =
        `<span class="name">${a.agent}</span> ` +
        `<span class="action">${t.action || "hold"} ${DISPLAY[t.asset] || t.asset || ""}</span>` +
        `<span class="sentiment">${a.sentiment || ""}</span>` +
        `<div style="color:var(--phosphor-dim);margin-top:2px;">${t.reason || ""}</div>`;
      els.agentLog.appendChild(entry);
    });
  }

  // --- game actions (all local) ---
  function handleTrade(e) {
    e.preventDefault();
    if (state.game_over) return;
    const form = new FormData(els.tradeForm);
    const assetDisplay = form.get("asset");
    const action = form.get("action");
    const pct = parseFloat(form.get("amount")) / 100;
    const key = Object.keys(DISPLAY).find((k) => DISPLAY[k] === assetDisplay);
    if (!key) { setStatus("Invalid asset", true); return; }
    try {
      E.executePlayerTrade(state, key, action, pct);
      addNews(`You ${action} ${pct*100}% ${assetDisplay}`, state.year, state.month);
      setStatus(`Traded ${action} ${assetDisplay} ${pct*100}%`);
      render();
    } catch (err) {
      setStatus("Trade failed: " + err.message, true);
    }
  }

  async function handleAdvance() {
    if (state.game_over) return;
    setStatus("Advancing month...");
    els.advanceBtn.disabled = true;
    try {
      // Snapshot prices before to compute index deltas
      prevPrices = { ...state.prices };

      // Pick the historical event for the *upcoming* month
      const nextY = state.year + (state.month === 12 ? 1 : 0);
      const nextM = state.month === 12 ? 1 : state.month + 1;
      const ev = Ev.eventForMonth(nextY, nextM);

      // Local deterministic agent decisions
      const snap = {
        month: state.month, year: state.year,
        prices: { ...state.prices }, portfolio: { ...state.portfolio },
        cash: state.cash_balance, total_value: E.totalValue(state),
        unrealized_pnl: E.totalPnl(state),
      };
      const agentActions = E.allLocalAgentsDecide(snap, ev);
      const news = {
        headline: ev.headline, regime: ev.regime,
        impact: { ...ev.impact }, duration_months: ev.duration_months,
        year: ev.year, month: ev.month,
      };
      E.advanceMonth(state, news, agentActions, ev);

      addNews(ev.headline, state.year, state.month);
      addAgentActions(agentActions);

      // AI insight via server LLM (fallback handled server-side)
      try {
        const r = await apiLLM("/api/insight", {
          event: { headline: ev.headline, regime: ev.regime },
          snapshot: {
            unrealized_pnl: E.totalPnl(state),
            cash: state.cash_balance,
            total_value: E.totalValue(state),
          },
        });
        if (r && r.insight) {
          els.insightText.textContent = r.insight;
          els.llmBadge.textContent = "LLM";
          els.llmBadge.className = "badge live";
        } else {
          els.insightText.textContent = fallbackInsight(ev, state);
          els.llmBadge.textContent = "FALLBACK";
          els.llmBadge.className = "badge fallback";
        }
      } catch (e) {
        els.insightText.textContent = fallbackInsight(ev, state);
        els.llmBadge.textContent = "FALLBACK";
        els.llmBadge.className = "badge fallback";
      }

      setStatus(`Month advanced → ${state.year}-${String(state.month).padStart(2,"0")}`);
      render();
    } catch (e) {
      setStatus("Advance failed: " + e.message, true);
    } finally {
      if (!state.game_over) els.advanceBtn.disabled = false;
    }
  }

  function fallbackInsight(ev, s) {
    const pnl = E.totalPnl(s);
    if (pnl < -50000) return `Cut losers in ${ev.regime.replace(/_/g, " ")} regimes and rotate into defensives.`;
    if (pnl > 50000) return `Book partial profits; ${ev.regime.replace(/_/g, " ")} trends rarely last.`;
    return `Hold the line through this ${ev.regime.replace(/_/g, " ")} phase.`;
  }

  function handleReset() {
    if (!confirm("Reset terminal and start a new session? (Your current game will be lost.)")) return;
    state = E.newGame();
    prevPrices = { ...state.prices };
    chatHistory = [];
    els.chatLog.innerHTML = "";
    els.newsContent.innerHTML = '<div class="muted">System boot complete. Awaiting first turn...</div>';
    els.agentLog.innerHTML = "";
    els.insightText.textContent = "Advance a month to see the AI's read on the market.";
    els.advanceBtn.disabled = false;
    els.tradeBtn.disabled = false;
    setStatus("Terminal reset");
    render();
  }

  async function handleMentor() {
    setStatus("Generating mentor review...");
    const summary = {
      year: state.year, month: state.month,
      starting_value: E.STARTING_CASH,
      ending_value: E.totalValue(state),
      invested_value: E.investedValue(state),
      cash: state.cash_balance,
      unrealized_pnl: E.totalPnl(state),
      max_drawdown: -0.25,
      sharpe_ratio: 0.0,
      allocations: computeAllocations(state),
      ledger: state.ledger.filter((t) => t.year === state.year),
    };
    const r = await apiLLM("/api/mentor", { summary });
    if (r && r.review) {
      els.mentorRoast.textContent = r.review.roast || "—";
      els.mentorLesson.textContent = `LESSON: ${r.review.lesson || ""}`;
      els.mentorSuggestion.textContent = `NEXT MOVE: ${r.review.suggestion || ""}`;
      els.modal.classList.remove("hidden");
      setStatus("Mentor ready");
    } else {
      setStatus("Mentor unavailable", true);
    }
  }

  function computeAllocations(s) {
    const total = E.totalValue(s);
    const out = {};
    for (const a of E.TRADABLE_KEYS) {
      out[a] = total > 0 ? (s.portfolio[a] * s.prices[a]) / total : 0;
    }
    return out;
  }

  // --- chatbot ---
  async function handleChat(e) {
    e.preventDefault();
    const msg = els.chatInput.value.trim();
    if (!msg) return;
    appendChat("user", msg);
    els.chatInput.value = "";
    const snapshot = {
      cash: state.cash_balance,
      total_value: E.totalValue(state),
      unrealized_pnl: E.totalPnl(state),
      positions: E.TRADABLE_KEYS
        .filter((k) => state.portfolio[k] > 0)
        .map((k) => ({
          asset: DISPLAY[k],
          qty: state.portfolio[k],
          price: state.prices[k],
          value: state.portfolio[k] * state.prices[k],
        })),
    };
    const r = await apiLLM("/api/chat", { message: msg, snapshot });
    if (r && r.reply) {
      const isFallback = r.reply.includes("trouble") || r.reply.length < 20;
      appendChat("bot", r.reply, isFallback);
    } else {
      appendChat("bot", "Connection to mentor lost. Check the terminal and try again.", true);
    }
  }

  function appendChat(role, content, fallback) {
    const div = document.createElement("div");
    div.className = "chat-msg " + role + (fallback ? " fallback" : "");
    div.textContent = content;
    els.chatLog.appendChild(div);
    els.chatLog.scrollTop = els.chatLog.scrollHeight;
  }

  function setStatus(text, isError) {
    els.statusLine.textContent = text;
    els.statusLine.style.color = isError ? "var(--red)" : "var(--phosphor-dim)";
  }

  // --- chip controls ---
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      chartMode = chip.dataset.chart;
      els.chartTitle.textContent = chartMode === "networth" ? "Net Worth" : DISPLAY[chartMode];
      renderWatch();
      renderChart();
    });
  });

  // --- event wiring ---
  els.tradeForm.addEventListener("submit", handleTrade);
  els.advanceBtn.addEventListener("click", handleAdvance);
  els.mentorBtn.addEventListener("click", handleMentor);
  els.resetBtn.addEventListener("click", handleReset);
  els.closeModal.addEventListener("click", () => els.modal.classList.add("hidden"));
  els.chatForm.addEventListener("submit", handleChat);
  window.addEventListener("resize", renderChart);

  // --- boot ---
  function applyLlmStatus(h) {
    const status = h.llm || "uninitialized";
    if (status === "loaded") {
      els.llmStatus.textContent = "LLM: LOCAL";
      els.llmStatus.className = "llm-tag loaded";
      els.llmStatus.title = `Model: ${h.model_path}`;
      els.llmBadge.className = "badge live";
      els.llmBadge.textContent = "LLM";
      els.chatLlmBadge.className = "badge live";
      els.chatLlmBadge.textContent = "LLM";
      setStatus("Ready (local LLM online)");
    } else if (status === "mock") {
      els.llmStatus.textContent = "LLM: MOCK";
      els.llmStatus.className = "llm-tag mock";
      els.llmStatus.title = h.llm_error || "Mock mode";
      els.llmBadge.className = "badge fallback";
      els.llmBadge.textContent = "FALLBACK";
      els.chatLlmBadge.className = "badge fallback";
      els.chatLlmBadge.textContent = "FALLBACK";
      setStatus("Ready (LLM in mock mode — features use deterministic fallbacks)");
    } else if (status === "loading" || status === "uninitialized") {
      els.llmStatus.textContent = "LLM: LOADING…";
      els.llmStatus.className = "llm-tag loading";
      els.llmStatus.title = h.llm_error
        ? `Loading model — ${h.llm_error}`
        : `Loading model from ${h.model_path}…`;
      els.llmBadge.className = "badge fallback";
      els.llmBadge.textContent = "FALLBACK";
      els.chatLlmBadge.className = "badge fallback";
      els.chatLlmBadge.textContent = "FALLBACK";
      setStatus("Loading local LLM in the background… (game works either way)");
    } else {
      // error
      const reason = (h.llm_error || "model not loaded").slice(0, 120);
      const modelInfo = h.model_exists
        ? `model found (${h.model_size_gb} GB) but failed to initialize`
        : `model file missing at ${h.model_path}`;
      els.llmStatus.textContent = "LLM: OFFLINE";
      els.llmStatus.className = "llm-tag error";
      els.llmStatus.title = `${reason} — ${modelInfo}`;
      els.llmBadge.className = "badge fallback";
      els.llmBadge.textContent = "FALLBACK";
      els.chatLlmBadge.className = "badge fallback";
      els.chatLlmBadge.textContent = "FALLBACK";
      setStatus(
        `LLM offline (${reason}). Chat/mentor use deterministic fallbacks. Game still works.`,
        true
      );
    }
  }

  let _lastStatus = null;
  async function pollLlm() {
    try {
      const h = await fetchHealth();
      const key = `${h.llm || "?"}|${h.llm_error || ""}`;
      if (key !== _lastStatus) {
        _lastStatus = key;
        applyLlmStatus(h);
      }
    } catch (e) {
      /* network blip; ignore */
    }
  }

  (async function boot() {
    await pollLlm();
    render();
    // Poll every 3s so the UI tracks the background load in real time
    // (uninitialized -> loading -> loaded/error). Stop polling once we
    // reach a terminal state (loaded, mock, or error).
    const tick = setInterval(async () => {
      const h = await (await fetch("/api/health").catch(() => null))?.json().catch(() => null);
      if (!h) return;
      const cur = h.llm || "?";
      if (cur !== _lastStatus.split("|")[0]) {
        applyLlmStatus(h);
        _lastStatus = `${h.llm || "?"}|${h.llm_error || ""}`;
      }
      if (cur === "loaded" || cur === "mock" || cur === "error") {
        clearInterval(tick);
      }
    }, 3000);
  })();
})();
