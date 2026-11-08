"""Offline reading-deck generation and optional-failure boundaries."""

import json
import re
from types import SimpleNamespace

import pytest
from httpx import Request
from markdown_it import MarkdownIt
from openai import APIConnectionError

from tradingagents.default_config import build_default_config
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.reading_slides import _explanations, _research_pages, write_reading_slides
from tradingagents.reporting import write_report_tree


def state():
    return {
        "trade_date": "2026-11-07",
        "market_report": "Market evidence.\n\n<script>alert('source')</script>\n\n"
                         "| Date | Close ($) |\n| --- | --- |\n"
                         "| 2026-11-05 | $100.00 |\n| 2026-11-06 | $110.00 |",
        "sentiment_report": "Sentiment evidence.",
        "news_report": "News evidence.",
        "fundamentals_report": "Fundamentals evidence.",
        "investment_debate_state": {
            "bull_history": "\nBull Analyst: First argument.\n\nBull Analyst: Complete rebuttal.\n",
            "bear_history": "\nBear Analyst: First objection.\n\nBear Analyst: Second objection.\n",
        },
        "investment_plan": "Research manager reasoning.",
        "trader_investment_plan": "Trader complete plan.\n\nFunding and protection remain conditional.",
        "risk_debate_state": {
            "aggressive_history": "Aggressive source.",
            "conservative_history": "Conservative source.",
            "neutral_history": "Neutral source.",
        },
        "final_trade_decision": "Rating: Hold\n\nNo new purchase until funding and protection are confirmed."
                               "\n\nFull final caveats and reassessment conditions.",
    }


class Model:
    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def invoke(self, messages):
        self.calls.append(messages)
        if self.failure:
            raise self.failure
        source = json.loads(messages[1][1])
        return SimpleNamespace(content=json.dumps({
            "main_point": "Read the source reasoning without treating a proposal as approval.",
            "terms": "Funding means how a proposed purchase would be paid for.",
            "uncertainty": "The report's data and conditions are not independently verified.",
            "final_action_connection": "The final Hold decision does not permit a new purchase "
                                       "before funding and protection are confirmed.",
            "risk_summary": "This analyst challenges the plan; uncertainties and conditions "
                            "still apply." if source["condense_risk"] else None,
        }))


@pytest.mark.unit
def test_full_source_rounds_and_decisions_with_only_risk_condensed(tmp_path):
    source = state()
    saved = write_report_tree(source, "TEST", tmp_path, html=False)
    markdown = re.sub(r"Generated: [^\n]+", "Generated: 2026-11-07 19:28:01",
                      saved.read_text(encoding="utf-8"))
    saved.write_text(markdown, encoding="utf-8")
    model = Model()
    progress = []
    output = write_reading_slides(source, "TEST", tmp_path, model,
                                 progress=lambda done, total: progress.append((done, total)))
    html = output.read_text(encoding="utf-8")
    assert "2026-11-07 19:28:01" in html
    md = MarkdownIt("commonmark", {"html": False}).enable("table").disable("image")
    for key in ("market_report", "sentiment_report", "news_report", "fundamentals_report",
                "investment_plan", "trader_investment_plan", "final_trade_decision"):
        assert md.render(source[key]) in html
    for role, key in (("Bull Researcher", "bull_history"), ("Bear Researcher", "bear_history")):
        original = source["investment_debate_state"][key]
        pages = _research_pages(role, original)
        assert "".join(text for _, text in pages) == original
        assert all(md.render(text) in html for _, text in pages)
    assert len(model.calls) == 12
    assert progress == [(i, 12) for i in range(13)]
    assert html.count('class="mode">Condensed source summary') == 3
    assert len(re.findall(r'<section id="slide-', html)) == 15
    assert html.count('aria-label="Plain-English reading guide"') == 15
    assert '<script>alert' not in html
    assert "&lt;script&gt;" in html
    assert 'aria-labelledby="close-title-1 close-desc-1"' in html
    assert "$100.00" in html and "$110.00" in html
    assert "not a complete daily series" in html
    assert "default-src &#x27;none&#x27;" in html
    assert "sha256-" in html
    assert not re.search(r'<(?:script|link|img)[^>]+(?:src|href)=', html)
    assert "[SOURCE:" not in html and "[EXPLANATION:" not in html
    assert not output.with_suffix(".html.tmp").exists()


