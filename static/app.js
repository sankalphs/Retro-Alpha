// Retro Alpha — Terminal frontend logic

const fmtMoney = (n) => "₹" + Math.round(n).toLocaleString("en-IN");
const fmtPct = (n) => (n >= 0 ? "+" : "") + n.toFixed(2) + "%";

const els = {
  date: document.getElementById("date-display"),
  mktcap: document.getElementById("mktcap-display"),
  netWorth: document.getElementById("net-worth"),
  returns: document.getElementById("returns"),
  cashLine: document.getElementById("cash-line"),
  goalLine: document.getElementById("goal-line"),
  ticker: document.getElementById("ticker"),
  holdingsBody: document.querySelector("#holdings-table tbody"),
  agentLog: document.getElementById("agent-log"),
  newsContent: document.getElementById("news-content"),
  chart: document.getElementById("price-chart"),
  tradeForm: document.getElementById("trade-form"),
  tradeBtn: document.getElementById("trade-btn"),
  advanceBtn: document.getElementById("advance-btn"),
  mentorBtn: document.getElementById("mentor-btn"),
  resetBtn: document.getElementById("reset-btn"),
  modal: document.getElementById("mentor-modal"),
  closeModal: document.getElementById("close-modal"),
  mentorRoast: document.getElementById("mentor-roast"),
  mentorLesson: document.getElementById("mentor-lesson"),
  mentorSuggestion: document.getElementById("mentor-suggestion"),
};

let state = null;
let history = [];

const ctx = els.chart.getContext("2d");

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function loadState() {
  state = await api("/api/state");
  history.push(state.total_value);
  if (history.length > 60) history.shift();
  render();
}

