"""
CloudOps AI — Restricted Remediation Executor

This module executes ONLY approved and allowlisted
remediation actions.

IMPORTANT:
- No arbitrary commands are accepted.
- No free-form AWS operations are accepted.
- Human approval is required.
- Execution is currently simulation-only.
- No AWS resources are modified.
"""

from backend.remediation import ALLOWED_ACTIONS
from backend.database import update_remediation_execution_status


def execute_remediation(proposal: dict) -> dict:
    """
    Execute an approved remediation proposal.

    Current implementation is SAFE/SIMULATED.
    It does not modify AWS resources.
    """

    # --------------------------------------------------
    # 1. Validate proposal exists
    # --------------------------------------------------

    if not proposal:
        return {
            "success": False,
            "execution_status": "blocked",
            "reason": "No remediation proposal was provided.",
        }

    # --------------------------------------------------
    # 2. Validate action allowlist
    # --------------------------------------------------

    action = proposal.get("action")

    if action not in ALLOWED_ACTIONS:
        return {
            "success": False,
            "execution_status": "blocked",
            "reason": f"Action '{action}' is not allowlisted.",
        }

    # --------------------------------------------------
    # 3. Require human approval
    # --------------------------------------------------

    if proposal.get("approval_status") != "approved":
        return {
            "success": False,
            "execution_status": "blocked",
            "reason": (
                "Remediation proposal has not been "
                "approved by an authorized human."
            ),
        }

    # --------------------------------------------------
    # 4. Prevent duplicate execution
    # --------------------------------------------------

    if proposal.get("execution_status") in {
        "executed",
        "simulated",
    }:
        return {
            "success": False,
            "execution_status": "blocked",
            "reason": "Proposal has already been executed.",
        }

    # --------------------------------------------------
    # 5. SIMULATED EXECUTION
    # --------------------------------------------------

    if action == "investigate_high_cpu":

        message = (
            f"Simulated investigation started for "
            f"{proposal['server_name']}. "
            "No infrastructure changes were made."
        )

    elif action == "investigate_stopped_instance":

        message = (
            f"Simulated investigation started for "
            f"{proposal['server_name']}. "
            "No infrastructure changes were made."
        )

    elif action == "restrict_public_security_group":

        message = (
            f"Simulated security-group remediation prepared for "
            f"{proposal['server_name']}. "
            "No AWS security-group rules were modified."
        )

    else:

        return {
            "success": False,
            "execution_status": "blocked",
            "reason": (
                f"No executor implementation exists for "
                f"action '{action}'."
            ),
        }

    # --------------------------------------------------
    # 6. Mark execution as simulated
    # --------------------------------------------------

    proposal["execution_status"] = "simulated"

    update_remediation_execution_status(
        proposal_id=proposal.get("proposal_id"),
        execution_status="simulated",
    )

    return {
        "success": True,
        "execution_status": "simulated",
        "action": action,
        "proposal_id": proposal.get("proposal_id"),
        "server_id": proposal.get("server_id"),
        "message": message,
        "aws_modified": False,
    }