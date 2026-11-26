"""Run the sample questions and save answers + tools used to a file.

This script only writes down the answers and which tools were used. It never
touches the hand-written judgments in docs/sample_questions.md, so running it
again won't erase your notes.

You can run it without an OpenAI key (USE_AGENT=0). It calls the tools
directly. Currency conversion needs an EXCHANGERATE_API_KEY.
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

# Make sure we can import tools no matter where we run this from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tools

USE_AGENT = os.environ.get("USE_AGENT", "0") == "1"

RAW_FILE = os.path.join("docs", "test_answers_raw.txt")

# A few questions that try both the weather and currency tools.
QUESTIONS = [
    "What is the current weather in Lagos?",
    "Convert 100 USD to NGN.",
    "What is the weather in Springfield?",
    "What is the weather in Tokyo, and how much is 50 USD in JPY?",
    "Who won the 1998 World Cup?",
]


def _record(question, tools_used, answer):
    """Write one question and its answer to the file."""
    line = (
        f"Q: {question}\n"
        f"TOOLS_USED: {','.join(tools_used) if tools_used else '(none)'}\n"
        f"ANSWER: {answer}\n"
        f"{'-' * 60}\n"
    )
    with open(RAW_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def run_via_tools(question):
    """Call the tools directly instead of using the LLM agent.

    This is a simple keyword-based router so the script works even without
    an OpenAI API key. It returns the list of tools used and the answer text.
    """
    q = question.lower()
    tools_used = []
    answers = []

    if "weather" in q:
        # Try to pull out the city name after words like "in", "for", or "at".
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
    """Run a question through the real agent (needs OPENAI_API_KEY)."""
    import agent

    result = agent.run_agent(question)
    tools_used = []
    # The agent already tacks "[Tool(s) used: ...]" onto the answer, so we
    # pull that part back out.
    if "[Tool(s) used:" in result:
        answer, _, tools_part = result.rpartition("[Tool(s) used: ")
        tools_used = [t.strip(" ]") for t in tools_part.split(",")]
    else:
        answer = result
    return tools_used, answer


def main():
    os.makedirs("docs", exist_ok=True)
    # Overwrite the file each time we run.
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
        except Exception as exc:
            # If something blows up, write down what happened instead of
            # crashing the whole script.
            tools_used = []
            answer = f"ERROR: {exc}"

        _record(question, tools_used, answer)
        print(f"Recorded: {question!r}")

    print(f"\nRaw results written to {RAW_FILE}")
    print("Write your hand judgments in docs/sample_questions.md.")


if __name__ == "__main__":
    main()