function render() {
  const s = state;
  els.date.textContent = `${s.year}-${String(s.month).padStart(2, "0")}`;
  els.mktcap.textContent = fmtMoney(s.total_value);
  els.netWorth.textContent = fmtMoney(s.total_value);

  const startValue = 1000000;
  const ret = ((s.total_value - startValue) / startValue) * 100;
  els.returns.textContent = `Return: ${fmtPct(ret)}`;
  els.returns.style.color = ret >= 0 ? "var(--phosphor)" : "var(--red)";
  els.cashLine.textContent = `Cash: ${fmtMoney(s.cash)}`;
  els.goalLine.textContent = `Goal: ${fmtMoney(s.goal_value)} by ${s.goal_year}-04`;

  // Ticker
  const tickerParts = Object.entries(s.prices)
    .filter(([asset]) => asset !== "Cash")
    .map(([asset, price]) => `${asset} ${fmtMoney(price)}`);
  els.ticker.textContent = tickerParts.join("   //   ") + "   //   ";

  // Holdings
  els.holdingsBody.innerHTML = "";
  Object.entries(s.portfolio).forEach(([asset, qty]) => {
    if (asset === "Cash") return;
    if (qty <= 0) return;
    const price = s.prices[asset] ?? 1;
    const value = qty * price;
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${asset}</td>
      <td>${qty.toFixed(4)}</td>
      <td>${fmtMoney(price)}</td>
      <td>${fmtMoney(value)}</td>
    `;
    els.holdingsBody.appendChild(row);
  });

  // Agent log
  els.agentLog.innerHTML = "";
  if (s.agent_actions && s.agent_actions.length) {
    s.agent_actions.forEach((a) => {
      const entry = document.createElement("div");
      entry.className = "agent-entry";
      entry.innerHTML = `
        <span class="name">${a.agent}</span>
        <span class="action">${a.action} ${a.asset}</span>
        <span class="sentiment">${a.sentiment}</span>
        <div style="margin-top:4px;color:var(--phosphor-dim)">${a.reason}</div>
      `;
      els.agentLog.appendChild(entry);
    });
  } else {
    els.agentLog.textContent = "No agent chatter this month.";
  }

  // News
  if (s.news && s.news.headline) {
    const item = document.createElement("div");
    item.textContent = `[${s.year}-${String(s.month).padStart(2, "0")}] ${s.news.headline}`;
    item.style.marginBottom = "8px";
    item.style.borderBottom = "1px dashed rgba(51,255,51,0.15)";
    item.style.paddingBottom = "8px";
    els.newsContent.prepend(item);
    while (els.newsContent.children.length > 12) {
      els.newsContent.lastChild.remove();
    }
  }

  drawChart();

  if (s.game_over) {
    els.advanceBtn.disabled = true;
    els.tradeBtn.disabled = true;
    els.ticker.textContent = s.won
      ? "CONGRATULATIONS — YOU SURVIVED THE MARKETS. SESSION COMPLETE."
      : "GAME OVER — MARGIN CALL. SESSION COMPLETE.";
    els.ticker.style.color = s.won ? "var(--phosphor)" : "var(--red)";
  }
}

function drawChart() {
  const canvas = els.chart;
  const w = canvas.width = canvas.clientWidth * window.devicePixelRatio;
  const h = canvas.height = canvas.clientHeight * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;

  ctx.clearRect(0, 0, width, height);
  if (history.length < 2) return;

  const min = Math.min(...history);
  const max = Math.max(...history);
  const range = max - min || 1;

  ctx.strokeStyle = "#33ff33";
  ctx.lineWidth = 2;
  ctx.shadowColor = "#33ff33";
  ctx.shadowBlur = 8;
  ctx.beginPath();

  history.forEach((val, i) => {
    const x = (i / (history.length - 1)) * (width - 20) + 10;
    const y = height - 20 - ((val - min) / range) * (height - 40);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.shadowBlur = 0;

  // Grid lines
  ctx.strokeStyle = "rgba(51,255,51,0.1)";
  ctx.lineWidth = 1;
  for (let i = 1; i < 5; i++) {
    const y = (height / 5) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

async function handleTrade(e) {
  e.preventDefault();
  if (state.game_over) return;
  const form = new FormData(els.tradeForm);
  const payload = {
    asset: form.get("asset"),
    action: form.get("action"),
    amount_pct: parseFloat(form.get("amount")),
  };
  setLoading(els.tradeBtn, true);
  try {
    state = await api("/api/trade", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    history.push(state.total_value);
    if (history.length > 60) history.shift();
    render();
  } catch (err) {
    flashNews(`TRADE REJECTED: ${err.message}`);
  } finally {
    setLoading(els.tradeBtn, false);
  }
}

async function handleAdvance() {
  if (state.game_over) return;
  setLoading(els.advanceBtn, true);
  try {
    state = await api("/api/advance", { method: "POST" });
    history.push(state.total_value);
    if (history.length > 60) history.shift();
    render();
  } catch (err) {
    flashNews(`ADVANCE FAILED: ${err.message}`);
  } finally {
    setLoading(els.advanceBtn, false);
  }
}

async function handleMentor() {
  setLoading(els.mentorBtn, true);
  try {
    const data = await api("/api/mentor");
    els.mentorRoast.textContent = data.review.roast || "No roast available.";
    els.mentorLesson.textContent = `LESSON: ${data.review.lesson || ""}`;
    els.mentorSuggestion.textContent = `NEXT MOVE: ${data.review.suggestion || ""}`;
    els.modal.classList.remove("hidden");
  } catch (err) {
    flashNews(`MENTOR BUSY: ${err.message}`);
  } finally {
    setLoading(els.mentorBtn, false);
  }
}

async function handleReset() {
  if (!confirm("Reset terminal and start a new session?")) return;
  state = await api("/api/reset", { method: "POST" });
  history = [state.total_value];
  els.newsContent.innerHTML = "";
  els.advanceBtn.disabled = false;
  els.tradeBtn.disabled = false;
  els.ticker.style.color = "var(--cyan)";
  render();
}

function flashNews(text) {
  const item = document.createElement("div");
  item.textContent = `[ALERT] ${text}`;
  item.style.color = "var(--red)";
  item.style.marginBottom = "8px";
  els.newsContent.prepend(item);
}

function setLoading(btn, loading) {
  btn.disabled = loading;
  btn.dataset.original = btn.dataset.original || btn.textContent;
  btn.textContent = loading ? "PROCESSING..." : btn.dataset.original;
}

els.tradeForm.addEventListener("submit", handleTrade);
els.advanceBtn.addEventListener("click", handleAdvance);
els.mentorBtn.addEventListener("click", handleMentor);
els.resetBtn.addEventListener("click", handleReset);
els.closeModal.addEventListener("click", () => els.modal.classList.add("hidden"));

window.addEventListener("resize", drawChart);

loadState().catch((err) => {
  els.ticker.textContent = `CONNECTION ERROR: ${err.message}`;
  els.ticker.style.color = "var(--red)";
});
