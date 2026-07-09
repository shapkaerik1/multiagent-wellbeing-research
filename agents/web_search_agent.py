"""
Web Search Agent
Enriches the quantitative findings with current policy/news context using
Claude's web_search tool.
"""
from agents.claude_client import ask_claude_with_web_search


def get_policy_context(top_states: list[str]) -> str:
    states_str = ", ".join(top_states)
    prompt = (
        f"Search for recent (last 6 months) news or policy developments related to "
        f"housing affordability, cost of living, or economic relief programs in these "
        f"states: {states_str}. Summarize the 3 most relevant findings in 4-5 sentences "
        f"total, citing sources by name."
    )
    return ask_claude_with_web_search(prompt)


if __name__ == "__main__":
    print(get_policy_context(["California", "New York", "Florida"]))
