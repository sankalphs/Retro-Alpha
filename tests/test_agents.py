"""Unit tests for agent inference helpers."""

import agents


def test_parse_agent_response():
    response = "agent: whale\naction: buy gov_bonds 0.15\nreason: safety\nsentiment: cautious"
    parsed = agents.parse_agent_response(response, "whale")
    assert parsed["agent"] == "whale"
    assert parsed["actions"][0]["asset"] == "gov_bonds"
    assert parsed["actions"][0]["amount_pct"] == 0.15


def test_parse_news_response():
    response = "headline: RBI hikes\nimpact: cash:0 fd:0.1 gov_bonds:-0.05 nifty_50:-0.05 nifty_it:-0.05 real_estate:-0.05 crypto:-0.05 gold:0.05\nduration: 3"
    parsed = agents.parse_news_response(response)
    assert parsed["headline"] == "RBI hikes"
    assert "cash" in parsed["impact"]
    assert parsed["duration_months"] == 3


def test_mock_generate():
    result = agents.mock_generate("agent whale", "")
    assert "agent:" in result
