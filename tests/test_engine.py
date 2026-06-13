"""Unit tests for the Retro Alpha engine."""

import pytest

import engine


def test_new_game():
    state = engine.new_game()
    assert state.cash_balance == 1_000_000
    assert state.total_value() == 1_000_000
    assert all(state.portfolio[a] == 0.0 for a in engine.ASSETS)


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


def test_advance_month():
    state = engine.new_game()
    news = {"headline": "Test", "impact": {a: 0.0 for a in engine.ASSETS}, "duration_months": 1}
    engine.advance_month(state, news, [])
    assert state.month == 1
    assert state.year == 1


def test_game_over():
    state = engine.new_game()
    state.year = 11
    state.month = 1
    news = {"headline": "Test", "impact": {a: 0.0 for a in engine.ASSETS}, "duration_months": 1}
    engine.advance_month(state, news, [])
    assert state.game_over
