import uuid


"""
CloudOps AI — Remediation Planner

This module creates safe remediation proposals.

IMPORTANT:
- This module does NOT modify AWS resources.
- It does NOT execute actions.
- Every proposal requires human approval.
- Actual execution is implemented later behind a policy gate.
"""


# ============================================================
# ALLOWED REMEDIATION ACTIONS
# ============================================================

ALLOWED_ACTIONS = {
    "investigate_high_cpu",
    "investigate_stopped_instance",
    "restrict_public_security_group",
}


# ============================================================
# REMEDIATION PLANNER
# ============================================================

def create_remediation_proposal(
    server_id: str,
    server_name: str,
    incident_type: str,
    severity: str,
    message: str,
):
    """
    Create a remediation proposal from an incident.

    This function only creates a proposal.
    It never executes an AWS operation.
    """

    incident_type_lower = incident_type.lower()

    # Generate ONE unique proposal ID for every proposal.
    proposal_id = f"proposal-{uuid.uuid4().hex[:12]}"

    # --------------------------------------------------------
    # High CPU
    # --------------------------------------------------------

    if "cpu" in incident_type_lower:
        return {
            "success": True,
            "proposal": {
                "proposal_id": proposal_id,

                "server_id": server_id,
                "server_name": server_name,

                "incident_type": incident_type,
                "severity": severity,
                "message": message,

                "action": "investigate_high_cpu",

                "action_description": (
                    "Investigate processes, application logs, "
                    "traffic patterns, and recent workload changes "
                    "causing high CPU utilization."
                ),

                "reason": (
                    "High CPU utilization was detected. "
                    "The root cause should be identified before "
                    "making infrastructure changes."
                ),

                "impact": (
                    "No infrastructure changes are performed. "
                    "This proposal only requests investigation."
                ),

                "preconditions": [
                    "Target server must exist.",
                    "Server monitoring data must be available.",
                    "Recent CPU metrics should be available.",
                ],

                "verification_plan": [
                    "Review CPU utilization after investigation.",
                    "Identify the process or workload causing CPU usage.",
                    "Confirm whether CPU utilization is improving.",
                ],

                "rollback": (
                    "Not applicable because this proposal "
                    "does not modify infrastructure."
                ),

                "approval_status": "pending_approval",

                "execution_status": "not_executed",

                "allowed": True,
            },
        }

    # --------------------------------------------------------
    # Stopped server
    # --------------------------------------------------------

    if (
        "stopped" in incident_type_lower
        or "stop" in incident_type_lower
    ):
        return {
            "success": True,
            "proposal": {
                "proposal_id": proposal_id,

                "server_id": server_id,
                "server_name": server_name,

                "incident_type": incident_type,
                "severity": severity,
                "message": message,

                "action": "investigate_stopped_instance",

                "action_description": (
                    "Investigate why the instance is stopped "
                    "before considering any recovery action."
                ),

                "reason": (
                    "The instance is currently stopped. "
                    "The cause must be confirmed before attempting "
                    "to start or modify the resource."
                ),

                "impact": (
                    "No infrastructure changes are performed."
                ),

                "preconditions": [
                    "Target server must exist.",
                    "Current instance state must be confirmed.",
                    "The reason for the stopped state should be investigated.",
                ],

                "verification_plan": [
                    "Confirm the current instance state.",
                    "Review relevant monitoring and event information.",
                    "Determine whether recovery is actually required.",
                ],

                "rollback": (
                    "Not applicable because this proposal "
                    "does not modify infrastructure."
                ),

                "approval_status": "pending_approval",

                "execution_status": "not_executed",

                "allowed": True,
            },
        }

    # --------------------------------------------------------
    # Security finding
    # --------------------------------------------------------

    if (
        "ssh" in incident_type_lower
        or "rdp" in incident_type_lower
        or "unrestricted" in incident_type_lower
        or "security" in incident_type_lower
    ):
        return {
            "success": True,
            "proposal": {
                "proposal_id": proposal_id,

                "server_id": server_id,
                "server_name": server_name,

                "incident_type": incident_type,
                "severity": severity,
                "message": message,

                "action": "restrict_public_security_group",

                "action_description": (
                    "Review the affected security-group rule "
                    "and restrict public inbound access to "
                    "trusted network ranges."
                ),

                "reason": (
                    "A security configuration may expose a "
                    "resource to unrestricted inbound access."
                ),

                "impact": (
                    "Changing the security-group rule could affect "
                    "legitimate network access. Human approval is "
                    "required before any change."
                ),

                "preconditions": [
                    "Affected security group must be identified.",
                    "Current inbound rules must be confirmed.",
                    "Trusted source IP ranges must be known.",
                    "The exact rule to change must be identified.",
                ],

                "verification_plan": [
                    "Confirm the security-group rule after the action.",
                    "Verify that unrestricted access has been removed.",
                    "Verify that required application access still works.",
                ],

                "rollback": (
                    "Restore the previous security-group rule "
                    "if approved access is unintentionally affected."
                ),

                "approval_status": "pending_approval",

                "execution_status": "not_executed",

                "allowed": True,
            },
        }

    # --------------------------------------------------------
    # No safe proposal
    # --------------------------------------------------------

    return {
        "success": False,
        "proposal": None,
        "reason": (
            "No approved remediation template exists for "
            f"incident type: {incident_type}"
        ),
    }


# ============================================================
# PROPOSAL VALIDATION
# ============================================================

def validate_proposal(proposal: dict) -> dict:
    """
    Validate that a remediation proposal uses an allowlisted action.

    This is a safety check only.
    It does not execute anything.
    """

    if not proposal:
        return {
            "valid": False,
            "reason": "Proposal is empty.",
        }

    action = proposal.get("action")

    if action not in ALLOWED_ACTIONS:
        return {
            "valid": False,
            "reason": f"Action '{action}' is not allowlisted.",
        }

    if proposal.get("approval_status") != "pending_approval":
        return {
            "valid": False,
            "reason": "Proposal is not waiting for human approval.",
        }

    if proposal.get("execution_status") != "not_executed":
        return {
            "valid": False,
            "reason": "Proposal has already been executed.",
        }

    return {
        "valid": True,
        "reason": "Proposal passed the initial safety checks.",
    }