"""Each model tier can name its own provider (#1440).

The quick tier (analysts, researchers, debaters, trader) and the deep tier
(research and portfolio managers) default to ``llm_provider``. A tier that names
another provider gets that provider's own settings and endpoint, never the main
provider's URL, and the run's settings and report say which provider each used.
"""

import json

import httpx
import pytest

from tradingagents import default_config
from tradingagents.llm_clients import factory


def _config(**overrides):
    config = {**default_config.DEFAULT_CONFIG, "llm_provider": "openai", "backend_url": "https://api.openai.com/v1",
              "quick_think_llm": "gpt-6-luna", "deep_think_llm": "gpt-6-sol",
              "openai_reasoning_effort": "low", "google_thinking_level": "high"}
    config.update(overrides)
    return config


def _captured(monkeypatch):
    made = []
    monkeypatch.setattr(factory, "create_llm_client",
                        lambda provider, model, base_url=None, **kw: made.append((provider, model, base_url, kw)))
    return made


@pytest.mark.unit
def test_a_tier_without_its_own_provider_uses_the_run_s(monkeypatch):
    made = _captured(monkeypatch)

    factory.create_tier_client(_config(), "deep")

    provider, model, base_url, kw = made[0]
    assert (provider, model, base_url) == ("openai", "gpt-6-sol", "https://api.openai.com/v1")
    assert kw["reasoning_effort"] == "low"


@pytest.mark.unit
def test_a_tier_on_another_provider_gets_that_provider_s_settings_and_not_the_main_url(monkeypatch):
    made = _captured(monkeypatch)

    factory.create_tier_client(_config(deep_think_provider="google", deep_think_llm="gemini-3.8-flash"), "deep")

    provider, model, base_url, kw = made[0]
    assert (provider, model) == ("google", "gemini-3.8-flash")
    assert base_url is None                       # the OpenAI URL must not follow it
    assert kw["thinking_level"] == "high" and "reasoning_effort" not in kw


@pytest.mark.unit
def test_a_tier_url_is_used_for_that_tier_only(monkeypatch):
    made = _captured(monkeypatch)
    config = _config(quick_think_provider="openai_compatible", quick_think_backend_url="http://localhost:8000/v1",
                     quick_think_llm="local-model")

    factory.create_tier_client(config, "quick")
    factory.create_tier_client(config, "deep")

    assert made[0][:3] == ("openai_compatible", "local-model", "http://localhost:8000/v1")
    assert made[1][:3] == ("openai", "gpt-6-sol", "https://api.openai.com/v1")


@pytest.mark.unit
def test_the_run_settings_and_report_name_each_tier_s_provider():
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.reporting import _header

    graph = object.__new__(TradingAgentsGraph)
    graph.selected_analysts = ("market",)
    graph.config = _config(deep_think_provider="anthropic", deep_think_llm="claude-opus-5-5")

    settings = graph.run_settings()
    assert settings["quick_think_provider"] == "openai" and settings["deep_think_provider"] == "anthropic"
    header = _header("NVDA", {}, settings)
    assert "deep anthropic claude-opus-5-5" in header and "quick openai gpt-6-luna" in header


@pytest.mark.unit
def test_the_tier_settings_are_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("TRADINGAGENTS_DEEP_THINK_PROVIDER", "anthropic")
    monkeypatch.setenv("TRADINGAGENTS_QUICK_THINK_BACKEND_URL", "http://localhost:8000/v1")

    config = default_config.build_default_config()

    assert config["deep_think_provider"] == "anthropic"
    assert config["quick_think_backend_url"] == "http://localhost:8000/v1"
    assert config["quick_think_provider"] is None


@pytest.mark.unit
@pytest.mark.parametrize("quick_protocol", ["openai-completions", "openai-responses"])
@pytest.mark.parametrize("provider,base_url", [
    ("openai", "http://local.test/v1"),
    ("openai", "https://api.openai.com/v1"),
    ("openai_compatible", "http://local.test/v1"),
])
def test_tier_protocols_route_requests_independently(monkeypatch, quick_protocol, provider, base_url):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/v1/responses":
            payload = {
                "id": "resp_test", "object": "response", "created_at": 1,
                "model": "gpt-5.5", "status": "completed", "error": None,
                "output": [{
                    "id": "msg_test", "type": "message", "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "ok", "annotations": []}],
                }],
            }
        else:
            payload = {
                "id": "chatcmpl_test", "object": "chat.completion", "created": 1,
                "model": "gpt-5.5",
                "choices": [{
                    "index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }],
            }
        return httpx.Response(200, json=payload)

    deep_protocol = (
        "openai-responses" if quick_protocol == "openai-completions" else "openai-completions"
    )
    config = _config(
        llm_provider=provider, backend_url=base_url,
        quick_think_llm="gpt-5.5", deep_think_llm="gpt-5.5",
        quick_think_protocol=quick_protocol, deep_think_protocol=deep_protocol,
    )
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        for tier, protocol in (("quick", quick_protocol), ("deep", deep_protocol)):
            llm = factory.create_tier_client(config, tier, http_client=http_client).get_llm()
            tool = {
                "name": "lookup", "description": "Look up a ticker",
                "parameters": {"type": "object", "properties": {"ticker": {"type": "string"}}},
            }
            assert llm.bind_tools([tool]).invoke("hello").content == "ok"
            request = requests[-1]
            body = json.loads(request.content)
            responses = protocol == "openai-responses"
            assert request.url.path == ("/v1/responses" if responses else "/v1/chat/completions")
            assert ("input" if responses else "messages") in body
            assert body["tools"][0]["type"] == "function"
    assert len(requests) == 2


@pytest.mark.unit
def test_unset_tier_protocol_keeps_its_default(monkeypatch):
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    config = _config(
        llm_provider="openai_compatible", backend_url="http://local.test/v1",
        quick_think_protocol="openai-responses", deep_think_protocol=None,
    )
    quick = factory.create_tier_client(config, "quick").get_llm()
    deep = factory.create_tier_client(config, "deep").get_llm()
    assert quick.use_responses_api is True
    assert deep.use_responses_api in (False, None)


@pytest.mark.unit
@pytest.mark.parametrize("tier", ["quick", "deep"])
@pytest.mark.parametrize(
    "provider,tier_provider",
    [("google", None), ("google", "openai_compatible"), ("openai_compatible", "google"),
     ("openai", "anthropic"), ("chatgpt", None)],
)
def test_protocol_override_rejects_other_providers(monkeypatch, tier, provider, tier_provider):
    made = _captured(monkeypatch)
    config = _config(
        llm_provider=provider,
        **{f"{tier}_think_provider": tier_provider, f"{tier}_think_protocol": "openai-responses"},
    )
    with pytest.raises(ValueError, match=f"{tier}_think_protocol requires"):
        factory.create_tier_client(config, tier)
    assert made == []


@pytest.mark.unit
@pytest.mark.parametrize("tier", ["quick", "deep"])
@pytest.mark.parametrize("protocol", ["responses", "", True, 123])
def test_invalid_protocol_fails_before_client_creation(monkeypatch, tier, protocol):
    made = _captured(monkeypatch)
    config = _config(llm_provider="openai_compatible", **{f"{tier}_think_protocol": protocol})
    with pytest.raises(ValueError, match=f"{tier}_think_protocol must be"):
        factory.create_tier_client(config, tier)
    assert made == []
