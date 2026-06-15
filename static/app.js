// Retro Alpha - Frontend with improved UX
// NN/g heuristics: system status visibility, recognition > recall,
// error prevention, user control & freedom, minimalist design

(function () {
  const E = window.RetroEngine;
  const Ev = window.RetroEvents;
  const DISPLAY = E.ASSET_DISPLAY_NAMES;
  const TRADABLE_DISPLAY = E.TRADABLE_KEYS.map(function (k) { return DISPLAY[k]; });

  // DOM refs
  function $(id) { return document.getElementById(id); }
  var els = {
    date: $("date-display"),
    llmStatus: $("llm-status"),
    llmBadge: $("llm-badge"),
    chatLlmBadge: $("chat-llm-badge"),
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
    tradeForm: $("trade-form"),
    tradeBtn: $("trade-btn"),
    sideBuy: $("side-buy"),
    sideSell: $("side-sell"),
    actionInput: $("action"),
    amountRange: $("amount-range"),
    amountInput: $("amount"),
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
    progressBar: $("progress-bar"),
    progressLabel: $("progress-label"),
    goalPct: $("goal-pct"),
    onboarding: $("onboarding-overlay"),
    onboardStart: $("onboard-start"),
    helpBtn: $("help-btn"),
    helpModal: $("help-modal"),
    closeHelp: $("close-help"),
    toastContainer: $("toast-container"),
  };

  // State
  var state = E.newGame();
  var chartMode = "networth";
  var prevPrices = {};
  for (var k in state.prices) prevPrices[k] = state.prices[k];

  // Formatters
  var fmtMoney = function (n) {
    var neg = n < 0 ? "-" : "";
    return neg + "\u20b9" + Math.abs(Math.round(n)).toLocaleString("en-IN");
  };
  var fmtPct = function (n) { return (n >= 0 ? "+" : "") + n.toFixed(2) + "%"; };
  var chgClass = function (n) { return n > 0.001 ? "up" : n < -0.001 ? "down" : "flat"; };

  // Toast notifications
  function toast(msg, type) {
    type = type || "info";
    var div = document.createElement("div");
    div.className = "toast " + type;
    div.textContent = msg;
    els.toastContainer.appendChild(div);
    setTimeout(function () {
      if (div.parentNode) div.parentNode.removeChild(div);
    }, 3000);
  }

  // API (LLM only)
  async function apiLLM(path, body) {
    try {
      var r = await fetch(path, {
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
      var r = await fetch("/game-api/health");
      return await r.json();
    } catch (e) {
      return { llm: "error" };
    }
  }

  // --- Rendering ---
  function render() {
    var s = state;
    var total = E.totalValue(s);
    var invested = E.investedValue(s);
    var pnl = E.totalPnl(s);
    var startVal = E.STARTING_CASH;
    var goalPct = (total / E.WIN_THRESHOLD) * 100;

    // Date & progress
    els.date.textContent = s.year + "-" + String(s.month).padStart(2, "0");
    var monthsDone = s.months_elapsed;
    var pct = (monthsDone / E.GAME_LENGTH_MONTHS) * 100;
    els.progressBar.style.width = pct + "%";
    els.progressBar.className = "progress-bar" +
      (pct > 80 ? " danger" : pct > 60 ? " warning" : "");
    els.progressLabel.textContent = "Month " + monthsDone + "/" + E.GAME_LENGTH_MONTHS;
    els.goalPct.textContent = Math.round(goalPct) + "%";
    els.goalPct.className = goalPct >= 100 ? "goal-pct up" : "goal-pct";

    // Summary
    els.cashLine.textContent = fmtMoney(s.cash_balance);
    els.netWorth.textContent = fmtMoney(total);
    els.investedLine.textContent = fmtMoney(invested);
    els.pnlLine.textContent = fmtMoney(pnl);
    els.pnlLine.className = pnl >= 0 ? "up" : "down";

    renderWatch();
    renderPositions();
    renderChart();
    renderTradeBtn();

    // Game over
    if (s.game_over) {
      els.advanceBtn.disabled = true;
      els.tradeBtn.disabled = true;
      if (s.won) {
        setStatus("YOU WIN! \u20b920L reached.");
        showGameOverBanner(true);
      } else {
        setStatus("GAME OVER - 10 years elapsed.");
        showGameOverBanner(false);
      }
    }
  }

  function renderTradeBtn() {
    var action = els.actionInput.value;
    els.tradeBtn.textContent = action === "buy" ? "BUY \u25b2" : "SELL \u25bc";
    els.tradeBtn.className = action === "buy" ? "btn btn-buy" : "btn btn-sell";
  }

  function showGameOverBanner(won) {
    var existing = document.querySelector(".game-over-banner");
    if (existing) existing.remove();
    var banner = document.createElement("div");
    banner.className = "game-over-banner " + (won ? "win" : "lose");
    banner.textContent = won
      ? "CONGRATULATIONS! You doubled your money. You beat the market."
      : "GAME OVER. 10 years passed. Reset to try again.";
    var summary = els.tradeForm.parentNode.querySelector(".summary");
    if (summary) summary.insertAdjacentElement("afterend", banner);
  }

  function renderWatch() {
    var s = state;
    var rows = E.TRADABLE_KEYS.map(function (key) {
      var display = DISPLAY[key];
      var price = s.prices[key];
      var prev = prevPrices[key] !== undefined ? prevPrices[key] : price;
      var chg = (price - prev) / Math.max(prev, 1e-9) * 100;
      var absChg = price - prev;
      var cls = chgClass(chg);
      var active = chartMode === key ? " active" : "";
      return "<tr class=\"" + active + "\" data-asset=\"" + key + "\">" +
        "<td>" + display + "</td>" +
        "<td>" + fmtMoney(price) + "</td>" +
        "<td class=\"" + cls + "\">" + (absChg >= 0 ? "+" : "") + absChg.toFixed(3) + "</td>" +
        "<td class=\"" + cls + "\">" + fmtPct(chg) + "</td>" +
      "</tr>";
    }).join("");
    els.watchBody.innerHTML = rows;
    els.watchBody.querySelectorAll("tr").forEach(function (tr) {
      tr.addEventListener("click", function () {
        var asset = tr.dataset.asset;
        chartMode = asset;
        els.chartTitle.textContent = DISPLAY[asset];
        document.querySelectorAll(".chip").forEach(function (c) { c.classList.remove("active"); });
        var chip = document.querySelector('.chip[data-chart="' + asset + '"]');
        if (chip) chip.classList.add("active");
        else document.querySelector('.chip[data-chart="networth"]').classList.add("active");
        renderWatch();
        renderChart();
      });
    });
  }

  function renderPositions() {
    var s = state;
    var rows = [];
    for (var i = 0; i < E.TRADABLE_KEYS.length; i++) {
      var asset = E.TRADABLE_KEYS[i];
      var qty = s.portfolio[asset];
      if (qty <= 0.0001) continue;
      var price = s.prices[asset];
      var basis = s.cost_basis[asset];
      var current = qty * price;
      var pnl = current - basis;
      var pnlPct = basis > 0 ? (pnl / basis) * 100 : 0;
      var pnlCls = pnl >= 0 ? "pnl-pos" : "pnl-neg";
      rows.push("<tr>" +
        "<td>" + DISPLAY[asset] + "</td>" +
        "<td>" + qty.toFixed(4) + "</td>" +
        "<td>" + (basis > 0 ? fmtMoney(basis / qty) : "-") + "</td>" +
        "<td>" + fmtMoney(price) + "</td>" +
        "<td>" + fmtMoney(current) + "</td>" +
        "<td class=\"" + pnlCls + "\">" + fmtMoney(pnl) + " (" + fmtPct(pnlPct) + ")</td>" +
      "</tr>");
    }
    if (rows.length === 0) {
      els.positionsBody.innerHTML = '<tr><td colspan="6" class="muted center">Buy assets to see them here</td></tr>';
    } else {
      els.positionsBody.innerHTML = rows.join("");
    }
  }

  // Chart
  function renderChart() {
    var canvas = els.chart;
    var dpr = window.devicePixelRatio || 1;
    var cssW = canvas.clientWidth;
    var cssH = canvas.clientHeight;
    if (cssW <= 0 || cssH <= 0) return;
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    var ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, cssW, cssH);

    var padL = 48, padR = 10, padT = 8, padB = 20;
    var plotW = cssW - padL - padR;
    var plotH = cssH - padT - padB;
    if (plotW <= 0 || plotH <= 0) return;

    var series;
    if (chartMode === "networth") {
      series = state.value_history;
    } else {
      series = (state.price_history || []).map(function (snap) { return snap[chartMode] || 0; });
    }
    if (!series || series.length < 2) {
      ctx.fillStyle = "rgba(51,255,51,0.3)";
      ctx.font = '12px "Share Tech Mono", monospace';
      ctx.textAlign = "center";
      ctx.fillText("Advance a month to build chart data", cssW / 2, cssH / 2);
      return;
    }

    var min = Infinity, max = -Infinity;
    for (var i = 0; i < series.length; i++) {
      if (series[i] < min) min = series[i];
      if (series[i] > max) max = series[i];
    }
    var range = (max - min) || 1;
    var yLo = min - range * 0.05;
    var yHi = max + range * 0.05;
    var yRange = yHi - yLo;
    var xStep = plotW / Math.max(series.length - 1, 1);

    // Grid
    ctx.strokeStyle = "rgba(51,255,51,0.06)";
    ctx.lineWidth = 0.5;
    ctx.font = '10px "Share Tech Mono", monospace';
    ctx.fillStyle = "rgba(51,255,51,0.35)";
    for (var j = 0; j <= 4; j++) {
      var gy = padT + (plotH / 4) * j;
      ctx.beginPath();
      ctx.moveTo(padL, gy);
      ctx.lineTo(cssW - padR, gy);
      ctx.stroke();
      var val = yHi - (yRange / 4) * j;
      var label = chartMode === "networth"
        ? fmtMoney(val).replace("\u20b9", "")
        : val.toFixed(3);
      ctx.textAlign = "right";
      ctx.fillText(label, padL - 4, gy + 3);
    }

    // X labels
    var totalMonths = series.length;
    var labelEvery = Math.max(Math.floor(totalMonths / 6), 1);
    ctx.textAlign = "center";
    for (var k = 0; k < totalMonths; k += labelEvery) {
      var lx = padL + k * xStep;
      var mIdx = state.months_elapsed - (totalMonths - 1 - k);
      var yStart = E.STARTING_YEAR;
      var absMonth = mIdx + E.STARTING_MONTH - 1;
      var yr = yStart + Math.floor(absMonth / 12);
      var mo = (absMonth % 12) + 1;
      ctx.fillText(String(mo).padStart(2, "0") + "/" + (yr % 100), lx, cssH - 4);
    }

    // Line
    var lineColor = chartMode === "networth" ? "#33ff33" : "#00e5ff";
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    ctx.shadowColor = lineColor;
    ctx.shadowBlur = 6;
    ctx.beginPath();
    for (var m = 0; m < series.length; m++) {
      var sx = padL + m * xStep;
      var sy = padT + plotH - ((series[m] - yLo) / yRange) * plotH;
      if (m === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Last dot
    var last = series[series.length - 1];
    var lastX = padL + (series.length - 1) * xStep;
    var lastY = padT + plotH - ((last - yLo) / yRange) * plotH;
    ctx.fillStyle = lineColor;
    ctx.beginPath();
    ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
    ctx.fill();

    if (chartMode === "networth") {
      els.chartTitle.textContent = "Net Worth";
    }
  }

  // News & agents
  function addNews(headline, year, month) {
    if (!headline) return;
    var item = document.createElement("div");
    item.className = "item";
    item.innerHTML = '<span class="ts">[' + year + '-' + String(month).padStart(2, "0") + ']</span>' + headline;
    els.newsContent.prepend(item);
    var children = els.newsContent.children;
    while (children.length > 30) {
      children[children.length - 1].remove();
    }
  }

  function addAgentActions(actions) {
    els.agentLog.innerHTML = "";
    if (!actions || !actions.length) {
      els.agentLog.innerHTML = '<div class="muted">No agent activity this month.</div>';
      return;
    }
    actions.forEach(function (a) {
      var t = (a.actions && a.actions[0]) || {};
      var entry = document.createElement("div");
      entry.className = "agent-entry";
      entry.innerHTML =
        '<span class="name">' + a.agent + '</span> ' +
        '<span class="action">' + (t.action || "hold") + ' ' + (DISPLAY[t.asset] || t.asset || "") + '</span>' +
        '<span class="sentiment">' + (a.sentiment || "") + '</span>' +
        '<div style="color:var(--phosphor-dim);margin-top:2px;">' + (t.reason || "") + '</div>';
      els.agentLog.appendChild(entry);
    });
  }

  // --- Trade ---
  function handleTrade(e) {
    e.preventDefault();
    if (state.game_over) { toast("Game is over. Reset to play again.", "warn"); return; }
    var assetDisplay = els.tradeForm.querySelector("#asset").value;
    var action = els.actionInput.value;
    var pct = parseFloat(els.amountInput.value) / 100;
    var key = Object.keys(DISPLAY).find(function (k) { return DISPLAY[k] === assetDisplay; });
    if (!key) { toast("Invalid asset selection.", "error"); return; }
    if (pct <= 0 || pct > 1) { toast("Amount must be 1-100% of portfolio.", "error"); return; }

    try {
      if (action === "buy") {
        var total = E.totalValue(state);
        var cost = total * pct;
        if (cost > state.cash_balance) {
          toast("Insufficient cash. You need \u20b9" + Math.round(cost).toLocaleString("en-IN") + ".", "error");
          return;
        }
      } else {
        var qty = state.portfolio[key];
        if (qty <= 0.0001) { toast("You don't own any " + assetDisplay + ".", "error"); return; }
      }
      E.executePlayerTrade(state, key, action, pct);
      addNews("You " + action + " " + (pct * 100).toFixed(0) + "% " + assetDisplay, state.year, state.month);
      setStatus("Traded: " + action.toUpperCase() + " " + assetDisplay + " " + (pct * 100).toFixed(0) + "%");
      toast(action.toUpperCase() + " " + assetDisplay + " (" + (pct * 100).toFixed(0) + "%)", "info");
      render();
    } catch (err) {
      toast("Trade failed: " + err.message, "error");
    }
  }

  // --- Advance Month ---
  async function handleAdvance() {
    if (state.game_over) { toast("Game over. Reset to play again.", "warn"); return; }
    setStatus("Advancing...");
    els.advanceBtn.disabled = true;
    els.advanceBtn.textContent = "...";
    try {
      prevPrices = {};
      for (var k in state.prices) prevPrices[k] = state.prices[k];

      var nextY = state.year + (state.month === 12 ? 1 : 0);
      var nextM = state.month === 12 ? 1 : state.month + 1;
      var ev = Ev.eventForMonth(nextY, nextM);

      var snap = {
        month: state.month, year: state.year,
        prices: {}, portfolio: {}, cash: state.cash_balance,
        total_value: E.totalValue(state), unrealized_pnl: E.totalPnl(state),
      };
      for (var k2 in state.prices) snap.prices[k2] = state.prices[k2];
      for (var k3 in state.portfolio) snap.portfolio[k3] = state.portfolio[k3];

      var agentActions = E.allLocalAgentsDecide(snap, ev);
      var news = {
        headline: ev.headline, regime: ev.regime,
        impact: {}, duration_months: ev.duration_months,
        year: ev.year, month: ev.month,
      };
      for (var k4 in ev.impact) news.impact[k4] = ev.impact[k4];

      E.advanceMonth(state, news, agentActions, ev);

      addNews(ev.headline, state.year, state.month);
      addAgentActions(agentActions);

      // Show deterministic insight (AI insight only on demand)
      var detInsight = fallbackInsight(ev, state);
      els.insightText.textContent = detInsight;
      els.insightText.className = "insight-text deterministic";

      var monthLabel = state.year + "-" + String(state.month).padStart(2, "0");
      setStatus("Month " + state.months_elapsed + "/" + E.GAME_LENGTH_MONTHS + " (" + monthLabel + ")");
      if (state.game_over) {
        if (state.won) {
          toast("YOU WIN! \u20b920L reached. Congratulations!", "info");
        } else {
          toast("GAME OVER. 10 years have passed.", "warn");
        }
      }
      render();
    } catch (e) {
      setStatus("Error: " + e.message, true);
    } finally {
      els.advanceBtn.textContent = "Advance Month \u23ce";
      if (!state.game_over) els.advanceBtn.disabled = false;
    }
  }

  function fallbackInsight(ev, s) {
    var pnl = E.totalPnl(s);
    var regime = (ev.regime || "stagnation").replace(/_/g, " ");
    if (pnl < -50000) return "Cut losers in " + regime + " regimes. Rotate into defensives.";
    if (pnl > 50000) return "Book partial profits. " + regime + " trends rarely last.";
    return "Hold steady through this " + regime + " phase.";
  }

  async function generateInsight() {
    if (state.game_over) return;
    var ev = Ev.eventForMonth(state.year, state.month);
    els.insightText.textContent = "Generating...";
    els.insightText.className = "insight-text";
    els.llmBadge.textContent = "...";
    els.llmBadge.className = "badge";
    try {
      var r = await apiLLM("/game-api/insight", {
        event: { headline: ev.headline, regime: ev.regime },
        snapshot: {
          unrealized_pnl: E.totalPnl(state),
          cash: state.cash_balance,
          total_value: E.totalValue(state),
        },
      });
      if (r && r.insight) {
        els.insightText.textContent = r.insight;
        els.insightText.className = "insight-text";
        els.llmBadge.textContent = "LLM";
        els.llmBadge.className = "badge live";
      } else {
        els.insightText.textContent = fallbackInsight(ev, state);
        els.insightText.className = "insight-text deterministic";
        els.llmBadge.textContent = "FALLBACK";
        els.llmBadge.className = "badge fallback";
      }
    } catch (e2) {
      els.insightText.textContent = fallbackInsight(ev, state);
      els.insightText.className = "insight-text deterministic";
      els.llmBadge.textContent = "FALLBACK";
      els.llmBadge.className = "badge fallback";
    }
  }

  // --- Reset ---
  function handleReset() {
    if (state.game_over || state.months_elapsed > 0) {
      if (!confirm("Reset your game? All progress will be lost.")) return;
    }
    state = E.newGame();
    prevPrices = {};
    for (var k in state.prices) prevPrices[k] = state.prices[k];
    els.chatLog.innerHTML = '<div class="chat-msg bot">Welcome back. Ask me about your portfolio or strategy.</div>';
    els.newsContent.innerHTML = '<div class="muted">System ready. Press Advance Month to begin.</div>';
    els.agentLog.innerHTML = "";
    els.insightText.textContent = "Click Generate to get AI market commentary.";
    els.insightText.className = "insight-text deterministic";
    els.llmBadge.textContent = "OFF";
    els.llmBadge.className = "badge fallback";
    els.advanceBtn.disabled = false;
    els.advanceBtn.textContent = "Advance Month \u23ce";
    els.tradeBtn.disabled = false;
    els.progressBar.style.width = "0%";
    els.progressBar.className = "progress-bar";
    els.progressLabel.textContent = "Month 0/" + E.GAME_LENGTH_MONTHS;
    var banner = document.querySelector(".game-over-banner");
    if (banner) banner.remove();
    setStatus("Game reset");
    toast("New game started. Good luck!", "info");
    render();
  }

  // --- Mentor ---
  async function handleMentor() {
    var total = E.totalValue(state);
    var invested = E.investedValue(state);
    var pnl = E.totalPnl(state);

    // Ensure at least a year has passed
    if (state.months_elapsed < 1) {
      toast("Advance at least one month before getting a review.", "warn");
      return;
    }

    setStatus("Generating review...");
    var summary = {
      year: state.year, month: state.month,
      starting_value: E.STARTING_CASH,
      ending_value: total,
      invested_value: invested,
      cash: state.cash_balance,
      unrealized_pnl: pnl,
      max_drawdown: -0.25,
      sharpe_ratio: 0.0,
      allocations: computeAllocations(state),
      ledger: state.ledger.filter(function (t) { return t.year === state.year; }),
    };
    var r = await apiLLM("/game-api/mentor", { summary: summary });
    if (r && r.review) {
      els.mentorRoast.textContent = r.review.roast || "-";
      els.mentorLesson.textContent = "LESSON: " + (r.review.lesson || "");
      els.mentorSuggestion.textContent = "NEXT MOVE: " + (r.review.suggestion || "");
      els.modal.classList.remove("hidden");
      setStatus("Review ready");
    } else {
      toast("Mentor unavailable. Try again.", "error");
    }
  }

  function computeAllocations(s) {
    var total = E.totalValue(s);
    var out = {};
    for (var i = 0; i < E.TRADABLE_KEYS.length; i++) {
      var a = E.TRADABLE_KEYS[i];
      out[a] = total > 0 ? (s.portfolio[a] * s.prices[a]) / total : 0;
    }
    return out;
  }

  // --- Chat ---
  async function handleChat(e) {
    e.preventDefault();
    var msg = els.chatInput.value.trim();
    if (!msg) return;
    appendChat("user", msg);
    els.chatInput.value = "";
    var snapshot = {
      cash: state.cash_balance,
      total_value: E.totalValue(state),
      unrealized_pnl: E.totalPnl(state),
      positions: E.TRADABLE_KEYS
        .filter(function (k) { return state.portfolio[k] > 0.0001; })
        .map(function (k) { return {
          asset: DISPLAY[k], qty: state.portfolio[k],
          price: state.prices[k], value: state.portfolio[k] * state.prices[k],
        }; }),
    };
    var warmDiv = appendChat("bot", "Thinking...");
    var r = await apiLLM("/game-api/chat", { message: msg, snapshot: snapshot });
    if (warmDiv && warmDiv.parentNode) warmDiv.remove();
    if (r && r.reply) {
      var isFallback = r.reply.indexOf("trouble") >= 0 || r.reply.length < 20;
      appendChat("bot", r.reply, isFallback);
    } else {
      appendChat("bot", "Can't reach the advisor right now. Check your connection.", true);
    }
  }

  function appendChat(role, content, fallback) {
    var div = document.createElement("div");
    div.className = "chat-msg " + role + (fallback ? " fallback" : "");
    div.textContent = content;
    els.chatLog.appendChild(div);
    els.chatLog.scrollTop = els.chatLog.scrollHeight;
    return div;
  }

  function setStatus(text, isError) {
    els.statusLine.textContent = text;
    els.statusLine.style.color = isError ? "var(--red)" : "var(--phosphor-dim)";
  }

  // --- Side toggle ---
  function setTradeSide(side) {
    els.actionInput.value = side;
    els.sideBuy.classList.toggle("active", side === "buy");
    els.sideSell.classList.toggle("active", side === "sell");
    renderTradeBtn();
  }

  els.sideBuy.addEventListener("click", function () { setTradeSide("buy"); });
  els.sideSell.addEventListener("click", function () { setTradeSide("sell"); });

  // Amount slider sync
  els.amountRange.addEventListener("input", function () {
    els.amountInput.value = els.amountRange.value;
  });
  els.amountInput.addEventListener("input", function () {
    var v = parseInt(els.amountInput.value) || 1;
    v = Math.max(1, Math.min(100, v));
    els.amountRange.value = v;
  });

  // --- Chart chips ---
  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      document.querySelectorAll(".chip").forEach(function (c) { c.classList.remove("active"); });
      chip.classList.add("active");
      chartMode = chip.dataset.chart;
      els.chartTitle.textContent = chartMode === "networth" ? "Net Worth" : DISPLAY[chartMode];
      renderWatch();
      renderChart();
    });
  });

  // --- Keyboard shortcuts ---
  document.addEventListener("keydown", function (e) {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
    if (e.key === "Enter") {
      e.preventDefault();
      if (els.onboarding && !els.onboarding.classList.contains("hidden")) {
        startGame();
      } else if (!state.game_over) {
        handleAdvance();
      }
    }
  });

  // --- Onboarding ---
  function startGame() {
    els.onboarding.classList.add("hidden");
    render();
    setStatus("Ready - Trade or Advance");
  }

  els.onboardStart.addEventListener("click", startGame);

  // --- Help modal ---
  els.helpBtn.addEventListener("click", function () {
    els.helpModal.classList.remove("hidden");
  });
  els.closeHelp.addEventListener("click", function () {
    els.helpModal.classList.add("hidden");
  });
  els.helpModal.addEventListener("click", function (e) {
    if (e.target === els.helpModal) els.helpModal.classList.add("hidden");
  });

  // --- Mentor modal close ---
  els.closeModal.addEventListener("click", function () {
    els.modal.classList.add("hidden");
  });
  els.modal.addEventListener("click", function (e) {
    if (e.target === els.modal) els.modal.classList.add("hidden");
  });

  // --- Event wiring ---
  els.tradeForm.addEventListener("submit", handleTrade);
  els.advanceBtn.addEventListener("click", handleAdvance);
  els.mentorBtn.addEventListener("click", handleMentor);
  els.resetBtn.addEventListener("click", handleReset);
  els.chatForm.addEventListener("submit", handleChat);
  window.addEventListener("resize", function () { requestAnimationFrame(renderChart); });

  // Generate insight on demand
  document.getElementById("insight-generate-btn").addEventListener("click", generateInsight);

  // --- LLM status ---
  function applyLlmStatus(h) {
    var status = h.llm || "uninitialized";
    if (status === "modal") {
      els.llmStatus.textContent = "LLM: CLOUD";
      els.llmStatus.className = "llm-tag loaded";
      els.llmBadge.className = "badge live";
      els.llmBadge.textContent = "LLM";
      els.chatLlmBadge.className = "badge live";
      els.chatLlmBadge.textContent = "LLM";
      setStatus("Ready (cloud GPU)");
    } else if (status === "hf") {
      els.llmStatus.textContent = "LLM: HF API";
      els.llmStatus.className = "llm-tag loaded";
      els.llmBadge.className = "badge live";
      els.llmBadge.textContent = "LLM";
      els.chatLlmBadge.className = "badge live";
      els.chatLlmBadge.textContent = "LLM";
      setStatus("Ready (HF API)");
    } else if (status === "mock") {
      els.llmStatus.textContent = "LLM: LOCAL";
      els.llmStatus.className = "llm-tag mock";
      els.llmBadge.className = "badge fallback";
      els.llmBadge.textContent = "OFF";
      els.chatLlmBadge.className = "badge fallback";
      els.chatLlmBadge.textContent = "FALLBACK";
      setStatus("Ready (local fallback mode)");
    } else if (status === "loading") {
      els.llmStatus.textContent = "LLM: LOADING";
      els.llmStatus.className = "llm-tag loading";
      els.llmBadge.className = "badge fallback";
      els.llmBadge.textContent = "OFF";
      els.chatLlmBadge.className = "badge fallback";
      els.chatLlmBadge.textContent = "FALLBACK";
      setStatus("Loading LLM...");
    } else {
      els.llmStatus.textContent = "LLM: LOCAL";
      els.llmStatus.className = "llm-tag mock";
      els.llmBadge.className = "badge fallback";
      els.llmBadge.textContent = "OFF";
      els.chatLlmBadge.className = "badge fallback";
      els.chatLlmBadge.textContent = "FALLBACK";
      setStatus("Ready (local fallback)");
    }
  }

  var lastStatusKey = null;
  async function pollLlm() {
    try {
      var h = await fetchHealth();
      var key = (h.llm || "?") + "|" + (h.llm_error || "");
      if (key !== lastStatusKey) {
        lastStatusKey = key;
        applyLlmStatus(h);
      }
    } catch (e) {}
  }

  // Boot
  (async function boot() {
    await pollLlm();
    // Show onboarding
    if (els.onboarding) {
      els.onboarding.classList.remove("hidden");
    }
    // Poll LLM status
    var tick = setInterval(async function () {
      var h = await (await fetch("/game-api/health").catch(function () { return null; }));
      if (!h || !h.json) return;
      try { h = await h.json(); } catch (e) { return; }
      var cur = h.llm || "?";
      if (cur !== (lastStatusKey || "").split("|")[0]) {
        applyLlmStatus(h);
        lastStatusKey = (h.llm || "?") + "|" + (h.llm_error || "");
      }
      if (cur === "modal" || cur === "mock" || cur === "hf" || cur === "error") {
        clearInterval(tick);
      }
    }, 3000);
  })();
})();
