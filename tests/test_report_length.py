"""Report-length presets budget whole sections without changing output contracts."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from tradingagents.agents import schemas
from tradingagents.agents.analysts import (
    fundamentals_analyst,
    market_analyst,
    news_analyst,
    sentiment_analyst,
)
from tradingagents.agents.context import get_report_length_instruction
from tradingagents.agents.managers.portfolio_manager import create_portfolio_manager
from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.trader.trader import create_trader
from tradingagents.dataflows.config import get_config, run_config, set_config
from tradingagents.default_config import REPORT_LENGTHS, build_default_config
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.reporting import write_report_tree

pytestmark = pytest.mark.unit

CASES = (
    (schemas.ResearchPlan, "rationale",
     {"recommendation": "Overweight", "rationale": "Evidence", "strategic_actions": "Add gradually"}),
    (schemas.TraderProposal, "reasoning",
     {"action": "Buy", "reasoning": "Evidence", "entry_price": "$189.50", "stop_loss": "15%"}),
    (schemas.PortfolioDecision, "investment_thesis",
     {"rating": "Overweight", "executive_summary": "Add gradually", "investment_thesis": "Evidence"}),
    (schemas.SentimentReport, "narrative",
     {"overall_band": "Mixed", "overall_score": 5, "confidence": "low", "narrative": "Evidence"}),
)


@pytest.mark.parametrize("length", REPORT_LENGTHS)
def test_environment_selects_a_validated_preset(monkeypatch, length):
    monkeypatch.setenv("TRADINGAGENTS_REPORT_LENGTH", f" {length.upper()} ")
    assert build_default_config()["report_length"] == length


@pytest.mark.parametrize("length", REPORT_LENGTHS)
def test_cli_preserves_report_length_independently_of_research_depth(monkeypatch, length):
    from cli import run

    monkeypatch.setenv("TRADINGAGENTS_REPORT_LENGTH", length)
    monkeypatch.setattr(run, "DEFAULT_CONFIG", build_default_config())
    selections = {
        "research_depth": 5, "quick_think_llm": "quick", "deep_think_llm": "deep",
        "backend_url": None, "llm_provider": "openai", "output_language": "Vietnamese",
    }
    config = run._build_run_config(selections, checkpoint=None)
    assert config["report_length"] == length
    assert config["max_debate_rounds"] == config["max_risk_discuss_rounds"] == 5
    assert config["output_language"] == "Vietnamese"
    assert config["max_tokens"] is None


@pytest.mark.parametrize("value", ("", None))
def test_unset_or_empty_environment_preserves_standard(monkeypatch, value):
    monkeypatch.delenv("TRADINGAGENTS_REPORT_LENGTH", raising=False)
    if value is not None:
        monkeypatch.setenv("TRADINGAGENTS_REPORT_LENGTH", value)
    assert build_default_config()["report_length"] == "standard"


def test_invalid_environment_fails_explicitly(monkeypatch):
    monkeypatch.setenv("TRADINGAGENTS_REPORT_LENGTH", "short")
    with pytest.raises(ValueError, match="TRADINGAGENTS_REPORT_LENGTH"):
        build_default_config()


@pytest.mark.parametrize("value", ("", "short", None, 300, True, [], {}))
def test_invalid_config_does_not_partially_change_the_run(value):
    before = get_config()
    with pytest.raises(ValueError, match="report_length"):
        set_config({"output_language": "Vietnamese", "report_length": value})
    assert get_config() == before
    with pytest.raises(ValueError, match="report_length"), run_config({"report_length": value}):
        pass


def test_standard_keeps_the_existing_prompt_and_limits():
    before = get_config()
    assert get_report_length_instruction() == ""
    assert get_report_length_instruction("Existing detailed instruction.") == "Existing detailed instruction."
    assert get_config() == before


def test_concise_budgets_the_whole_section_not_each_field():
    with run_config({"report_length": "concise"}):
        instruction = get_report_length_instruction()
    assert "approximately 300 words" in instruction
    assert "all prose fields combined" in instruction
    assert "not 300 words per field" in instruction
    assert "not tool calls" in instruction


def test_run_scopes_are_isolated_and_keep_other_settings():
    def instruction(length):
        with run_config({"report_length": length, "output_language": "Vietnamese"}):
            assert get_config()["output_language"] == "Vietnamese"
            assert get_config()["max_tokens"] is None
            return get_report_length_instruction()

    with ThreadPoolExecutor(max_workers=2) as executor:
        short, long = list(executor.map(instruction, ("concise", "comprehensive")))
    assert "Report length: Concise" in short and "long-form" not in short
    assert "Report length: Comprehensive" in long and "300 words" not in long
    assert get_report_length_instruction() == ""
    with run_config({"report_length": "concise"}):
        with run_config({"report_length": "comprehensive"}):
            assert "Comprehensive" in get_report_length_instruction()
        assert "Concise" in get_report_length_instruction()


@pytest.mark.parametrize("base,field,data", CASES)
@pytest.mark.parametrize("length", REPORT_LENGTHS)
def test_schema_profiles_preserve_fields_validators_and_base_descriptions(base, field, data, length):
    before = deepcopy(base.model_json_schema())
    profile = schemas.report_schema(base, length)
    assert issubclass(profile, base)
    assert profile.model_validate(data).model_dump() == base.model_validate(data).model_dump()
    assert profile.model_json_schema().get("required") == before.get("required")
    for name, property_schema in before["properties"].items():
        actual = profile.model_json_schema()["properties"][name]
        assert {k: v for k, v in actual.items() if k != "description"} == {
            k: v for k, v in property_schema.items() if k != "description"
        }
    assert base.model_json_schema() == before
    if length == "standard":
        assert profile is base
    else:
        description = profile.model_fields[field].description
        assert length in description
        assert "whole-section word budget" in description
        assert "Two to four sentences" not in description
        if base is schemas.SentimentReport:
            assert "develop each section thoroughly" not in description


@pytest.mark.parametrize("length", ("concise", "comprehensive"))
def test_preset_schemas_do_not_relax_ratings_or_numeric_bounds(length):
    with pytest.raises(ValidationError):
        schemas.report_schema(schemas.TraderProposal, length)(action="Short", reasoning="x")
    with pytest.raises(ValidationError):
        schemas.report_schema(schemas.SentimentReport, length)(
            overall_band="Mixed", overall_score=11, confidence="low", narrative="x",
        )


def _state():
    return {
        "company_of_interest": "NVDA", "trade_date": "2026-01-09",
        "messages": [], "asset_type": "stock",
        "investment_plan": "**Recommendation**: Overweight",
        "trader_investment_plan": "**Action**: Buy",
        "market_report": "Current price $189.50; ATR 4.2.",
        "investment_debate_state": {
            "history": "Debate", "bull_history": "Bull", "bear_history": "Bear",
            "current_response": "", "count": 1,
        },
        "risk_debate_state": {
            "history": "Risk", "aggressive_history": "Aggressive",
            "conservative_history": "Conservative", "neutral_history": "Neutral",
            "current_aggressive_response": "", "current_conservative_response": "",
            "current_neutral_response": "", "count": 1,
        },
    }


def _text(prompt):
    if isinstance(prompt, str):
        return prompt
    return "\n".join(m["content"] if isinstance(m, dict) else m.content for m in prompt)


@pytest.mark.parametrize("structured", (False, True))
@pytest.mark.parametrize("factory,base,field,data", (
    (create_research_manager, *CASES[0]),
    (create_trader, *CASES[1]),
    (create_portfolio_manager, *CASES[2]),
    (sentiment_analyst.create_sentiment_analyst, *CASES[3]),
))
def test_structured_and_freetext_agents_use_the_active_run(factory, base, field, data, structured, monkeypatch):
    monkeypatch.setattr(sentiment_analyst.get_news, "func", lambda *a: "News")
    monkeypatch.setattr(sentiment_analyst, "fetch_stocktwits_messages", lambda *a, **k: "Posts")
    monkeypatch.setattr(sentiment_analyst, "fetch_reddit_posts", lambda *a, **k: "Posts")
    captured = []
    llm = MagicMock()

    def bind(schema):
        if not structured:
            raise NotImplementedError("Free text only")
        result = MagicMock()
        result.invoke.side_effect = lambda prompt: (
            captured.append((schema, _text(prompt))) or schema.model_validate(data)
        )
        return result

    llm.with_structured_output.side_effect = bind
    llm.invoke.side_effect = lambda prompt: (
        captured.append((None, _text(prompt))) or MagicMock(content="**Rating**: Overweight")
    )
    node = factory(llm)
    for length in REPORT_LENGTHS:
        with run_config({"report_length": length, "output_language": "Vietnamese"}):
            node(_state())
        schema, prompt = captured[-1]
        assert "Vietnamese" in prompt
        if length == "standard":
            assert "Report length:" not in prompt
            if structured:
                assert schema is base
        else:
            assert f"Report length: {length.title()}" in prompt
            if structured:
                assert length in schema.model_fields[field].description
        if length == "concise":
            assert "approximately 300 words" in prompt
    if structured:
        llm.invoke.assert_not_called()


@pytest.mark.parametrize("module,factory", (
    (market_analyst, market_analyst.create_market_analyst),
    (news_analyst, news_analyst.create_news_analyst),
    (fundamentals_analyst, fundamentals_analyst.create_fundamentals_analyst),
))
@pytest.mark.parametrize("length", REPORT_LENGTHS)
def test_tool_using_analysts_receive_budget_without_losing_tools(module, factory, length, monkeypatch):
    captured = []

    def take_turn(prompt, llm, tools, messages):
        captured.append(_text(prompt.format_messages(messages=messages)))
        assert tools == module.TOOLS
        return MagicMock(), "Report"

    monkeypatch.setattr(module, "take_turn", take_turn)
    with run_config({"report_length": length}):
        factory(MagicMock())(_state())
    prompt = captured[0]
    assert "Markdown table" in prompt
    assert "tool-call date ranges" in prompt
    if length == "standard":
        assert "Report length:" not in prompt
    else:
        assert f"Report length: {length.title()}" in prompt
    if length == "concise":
        assert "very detailed and nuanced" not in prompt
        assert "as much detail as possible" not in prompt


@pytest.mark.parametrize("length", REPORT_LENGTHS)
def test_saved_reports_record_profile_and_never_truncate_sections(tmp_path, length):
    graph = object.__new__(TradingAgentsGraph)
    graph.config = {"report_length": length}
    graph.selected_analysts = ("market",)
    body = " ".join(f"evidence{i}" for i in range(600))
    state = {"market_report": body, "trade_date": "2026-01-09"}
    write_report_tree(state, "NVDA", tmp_path, settings=graph.run_settings())
    assert (tmp_path / "1_analysts" / "market.md").read_text(encoding="utf-8") == body
    markdown = (tmp_path / "complete_report.md").read_text(encoding="utf-8")
    html = (tmp_path / "complete_report.html").read_text(encoding="utf-8")
    assert f"Report length: {length.title()}" in markdown
    assert "Report length" in html and length.title() in html
    assert body in markdown and body in html


def test_report_length_changes_checkpoint_signature():
    graph = object.__new__(TradingAgentsGraph)
    graph.config = build_default_config()
    graph.selected_analysts = ("market",)
    signatures = []
    for length in REPORT_LENGTHS:
        graph.config["report_length"] = length
        signatures.append(graph._run_signature("stock"))
    assert len(set(signatures)) == len(REPORT_LENGTHS)
