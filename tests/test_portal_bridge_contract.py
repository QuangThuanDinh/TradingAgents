"""Interfaces used by the external viewer's progress bridge."""

from inspect import signature

import pytest

from cli import main, run
from tradingagents.default_config import build_default_config


@pytest.mark.unit
def test_external_progress_bridge_interfaces_remain_available():
    assert callable(main.app)
    assert callable(run.Live)
    assert callable(run.update_display)
    assert "stats_handler" in signature(run.update_display).parameters
    buffer = run.message_buffer
    assert isinstance(buffer.agent_status, dict)
    assert isinstance(buffer.report_sections, dict)
    assert callable(buffer.update_agent_status)
    assert isinstance(buffer.get_completed_reports_count(), int)
    assert isinstance(run.StatsCallbackHandler().get_stats(), dict)
    assert signature(run.TradingAgentsGraph.save_reports).parameters["html"].default is True


@pytest.mark.unit
def test_fork_news_overrides_and_report_preset_defaults():
    config = build_default_config()
    assert config["report_length"] == "standard"
    assert config["tool_vendors"] == {
        "get_news": "alpha_vantage,yfinance",
        "get_global_news": "alpha_vantage,yfinance",
    }
