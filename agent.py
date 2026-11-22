import os

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)

from tools import TOOLS

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about live weather and "
    "currency information. You MUST always use a tool to fetch live data and "
    "never guess or make up numbers. If a tool returns an error, explain it "
    "plainly to the user in one short sentence. If the user asks about a topic "
    "other than weather or currency, politely decline and say you can only help "
    "with weather and currency questions."
)


def _build_llm():
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    kwargs = {"model": model, "api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def run_agent(question: str) -> str:
    """Run the agent on a user question and return the answer text.

    Returns a friendly message for empty questions, tool-loop guards, and
    language-model errors without exposing URLs or keys.
    """
    if not question or not question.strip():
        return "Please ask a question."

    llm = _build_llm()
    agent = create_agent(llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"recursion_limit": 8},
        )
    except GraphRecursionError:
        return "The assistant got stuck trying to use tools. Please rephrase your question."
    except AuthenticationError:
        return "Language model authentication failed. Check your OpenAI API key."
    except RateLimitError:
        return "The language model is rate-limiting requests. Please wait and try again."
    except APIConnectionError:
        return "Could not connect to the language model service. Check your connection."
    except APIStatusError as exc:
        return f"The language model service returned an error ({exc.status_code})."

    answer = result["messages"][-1].content

    # Show which tool was used (evidence the assistant identified the right API).
    tools_used = [
        c["name"]
        for m in result["messages"]
        if m.type == "ai"
        for c in m.tool_calls
    ]
    if tools_used:
        answer = f"{answer}\n\n[Tool(s) used: {', '.join(tools_used)}]"

    return answer


def main() -> None:
    print("Realtime Info Assistant")
    print("Ask about weather or currency. Press Ctrl+C or Ctrl+D to exit.")
    while True:
        try:
            question = input("\nQuestion: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not question or not question.strip():
            print("Please ask a question.")
            continue
        print(run_agent(question))


if __name__ == "__main__":
    main()