@pytest.mark.unit
def test_disabled_generation_makes_no_model_calls_and_removes_only_owned_old_deck(tmp_path):
    model = Model()
    graph = SimpleNamespace(run_settings=lambda: {}, deep_thinking_llm=model)
    (tmp_path / "reading_slides.html").write_text("Old deck", encoding="utf-8")
    (tmp_path / "notes.md").write_text("Keep my notes", encoding="utf-8")
    output = TradingAgentsGraph.save_reports(graph, state(), "TEST", tmp_path)
    assert output.is_file()
    assert not model.calls
    assert graph.report_warnings == []
    assert not (tmp_path / "reading_slides.html").exists()
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "Keep my notes"


@pytest.mark.unit
@pytest.mark.parametrize("failure", [
    RuntimeError("Deep model unavailable"), ValueError("Invalid JSON"),
    APIConnectionError(request=Request("POST", "https://llm.example")),
])
def test_slide_failures_warn_without_losing_main_reports(tmp_path, caplog, failure):
    graph = SimpleNamespace(
        run_settings=lambda: {"reading_slides": True}, deep_thinking_llm=Model(failure),
    )
    (tmp_path / "reading_slides.html").write_text("Stale deck", encoding="utf-8")
    output = TradingAgentsGraph.save_reports(graph, state(), "TEST", tmp_path)
    assert output.is_file()
    assert (tmp_path / "complete_report.html").is_file()
    assert (tmp_path / "5_portfolio" / "decision.md").read_text(encoding="utf-8") == state()["final_trade_decision"]
    assert len(graph.report_warnings) == 1
    assert "Primary reports are saved" in graph.report_warnings[0]
    assert "Reading-slides generation failed" in caplog.text
    assert not (tmp_path / "reading_slides.html").exists()


@pytest.mark.unit
@pytest.mark.parametrize("change", [
    {"main_point": ""},
    {"extra": "unexpected"},
    {"main_point": "Invented return 987654%."},
    {"risk_summary": "Forbidden shortened source."},
])
def test_invalid_model_output_is_rejected_before_writing_a_deck(tmp_path, change):
    write_report_tree(state(), "TEST", tmp_path, html=False)
    model = Model()
    original = model.invoke

    def malformed(messages):
        response = original(messages)
        result = json.loads(response.content)
        result.update(change)
        return SimpleNamespace(content=json.dumps(result))

    model.invoke = malformed
    with pytest.raises(ValueError):
        write_reading_slides(state(), "TEST", tmp_path, model)
    assert not (tmp_path / "reading_slides.html").exists()


@pytest.mark.unit
def test_environment_parses_explicit_boolean_without_silent_defaults(monkeypatch):
    monkeypatch.delenv("TRADINGAGENTS_READING_SLIDES", raising=False)
    assert build_default_config()["reading_slides"] is False
    monkeypatch.setenv("TRADINGAGENTS_READING_SLIDES", "true")
    assert build_default_config()["reading_slides"] is True
    monkeypatch.setenv("TRADINGAGENTS_READING_SLIDES", "treu")
    with pytest.raises(ValueError, match="TRADINGAGENTS_READING_SLIDES"):
        build_default_config()


@pytest.mark.unit
def test_source_numbers_can_change_decimal_format_without_being_invented():
    model = Model()
    original = model.invoke

    def response(messages):
        content = json.loads(original(messages).content)
        content["main_point"] = "The reported close of 100 is an observation, not a forecast."
        return SimpleNamespace(content=json.dumps(content))

    model.invoke = response
    explanation = _explanations(model, "Reading instructions", "Market Analyst",
                                state()["market_report"], state()["final_trade_decision"], False)
    assert "100" in explanation["main_point"]
