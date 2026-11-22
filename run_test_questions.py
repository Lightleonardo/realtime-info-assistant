"""Run the sample questions and record answers + tools used to a raw file.

This script intentionally records ONLY the answers and the tools used — never
the hand-written judgments.  Judgments live in docs/sample_questions.md and are
written by hand so that re-running this script never overwrites them.

Usage (no network to real LLM needed if you set USE_AGENT=0):

    powershell
    $env:EXCHANGERATE_API_KEY="your-real-key"
    python run_test_questions.py

Set USE_AGENT=1 to route through agent.run_agent (requires OPENAI_API_KEY).
Set USE_AGENT=0 to call the tools directly (works for weather without any key;
currency needs EXCHANGERATE_API_KEY).
"""

import os
import sys

# Allow running both from the repo root and from inside tests/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tools

USE_AGENT = os.environ.get("USE_AGENT", "0") == "1"

RAW_FILE = os.path.join("docs", "test_answers_raw.txt")

# ---------------------------------------------------------------------------
# Sample questions covering both APIs
# ---------------------------------------------------------------------------

QUESTIONS = [
    # 1. Weather in a city you know
    "What is the current weather in Lagos?",
    # 2. A currency conversion with an amount
    "Convert 100 USD to NGN.",
    # 3. An ambiguous place ("weather in Springfield")
    "What is the weather in Springfield?",
    # 4. A question that needs both tools
    "What is the weather in Tokyo, and how much is 50 USD in JPY?",
    # 5. An off-topic question (should be declined)
    "Who won the 1998 World Cup?",
]


def _record(question, tools_used, answer):
    """Append one result to the raw file."""
    line = (
        f"Q: {question}\n"
        f"TOOLS_USED: {','.join(tools_used) if tools_used else '(none)'}\n"
        f"ANSWER: {answer}\n"
        f"{'-' * 60}\n"
    )
    with open(RAW_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def _extract_tools_used_from_messages(result):
    """Pull tool names out of an agent result dict."""
    return [
        c["name"]
        for m in result["messages"]
        if m.type == "ai"
        for c in m.tool_calls
    ]


def run_via_tools(question):
    """Run a question by calling the tools directly (no LLM needed).

    Returns (tools_used, answer).  This is a best-effort keyword router so the
    script is useful even without an OpenAI key.
    """
    q = question.lower()
    tools_used = []
    answers = []

    if "weather" in q:
        city = None
        for word in ("in ", "for ", "at "):
            if word in q:
                city = q.split(word, 1)[1].strip().rstrip("?.,!")
                break
        city = city or "Lagos"
        answer = tools.get_current_weather.func(city)
        tools_used.append("get_current_weather")
        answers.append(answer)

    if any(w in q for w in ("convert", "usd", "ngn", "jpy", "currency", "money")):
        import re

        amount_match = re.search(r"(\d+(?:\.\d+)?)", q)
        amount = float(amount_match.group(1)) if amount_match else 100.0
        from_cur = "USD"
        to_cur = "NGN"
        if "to ngn" in q or "in ngn" in q:
            to_cur = "NGN"
        if "to jpy" in q or "in jpy" in q:
            to_cur = "JPY"
        if "usd" in q:
            from_cur = "USD"
        answer = tools.convert_currency.func(amount, from_cur, to_cur)
        tools_used.append("convert_currency")
        answers.append(answer)

    if not answers:
        answer = "I can only help with weather and currency questions."
    else:
        answer = " ".join(answers)

    return tools_used, answer


def run_via_agent(question):
    """Run a question through the agent (requires OPENAI_API_KEY)."""
    import agent

    result = agent.run_agent(question)
    tools_used = []
    # agent.run_agent already appends [Tool(s) used: ...] to the answer; parse it.
    if "[Tool(s) used:" in result:
        answer, _, tools_part = result.rpartition("[Tool(s) used: ")
        tools_used = [t.strip(" ]") for t in tools_part.split(",")]
    else:
        answer = result
    return tools_used, answer


def main():
    os.makedirs("docs", exist_ok=True)
    # Start a fresh raw file each run.
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        f.write("Sample question answers and tools used (raw, no judgments)\n")
        f.write(f"Mode: {'agent' if USE_AGENT else 'direct-tools'}\n")
        f.write("=" * 60 + "\n\n")

    for question in QUESTIONS:
        try:
            if USE_AGENT:
                tools_used, answer = run_via_agent(question)
            else:
                tools_used, answer = run_via_tools(question)
        except Exception as exc:  # noqa: BLE001 — record failures honestly
            tools_used = []
            answer = f"ERROR: {exc}"

        _record(question, tools_used, answer)
        print(f"Recorded: {question!r}")

    print(f"\nRaw results written to {RAW_FILE}")
    print("Write your hand judgments in docs/sample_questions.md.")


if __name__ == "__main__":
    main()