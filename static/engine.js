// Retro Alpha — Browser-local game engine.
// Mirrors engine.py: random walk, price shock, agent pressure, trades,
// cost basis, history. Runs 100% in the browser; server is only for LLM.

(function () {
  const ASSETS = ["cash", "fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"];
  const REGIMES = [
    "bull_market", "bear_market", "market_crash", "recovery", "high_inflation",
    "rate_hike", "rate_cut", "election_year", "monsoon_shock", "fii_exit",
    "tech_boom", "real_estate_boom", "crypto_frenzy", "gold_rush", "stagnation"
  ];

  const ASSET_PARAMS = {
    cash:       { mean: 0.00, vol: 0.01 },
    fd:         { mean: 0.065, vol: 0.005 },
    gov_bonds:  { mean: 0.07,  vol: 0.06 },
    nifty_50:   { mean: 0.12,  vol: 0.16 },
    nifty_it:   { mean: 0.15,  vol: 0.28 },
    real_estate:{ mean: 0.10,  vol: 0.18 },
    crypto:     { mean: 0.20,  vol: 0.65 },
    gold:       { mean: 0.08,  vol: 0.14 },
  };
  const CORRELATION = 0.3;

  const STARTING_YEAR = 1994;
  const STARTING_MONTH = 4;
  const GAME_LENGTH_MONTHS = 120;
  const WIN_THRESHOLD = 2_000_000;
  const STARTING_CASH = 1_000_000;

  // --- helpers --------------------------------------------------------

  function gaussian() {
    // Box-Muller standard normal
    const u1 = Math.random() || 1e-12;
    const u2 = Math.random();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  }

  function makePrices() {
    const p = {};
    for (const a of ASSETS) p[a] = 1.0;
    return p;
  }

  // --- game state -----------------------------------------------------

  function newGame() {
    return {
      year: STARTING_YEAR,
      month: STARTING_MONTH,
      months_elapsed: 0,
      prices: makePrices(),
      portfolio: Object.fromEntries(ASSETS.map((a) => [a, 0.0])),
      cost_basis: Object.fromEntries(ASSETS.map((a) => [a, 0.0])),
      cash_balance: STARTING_CASH,
      news: {},
      agent_actions: [],
      ledger: [],
      game_over: false,
      won: false,
      last_event: {},
      value_history: [STARTING_CASH],
      price_history: [],
    };
  }

  function totalValue(s) {
    let v = s.cash_balance;
    for (const a of ASSETS) {
      if (a === "cash") continue;
      v += s.portfolio[a] * s.prices[a];
    }
    return v;
  }

  function investedValue(s) {
    let v = 0;
    for (const a of ASSETS) {
      if (a === "cash") continue;
      v += s.portfolio[a] * s.prices[a];
    }
    return v;
  }

  function totalPnl(s) {
    let pnl = 0;
    for (const a of ASSETS) {
      const current = s.portfolio[a] * s.prices[a];
      pnl += current - s.cost_basis[a];
    }
    return pnl;
  }

  // --- price dynamics -------------------------------------------------

  function priceShock(s, impact) {
    for (const a of ASSETS) {
      if (a === "cash") continue;
      if (impact[a] !== undefined) {
        s.prices[a] = s.prices[a] * (1 + Number(impact[a]));
      }
    }
  }

  function randomWalk(s) {
    const tradable = ASSETS.filter((a) => a !== "cash");
    const n = tradable.length;
    const shocks = tradable.map(() => gaussian());
    const meanShock = shocks.reduce((a, b) => a + b, 0) / n;
    const correlated = shocks.map((z) => meanShock * CORRELATION + z * Math.sqrt(1 - CORRELATION * CORRELATION));
    for (let i = 0; i < n; i++) {
      const asset = tradable[i];
      const p = ASSET_PARAMS[asset];
      const monthlyMean = p.mean / 12;
      const monthlyVol = p.vol / Math.sqrt(12);
      const ret = monthlyMean + monthlyVol * correlated[i];
      s.prices[asset] = s.prices[asset] * (1 + ret);
    }
  }

  function applyAgentTrades(s, agentActions) {
    const pressure = Object.fromEntries(ASSETS.map((a) => [a, 0.0]));
    for (const action of agentActions || []) {
      for (const item of action.actions || []) {
        const asset = item.asset;
        if (!(asset in pressure)) continue;
        const amt = Number(item.amount_pct || 0) * (item.action === "buy" ? 1 : -1);
        pressure[asset] += amt;
      }
    }
    for (const a of ASSETS) {
      if (a === "cash") continue;
      s.prices[a] = s.prices[a] * (1 + pressure[a] * 0.03);
    }
  }

  // --- player trades --------------------------------------------------

  function executePlayerTrade(s, asset, action, amountPct) {
    if (!(asset in s.prices)) {
      throw new Error("Unknown asset: " + asset);
    }
    const total = totalValue(s);
    let tradeValue = total * amountPct;

    if (action === "buy") {
      tradeValue = Math.min(tradeValue, s.cash_balance);
      if (tradeValue <= 0) return;
      const price = s.prices[asset];
      const shares = tradeValue / price;
      s.cash_balance -= tradeValue;
      s.portfolio[asset] += shares;
      s.cost_basis[asset] += tradeValue;
    } else if (action === "sell") {
      const price = s.prices[asset];
      const currentValue = s.portfolio[asset] * price;
      const sellValue = Math.min(tradeValue, currentValue);
      if (sellValue <= 0) return;
      const shares = sellValue / price;
      // Reduce cost basis proportionally (average-cost method)
      if (s.portfolio[asset] > 0) {
        const fractionSold = shares / s.portfolio[asset];
        s.cost_basis[asset] = Math.max(0, s.cost_basis[asset] * (1 - fractionSold));
      }
      s.portfolio[asset] -= shares;
      s.cash_balance += sellValue;
    }

    s.ledger.push({
      month: s.month, year: s.year, asset, action,
      amount_pct: amountPct, value: tradeValue,
    });
  }

  // --- advance month --------------------------------------------------

  function advanceMonth(s, news, agentActions, event) {
    if (s.game_over) return;
    s.months_elapsed += 1;
    s.month += 1;
    if (s.month > 12) { s.month = 1; s.year += 1; }

    s.news = news || {};
    s.agent_actions = agentActions || [];
    s.last_event = event || {};

    if (event && event.impact) priceShock(s, event.impact);
    applyAgentTrades(s, agentActions);
    randomWalk(s);

    s.value_history.push(totalValue(s));
    if (s.value_history.length > 240) {
      s.value_history = s.value_history.slice(-240);
    }
    const snap = {};
    for (const a of ASSETS) snap[a] = s.prices[a];
    s.price_history.push(snap);
    if (s.price_history.length > 240) {
      s.price_history = s.price_history.slice(-240);
    }

    if (s.months_elapsed >= GAME_LENGTH_MONTHS) {
      s.game_over = true;
      s.won = totalValue(s) >= WIN_THRESHOLD;
    }
  }

  // --- local NPC agents (deterministic, no LLM needed) ---------------

  function localAgentDecide(persona, state, event) {
    const regime = (event && event.regime) || "stagnation";
    const crashy = ["market_crash", "bear_market", "fii_exit", "high_inflation"].includes(regime);
    const boomy = ["bull_market", "tech_boom", "recovery", "real_estate_boom"].includes(regime);

    let asset, action, amountPct, reason, sentiment;
    if (persona === "whale") {
      if (crashy) {
        asset = "gov_bonds"; action = "buy"; amountPct = 0.15;
        reason = "Flight to safety during the " + regime.replace(/_/g, " ");
        sentiment = "cautious";
      } else if (boomy) {
        asset = "nifty_50"; action = "buy"; amountPct = 0.10;
        reason = "Risk-on into a " + regime.replace(/_/g, " ");
        sentiment = "bullish";
      } else {
        asset = "fd"; action = "buy"; amountPct = 0.05;
        reason = "Park cash, wait for a clearer setup";
        sentiment = "neutral";
      }
    } else if (persona === "retail") {
      if (crashy) {
        asset = "nifty_it"; action = "sell"; amountPct = 0.20;
        reason = "Panic selling into the " + regime.replace(/_/g, " ");
        sentiment = "panic";
      } else if (boomy) {
        asset = "nifty_50"; action = "buy"; amountPct = 0.10;
        reason = "FOMO is real";
        sentiment = "bullish";
      } else {
        asset = "gold"; action = "buy"; amountPct = 0.05;
        reason = "Safe haven while I figure this out";
        sentiment = "neutral";
      }
    } else { // permabull
      if (regime === "crypto_frenzy" || crashy) {
        asset = "crypto"; action = "buy"; amountPct = 0.20;
        reason = "Buy the dip. Crypto only goes up.";
        sentiment = "bullish";
      } else {
        asset = "crypto"; action = "buy"; amountPct = 0.05;
        reason = "DCA forever";
        sentiment = "bullish";
      }
    }
    return {
      agent: persona,
      actions: [{ asset, action, amount_pct: amountPct, reason }],
      sentiment,
    };
  }

  function allLocalAgentsDecide(state, event) {
    return ["whale", "retail", "permabull"].map((p) => localAgentDecide(p, state, event));
  }

  // --- public API -----------------------------------------------------

  window.RetroEngine = {
    ASSETS, REGIMES, ASSET_PARAMS, ASSET_DISPLAY_NAMES: {
      cash: "Cash", fd: "FD", gov_bonds: "Gov Bonds", nifty_50: "Nifty 50",
      nifty_it: "Nifty IT", real_estate: "Real Estate", crypto: "Crypto", gold: "Gold",
    },
    TRADABLE_KEYS: ["fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"],
    STARTING_YEAR, STARTING_MONTH, GAME_LENGTH_MONTHS, WIN_THRESHOLD, STARTING_CASH,
    newGame, totalValue, investedValue, totalPnl,
    priceShock, randomWalk, applyAgentTrades,
    executePlayerTrade, advanceMonth,
    localAgentDecide, allLocalAgentsDecide,
  };
})();
