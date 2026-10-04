
import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

load_dotenv()


class IncidentState(TypedDict):
    server_name: str
    cpu_usage: float
    status: str
    incident_type: str
    severity: str
    diagnosis: str
    recommendation: str
    agent_type: str


def rule_based_investigation(state: IncidentState) -> dict:
    """Analyze a server incident using deterministic rules."""

    if state["status"].lower() == "stopped":
        return {
            "incident_type": "Server stopped",
            "severity": "critical",
            "diagnosis": (
                f'{state["server_name"]} is stopped and may be '
                "unavailable to users."
            ),
            "recommendation": (
                "Check the server state, recent changes, and system "
                "logs before considering a restart."
            ),
        }

    if state["cpu_usage"] >= 80:
        return {
            "incident_type": "High CPU utilization",
            "severity": "high",
            "diagnosis": (
                f'{state["server_name"]} has high CPU utilization '
                f'({state["cpu_usage"]}%).'
            ),
            "recommendation": (
                "Inspect running processes, application logs, and "
                "recent traffic changes to identify the cause."
            ),
        }

    if state["cpu_usage"] >= 60:
        return {
            "incident_type": "Elevated CPU utilization",
            "severity": "medium",
            "diagnosis": (
                f'{state["server_name"]} has elevated CPU utilization '
                f'({state["cpu_usage"]}%).'
            ),
            "recommendation": (
                "Monitor CPU trends and inspect processes if "
                "utilization continues to rise."
            ),
        }

    return {
        "incident_type": "No major incident detected",
        "severity": "low",
        "diagnosis": (
            f'{state["server_name"]} is running with CPU utilization '
            f'of {state["cpu_usage"]}%.'
        ),
        "recommendation": "Continue monitoring the server.",
    }


def investigate_incident(state: IncidentState) -> dict:
    """Investigate incidents with rules or Gemini."""

    baseline = rule_based_investigation(state)

    # Rules mode: no Gemini API calls.
    ai_mode = os.getenv("AI_MODE", "rules").strip().lower()

    if ai_mode == "rules":
        return {
            **baseline,
            "agent_type": "rule-based",
        }

    # If the API key is missing, use the local rules.
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("GEMINI_API_KEY not configured; using local rules.")
        return {
            **baseline,
            "agent_type": "rule-based fallback",
        }

    try:
        model = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            google_api_key=api_key,
            temperature=0,
            max_retries=0,
        )

        prompt = f"""
You are the incident investigation assistant for CloudOps AI.

Observed server information:
- Server name: {state["server_name"]}
- Status: {state["status"]}
- CPU utilization: {state["cpu_usage"]}%
- Rule-based incident type: {baseline["incident_type"]}
- Rule-based severity: {baseline["severity"]}

Provide:
Incident Type: a short incident description
Diagnosis: a brief explanation
Recommended Action: safe troubleshooting steps

Requirements:
- Use only the provided facts.
- Do not claim an unverified root cause.
- Distinguish possibilities from confirmed facts.
- Recommend read-only investigation first.
- Do not execute actions or recommend automatic destructive changes.
- Keep the response concise.
"""

        response = model.invoke(prompt)
        content = response.content

        if isinstance(content, list):
            content = "\n".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

        content = str(content).strip()

        if not content:
            raise ValueError("Gemini returned an empty response.")

        print("Gemini investigation completed successfully.")

        return {
            **baseline,
            "diagnosis": content,
            "recommendation": (
                "Review the AI analysis and inspect relevant processes "
                "and logs before taking action."
            ),
            "agent_type": "gemini",
        }

    except Exception as error:
        print(
            "Gemini investigation unavailable; "
            f"using rules: {error}"
        )

        return {
            **baseline,
            "agent_type": "rule-based fallback",
        }


# Build the LangGraph workflow.
workflow = StateGraph(IncidentState)

workflow.add_node("investigate", investigate_incident)
workflow.add_edge(START, "investigate")
workflow.add_edge("investigate", END)

incident_graph = workflow.compile()


def analyze_incident(
    server_name: str,
    cpu_usage: float,
    status: str,
) -> dict:
    """Run the incident investigation workflow."""

    initial_state: IncidentState = {
        "server_name": server_name,
        "cpu_usage": cpu_usage,
        "status": status,
        "incident_type": "",
        "severity": "",
        "diagnosis": "",
        "recommendation": "",
        "agent_type": "",
    }

    return incident_graph.invoke(initial_state)
