"""
Retro Alpha market simulation engine.
"""

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

ASSETS = ["cash", "fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"]

REGIMES = [
    "bull_market", "bear_market", "market_crash", "recovery", "high_inflation",
    "rate_hike", "rate_cut", "election_year", "monsoon_shock", "fii_exit",
    "tech_boom", "real_estate_boom", "crypto_frenzy", "gold_rush", "stagnation"
]

# Annualized expected returns and volatilities (calibrated for simulation)
ASSET_PARAMS = {
    "cash":      {"mean": 0.00, "vol": 0.01},
    "fd":        {"mean": 0.065, "vol": 0.005},
    "gov_bonds": {"mean": 0.07, "vol": 0.06},
    "nifty_50":  {"mean": 0.12, "vol": 0.16},
    "nifty_it":  {"mean": 0.15, "vol": 0.28},
    "real_estate":{"mean": 0.10, "vol": 0.18},
    "crypto":    {"mean": 0.20, "vol": 0.65},
    "gold":      {"mean": 0.08, "vol": 0.14},
}

CORRELATION = 0.3

STARTING_YEAR = 1994
STARTING_MONTH = 4
GAME_LENGTH_MONTHS = 120  # 10 years
WIN_THRESHOLD = 2_000_000.0


@dataclass
class GameState:
    year: int = STARTING_YEAR
    month: int = STARTING_MONTH
    months_elapsed: int = 0
    prices: Dict[str, float] = field(default_factory=lambda: {a: 1.0 for a in ASSETS})
    portfolio: Dict[str, float] = field(default_factory=lambda: {a: 0.0 for a in ASSETS})
    cash_balance: float = 1_000_000.0
    news: Dict = field(default_factory=dict)
    agent_actions: List[Dict] = field(default_factory=list)
    ledger: List[Dict] = field(default_factory=list)
    game_over: bool = False
    won: bool = False

    def total_value(self) -> float:
        return float(
            self.cash_balance
            + sum(float(self.portfolio[a]) * float(self.prices[a]) for a in ASSETS)
        )


def new_game(starting_cash: float = 1_000_000.0) -> GameState:
    state = GameState(cash_balance=starting_cash)
    state.portfolio = {a: 0.0 for a in ASSETS}
    return state


def price_shock(state: GameState, impact: Dict[str, float]):
    """Apply a news-driven price shock."""
    for asset in ASSETS:
        if asset == "cash":
            continue
        if asset in impact:
            state.prices[asset] = float(state.prices[asset] * (1 + float(impact[asset])))


def random_walk(state: GameState):
    """Apply monthly random price drift correlated across assets."""
    tradable = [a for a in ASSETS if a != "cash"]
    n = len(tradable)
    corr_matrix = np.full((n, n), CORRELATION) + np.eye(n) * (1 - CORRELATION)
    shocks = np.random.multivariate_normal(np.zeros(n), corr_matrix)
    for i, asset in enumerate(tradable):
        params = ASSET_PARAMS[asset]
        monthly_mean = params["mean"] / 12
        monthly_vol = params["vol"] / np.sqrt(12)
        ret = float(monthly_mean + monthly_vol * shocks[i])
        state.prices[asset] = float(state.prices[asset] * (1 + ret))


def apply_agent_trades(state: GameState, agent_actions: List[Dict]):
    """Apply agent trades to prices via order-flow pressure."""
    pressure = {a: 0.0 for a in ASSETS}
    for action in agent_actions:
        for item in action.get("actions", []):
            asset = item.get("asset", "cash")
            if asset not in pressure:
                continue
            amt = float(item.get("amount_pct", 0.0)) * (1 if item.get("action") == "buy" else -1)
            pressure[asset] += amt
    for asset in ASSETS:
        # Agent flow moves price by up to 3%
        state.prices[asset] = float(state.prices[asset] * (1 + pressure[asset] * 0.03))


def execute_player_trade(state: GameState, asset: str, action: str, amount_pct: float):
    """Execute a player trade. amount_pct is relative to total portfolio value."""
    if asset not in state.prices:
        raise ValueError(f"Unknown asset: {asset}")

    total = float(state.total_value())
    trade_value = float(total * amount_pct)

    if action == "buy":
        trade_value = float(min(trade_value, state.cash_balance))
        if trade_value <= 0:
            return
        price = float(state.prices[asset])
        shares = float(trade_value / price) if price > 0 else 0.0
        state.cash_balance = float(state.cash_balance - trade_value)
        state.portfolio[asset] = float(state.portfolio[asset] + shares)
    elif action == "sell":
        price = float(state.prices[asset])
        current_value = float(state.portfolio[asset] * price)
        sell_value = float(min(trade_value, current_value))
        if sell_value <= 0:
            return
        shares = float(sell_value / price) if price > 0 else 0.0
        state.portfolio[asset] = float(state.portfolio[asset] - shares)
        state.cash_balance = float(state.cash_balance + sell_value)

    state.ledger.append({
        "month": state.month,
        "year": state.year,
        "asset": asset,
        "action": action,
        "amount_pct": float(amount_pct),
        "value": float(trade_value),
    })


def advance_month(state: GameState, news: Dict, agent_actions: List[Dict]):
    """Advance the simulation by one month."""
    if state.game_over:
        return

    state.months_elapsed += 1
    state.month += 1
    if state.month > 12:
        state.month = 1
        state.year += 1

    state.news = news
    state.agent_actions = agent_actions

    if news.get("impact"):
        price_shock(state, news["impact"])

    apply_agent_trades(state, agent_actions)
    random_walk(state)

    if state.months_elapsed >= GAME_LENGTH_MONTHS:
        state.game_over = True
        state.won = bool(state.total_value() >= WIN_THRESHOLD)


def year_end_summary(state: GameState) -> Dict:
    """Compute year-end stats for the mentor."""
    year_ledger = [t for t in state.ledger if t["year"] == state.year]
    values = [float(state.total_value())]  # simplified
    returns = (
        (np.diff(values) / values[:-1]).tolist()
        if len(values) > 1
        else [0.0]
    )
    sharpe = float((np.mean(returns) / (np.std(returns) + 1e-9)) * np.sqrt(12))

    total = float(state.total_value())
    allocations = {}
    for asset in ASSETS:
        val = float(state.portfolio[asset]) * float(state.prices[asset])
        allocations[asset] = round(val / total, 3) if total > 0 else 0.0

    return {
        "year": int(state.year),
        "starting_value": 1_000_000,
        "ending_value": float(total),
        "max_drawdown": -0.25,  # placeholder
        "sharpe_ratio": float(round(sharpe, 2)),
        "allocations": {k: float(v) for k, v in allocations.items()},
        "ledger": year_ledger,
    }

