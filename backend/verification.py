"""
CloudOps AI — Remediation Verification

This module verifies whether a remediation produced
the expected outcome.

IMPORTANT:
- Verification is read-only.
- It does NOT modify AWS resources.
- It does NOT assume execution was successful.
"""


def verify_remediation(
    proposal: dict,
    current_cpu: float | None = None,
    previous_cpu: float | None = None,
) -> dict:
    """
    Verify the expected result of a remediation proposal.

    For high CPU incidents:
    - current CPU must be available
    - previous CPU must be available
    - CPU should decrease
    - CPU below 80% is considered healthy

    No AWS resources are modified.
    """

    if not proposal:
        return {
            "success": False,
            "verification_status": "failed",
            "reason": "No remediation proposal was provided.",
            "aws_modified": False,
        }

    if proposal.get("execution_status") != "simulated":
        return {
            "success": False,
            "verification_status": "not_ready",
            "reason": (
                "Remediation has not been executed. "
                "Verification cannot start."
            ),
            "aws_modified": False,
        }

    action = proposal.get("action")

    # --------------------------------------------------------
    # High CPU verification
    # --------------------------------------------------------

    if action == "investigate_high_cpu":

        if current_cpu is None:
            return {
                "success": False,
                "verification_status": "unavailable",
                "reason": "Current CPU data is not available.",
                "aws_modified": False,
            }

        if previous_cpu is None:
            return {
                "success": False,
                "verification_status": "unavailable",
                "reason": "Previous CPU data is not available.",
                "aws_modified": False,
            }

        cpu_change = round(current_cpu - previous_cpu, 2)

        # CPU decreased and is now below the high threshold.
        if current_cpu < previous_cpu and current_cpu < 80:
            status = "verified"
            reason = (
                f"CPU utilization improved from {previous_cpu}% "
                f"to {current_cpu}% and is now below the high-CPU threshold."
            )

        # CPU decreased, but is still high.
        elif current_cpu < previous_cpu:
            status = "partially_verified"
            reason = (
                f"CPU utilization improved from {previous_cpu}% "
                f"to {current_cpu}%, but remains at or above 80%."
            )

        # CPU did not improve.
        else:
            status = "not_improved"
            reason = (
                f"CPU utilization did not improve. "
                f"Previous: {previous_cpu}%, current: {current_cpu}%."
            )

        return {
            "success": status in {"verified", "partially_verified"},
            "verification_status": status,
            "server_id": proposal.get("server_id"),
            "server_name": proposal.get("server_name"),
            "proposal_id": proposal.get("proposal_id"),
            "previous_cpu": previous_cpu,
            "current_cpu": current_cpu,
            "cpu_change": cpu_change,
            "reason": reason,
            "aws_modified": False,
        }

    # --------------------------------------------------------
    # Stopped instance verification
    # --------------------------------------------------------

    if action == "investigate_stopped_instance":
        return {
            "success": True,
            "verification_status": "verified",
            "server_id": proposal.get("server_id"),
            "server_name": proposal.get("server_name"),
            "proposal_id": proposal.get("proposal_id"),
            "reason": (
                "Investigation was simulated successfully. "
                "No infrastructure recovery action was performed."
            ),
            "aws_modified": False,
        }

    # --------------------------------------------------------
    # Security-group verification
    # --------------------------------------------------------

    if action == "restrict_public_security_group":
        return {
            "success": False,
            "verification_status": "not_executed",
            "server_id": proposal.get("server_id"),
            "server_name": proposal.get("server_name"),
            "proposal_id": proposal.get("proposal_id"),
            "reason": (
                "Security-group remediation is currently simulation-only. "
                "No AWS security-group rule was modified."
            ),
            "aws_modified": False,
        }

    # --------------------------------------------------------
    # Unknown action
    # --------------------------------------------------------

    return {
        "success": False,
        "verification_status": "unsupported",
        "reason": f"No verification logic exists for action '{action}'.",
        "aws_modified": False,
    }