"""Unit tests for the Retro Alpha engine."""

import pytest

import engine


def test_new_game():
    state = engine.new_game()
    assert state.cash_balance == 1_000_000
    assert state.total_value() == 1_000_000
    assert state.year == engine.STARTING_YEAR
    assert state.month == engine.STARTING_MONTH
    assert state.months_elapsed == 0
    assert all(state.portfolio[a] == 0.0 for a in engine.ASSETS)
    assert state.game_over is False


def test_trade_buy():
    state = engine.new_game()
    engine.execute_player_trade(state, "nifty_50", "buy", 0.5)
    assert state.cash_balance < 1_000_000
    assert state.portfolio["nifty_50"] > 0
    assert len(state.ledger) == 1


def test_trade_sell():
    state = engine.new_game()
    engine.execute_player_trade(state, "nifty_50", "buy", 0.5)
    engine.execute_player_trade(state, "nifty_50", "sell", 0.5)
    assert state.cash_balance > 0


def test_trade_invalid_asset():
    state = engine.new_game()
    with pytest.raises(ValueError):
        engine.execute_player_trade(state, "banana", "buy", 0.1)


def test_advance_month():
    state = engine.new_game()
    news = {"headline": "Test", "impact": {a: 0.0 for a in engine.ASSETS}, "duration_months": 1}
    engine.advance_month(state, news, [])
    assert state.months_elapsed == 1
    assert state.month == engine.STARTING_MONTH + 1
    assert state.year == engine.STARTING_YEAR


def test_advance_year_rollover():
    state = engine.new_game()
    state.month = 12
    news = {"headline": "Test", "impact": {a: 0.0 for a in engine.ASSETS}, "duration_months": 1}
    engine.advance_month(state, news, [])
    assert state.month == 1
    assert state.year == engine.STARTING_YEAR + 1


def test_game_over_at_120_months():
    state = engine.new_game()
    state.months_elapsed = 119
    news = {"headline": "Test", "impact": {a: 0.0 for a in engine.ASSETS}, "duration_months": 1}
    engine.advance_month(state, news, [])
    assert state.months_elapsed == 120
    assert state.game_over is True


def test_cash_price_stable():
    state = engine.new_game()
    for _ in range(20):
        state.months_elapsed += 1
        engine.random_walk(state)
    assert abs(state.prices["cash"] - 1.0) < 1e-9


def test_winning_threshold():
    state = engine.new_game()
    state.cash_balance = 3_000_000
    state.months_elapsed = 119
    news = {"headline": "Test", "impact": {a: 0.0 for a in engine.ASSETS}, "duration_months": 1}
    engine.advance_month(state, news, [])
    assert state.won is True
