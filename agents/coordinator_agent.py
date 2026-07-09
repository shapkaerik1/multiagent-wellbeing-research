"""
Coordinator Agent
Synthesizes outputs from the Economic Stress, Culture Disparity, Wellbeing,
and Web Search agents into one unified findings report.
"""
from agents.claude_client import ask_claude


def synthesize_report(econ_summary: str, disparity_summary: str,
                       wellbeing_summary: str, policy_context: str) -> str:
    prompt = f"""You are the Coordinator Agent for a multi-agent research system studying
economic precarity, cultural disparities, and psychological wellbeing across U.S. income groups.

Economic Stress Agent findings:
{econ_summary}

Culture Disparity Agent findings:
{disparity_summary}

Wellbeing Agent findings:
{wellbeing_summary}

Web Search Agent policy context:
{policy_context}

Write a unified 2-paragraph findings summary connecting these four inputs, flagging
any notable cross-domain correlation (e.g. between cost burden, disparity, and distress).
Keep it factual, appropriate for a research report, and note any limitations of the data."""
    return ask_claude(prompt, max_tokens=800)


if __name__ == "__main__":
    print(synthesize_report("econ test", "disparity test", "wellbeing test", "policy test"))
