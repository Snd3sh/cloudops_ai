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

    monitoring_result: str
    diagnosis: str
    recommendation: str

    agent_type: str


# ============================================================
# AGENT 1: MONITORING AGENT
# ============================================================

def monitoring_agent(state: IncidentState) -> dict:
    """
    Analyze the basic health information of the server.

    This agent focuses only on observed metrics and server state.
    It does not try to determine the root cause.
    """

    server_name = state["server_name"]
    cpu_usage = state["cpu_usage"]
    status = state["status"].lower()

    if status == "stopped":
        return {
            "incident_type": "Server stopped",
            "severity": "critical",
            "monitoring_result": (
                f"{server_name} is currently stopped. "
                "The server may be unavailable to users."
            ),
        }

    if cpu_usage >= 80:
        return {
            "incident_type": "High CPU utilization",
            "severity": "high",
            "monitoring_result": (
                f"{server_name} is running with high CPU utilization "
                f"of {cpu_usage}%."
            ),
        }

    if cpu_usage >= 60:
        return {
            "incident_type": "Elevated CPU utilization",
            "severity": "medium",
            "monitoring_result": (
                f"{server_name} is running with elevated CPU utilization "
                f"of {cpu_usage}%."
            ),
        }

    return {
        "incident_type": "No major incident detected",
        "severity": "low",
        "monitoring_result": (
            f"{server_name} is running normally with CPU utilization "
            f"of {cpu_usage}%."
        ),
    }


# ============================================================
# AGENT 2: DIAGNOSIS AGENT
# ============================================================

def diagnosis_agent(state: IncidentState) -> dict:
    """
    Determine a safe diagnosis based only on information
    produced by the monitoring agent.
    """

    incident_type = state["incident_type"]
    severity = state["severity"]
    monitoring_result = state["monitoring_result"]

    if incident_type == "Server stopped":
        diagnosis = (
            f"{monitoring_result} "
            "The available information confirms the server is stopped, "
            "but it does not confirm why it stopped."
        )

    elif incident_type == "High CPU utilization":
        diagnosis = (
            f"{monitoring_result} "
            "Possible causes include resource-intensive processes, "
            "increased application workload, or unusual traffic. "
            "The root cause is not confirmed from CPU data alone."
        )

    elif incident_type == "Elevated CPU utilization":
        diagnosis = (
            f"{monitoring_result} "
            "The CPU load is above the normal monitoring threshold. "
            "Further monitoring is required to determine whether "
            "the condition is temporary or persistent."
        )

    else:
        diagnosis = (
            f"{monitoring_result} "
            "No major incident is indicated by the available "
            "server status and CPU information."
        )

    return {
        "diagnosis": diagnosis,
        "agent_type": "multi-agent-rule-based",
    }


# ============================================================
# AGENT 3: RECOMMENDATION AGENT
# ============================================================

def recommendation_agent(state: IncidentState) -> dict:
    """
    Generate safe troubleshooting recommendations.

    This agent does not execute any action.
    """

    incident_type = state["incident_type"]
    severity = state["severity"]

    if incident_type == "Server stopped":
        recommendation = (
            "Check the server state, recent changes, system logs, "
            "and monitoring events. Verify the reason for the stopped "
            "state before considering a restart."
        )

    elif incident_type == "High CPU utilization":
        recommendation = (
            "Inspect running processes, application logs, recent "
            "traffic changes, and CPU trends. Identify the source "
            "of the high CPU usage before taking corrective action."
        )

    elif incident_type == "Elevated CPU utilization":
        recommendation = (
            "Continue monitoring CPU trends and inspect running "
            "processes if utilization continues to increase."
        )

    else:
        recommendation = (
            "Continue monitoring the server and investigate further "
            "only if its status or resource utilization changes."
        )

    return {
        "recommendation": recommendation,
    }


# ============================================================
# AGENT 4: FINAL REPORT AGENT
# ============================================================

def final_report_agent(state: IncidentState) -> dict:
    """
    Combine the outputs of the previous agents into the final
    incident investigation result.
    """

    return {
        "incident_type": state["incident_type"],
        "severity": state["severity"],
        "diagnosis": state["diagnosis"],
        "recommendation": state["recommendation"],
        "agent_type": state.get(
            "agent_type",
            "multi-agent-rule-based",
        ),
    }


# ============================================================
# OPTIONAL GEMINI ENHANCEMENT
# ============================================================

def gemini_enhancement(state: IncidentState) -> dict:
    """
    Optionally enhance the diagnosis using Gemini.

    Gemini is only used when AI_MODE is not 'rules'.

    If Gemini is unavailable, the existing rule-based diagnosis
    remains unchanged.
    """

    ai_mode = os.getenv("AI_MODE", "rules").strip().lower()

    if ai_mode == "rules":
        return {}

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print(
            "GEMINI_API_KEY not configured; "
            "using multi-agent rules."
        )
        return {}

    try:
        model = ChatGoogleGenerativeAI(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            ),
            google_api_key=api_key,
            temperature=0,
            max_retries=0,
        )

        prompt = f"""
You are the diagnosis specialist in CloudOps AI.

Server:
{state["server_name"]}

Status:
{state["status"]}

CPU:
{state["cpu_usage"]}%

Incident:
{state["incident_type"]}

Severity:
{state["severity"]}

Monitoring result:
{state["monitoring_result"]}

Current diagnosis:
{state["diagnosis"]}

Provide a concise improved diagnosis.

Rules:
- Use only the provided facts.
- Do not claim an unverified root cause.
- Clearly distinguish possibilities from confirmed facts.
- Do not recommend destructive actions.
- Do not execute any action.
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

        print("Gemini diagnosis enhancement completed.")

        return {
            "diagnosis": content,
            "agent_type": "multi-agent-gemini",
        }

    except Exception as error:
        print(
            "Gemini unavailable; "
            f"using multi-agent rules: {error}"
        )

        return {}


# ============================================================
# BUILD LANGGRAPH
# ============================================================

workflow = StateGraph(IncidentState)

# Register agents as graph nodes.
workflow.add_node(
    "monitoring_agent",
    monitoring_agent,
)

workflow.add_node(
    "diagnosis_agent",
    diagnosis_agent,
)

workflow.add_node(
    "gemini_enhancement",
    gemini_enhancement,
)

workflow.add_node(
    "recommendation_agent",
    recommendation_agent,
)

workflow.add_node(
    "final_report_agent",
    final_report_agent,
)


# ============================================================
# GRAPH FLOW
# ============================================================

workflow.add_edge(
    START,
    "monitoring_agent",
)

workflow.add_edge(
    "monitoring_agent",
    "diagnosis_agent",
)

workflow.add_edge(
    "diagnosis_agent",
    "gemini_enhancement",
)

workflow.add_edge(
    "gemini_enhancement",
    "recommendation_agent",
)

workflow.add_edge(
    "recommendation_agent",
    "final_report_agent",
)

workflow.add_edge(
    "final_report_agent",
    END,
)


incident_graph = workflow.compile()


# ============================================================
# PUBLIC FUNCTION USED BY main.py
# ============================================================

def analyze_incident(
    server_name: str,
    cpu_usage: float,
    status: str,
) -> dict:
    """
    Run the complete multi-agent incident investigation.
    """

    initial_state: IncidentState = {
        "server_name": server_name,
        "cpu_usage": cpu_usage,
        "status": status,

        "incident_type": "",
        "severity": "",

        "monitoring_result": "",
        "diagnosis": "",
        "recommendation": "",

        "agent_type": "",
    }

    return incident_graph.invoke(initial_state)