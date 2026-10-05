"""
CloudOps AI — Approval and Policy Gate

This module controls whether a remediation proposal
can proceed to execution.

IMPORTANT:
- No AWS resources are modified here.
- Every action requires human approval.
- Only allowlisted actions can pass the policy gate.
- Approval/rejection decisions are stored in PostgreSQL.
"""

from backend.remediation import validate_proposal
from backend.database import save_remediation_approval


def policy_gate(proposal: dict) -> dict:
    """
    Validate a remediation proposal before human approval.
    """

    if not proposal:
        return {
            "allowed": False,
            "reason": "No remediation proposal was provided.",
        }

    validation = validate_proposal(proposal)

    if not validation["valid"]:
        return {
            "allowed": False,
            "reason": validation["reason"],
        }

    return {
        "allowed": True,
        "reason": (
            "Proposal passed the policy gate "
            "and is ready for human approval."
        ),
    }


def approve_proposal(
    proposal: dict,
    approver: str,
) -> dict:
    """
    Approve a remediation proposal.

    This function does NOT execute the action.
    It only records the approval decision.
    """

    policy = policy_gate(proposal)

    if not policy["allowed"]:
        return {
            "success": False,
            "approval_status": "blocked",
            "reason": policy["reason"],
        }

    if not approver:
        return {
            "success": False,
            "approval_status": "rejected",
            "reason": "An authorized approver is required.",
        }

    proposal["approval_status"] = "approved"
    proposal["approved_by"] = approver

    approval_id = save_remediation_approval(
        proposal=proposal,
        approval_status="approved",
        approver=approver,
    )

    return {
        "success": True,
        "approval_status": "approved",
        "approved_by": approver,
        "approval_id": approval_id,
        "reason": (
            "Proposal approved. "
            "No infrastructure action has been executed."
        ),
    }


def reject_proposal(
    proposal: dict,
    approver: str,
    reason: str,
) -> dict:
    """
    Reject a remediation proposal.

    Rejection prevents the proposal from proceeding
    to execution.
    """

    if not proposal:
        return {
            "success": False,
            "approval_status": "rejected",
            "reason": "No remediation proposal was provided.",
        }

    if not approver:
        return {
            "success": False,
            "approval_status": "rejected",
            "reason": "An authorized approver is required.",
        }

    if not reason:
        return {
            "success": False,
            "approval_status": "rejected",
            "reason": "A rejection reason is required.",
        }

    proposal["approval_status"] = "rejected"
    proposal["rejected_by"] = approver
    proposal["rejection_reason"] = reason

    approval_id = save_remediation_approval(
        proposal=proposal,
        approval_status="rejected",
        approver=approver,
        rejection_reason=reason,
    )

    return {
        "success": True,
        "approval_status": "rejected",
        "rejected_by": approver,
        "approval_id": approval_id,
        "reason": reason,
    }