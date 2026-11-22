"""Tests for agent.py — no real model, no real network."""

import httpx
from langchain_core.messages import AIMessage
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langgraph.errors import GraphRecursionError

import agent
import tools


class FakeToolModel(GenericFakeChatModel):
    """A stand-in model that supports tool calling (bind_tools returns self)."""

    def bind_tools(self, tools, **kwargs):
        return self


# ---------------------------------------------------------------------------
# Agent calls a tool and then answers
# ---------------------------------------------------------------------------

def test_agent_calls_tool_and_answers(monkeypatch):
    # Mock the transport so the weather tool never hits the network.
    def handler(request):
        if "search" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "Lagos",
                            "latitude": 6.45,
                            "longitude": 3.4,
                            "country": "Nigeria",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 30.5,
                    "wind_speed_10m": 12.6,
                },
                "current_units": {
                    "temperature_2m": "°C",
                    "wind_speed_10m": "km/h",
                },
            },
        )

    original = tools._transport
    tools._transport = httpx.MockTransport(handler)
    try:
        fake_llm = FakeToolModel(messages=iter([
            AIMessage(content="", tool_calls=[{"name": "get_current_weather", "args": {"city": "Lagos"}, "id": "c1"}]),
            AIMessage(content="It is 30°C in Lagos."),
        ]))
        monkeypatch.setattr(agent, "_build_llm", lambda: fake_llm)

        result = agent.run_agent("What is the weather in Lagos?")

        assert "30°C" in result
        assert "[Tool(s) used: get_current_weather]" in result
    finally:
        tools._transport = original


# ---------------------------------------------------------------------------
# Empty question
# ---------------------------------------------------------------------------

def test_agent_empty_question(monkeypatch):
    fake_llm = FakeToolModel(messages=iter([AIMessage(content="ignored")]))
    monkeypatch.setattr(agent, "_build_llm", lambda: fake_llm)

    result = agent.run_agent("")
    assert result == "Please ask a question."

    result = agent.run_agent("   ")
    assert result == "Please ask a question."


# ---------------------------------------------------------------------------
# Endless tool loop hits the recursion guard
# ---------------------------------------------------------------------------

def test_agent_endless_tool_loop(monkeypatch):
    """A model that keeps requesting tools forever triggers GraphRecursionError,
    which run_agent converts into a friendly message.
    """
    original = tools._transport
    tools._transport = None
    try:
        from langchain.agents import create_agent as real_create_agent

        class FakeGraph:
            def invoke(self, *args, **kwargs):
                raise GraphRecursionError("recursion limit reached")

        monkeypatch.setattr(agent, "create_agent", lambda *a, **k: FakeGraph())
        monkeypatch.setattr(agent, "_build_llm", lambda: object())

        result = agent.run_agent("What is the weather in Lagos?")
        assert "stuck" in result.lower() or "rephrase" in result.lower()
    finally:
        tools._transport = original
        # restore the real import reference
        agent.create_agent = real_create_agent
