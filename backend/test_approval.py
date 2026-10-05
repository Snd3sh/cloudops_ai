from remediation import create_remediation_proposal
from approval import (
    policy_gate,
    approve_proposal,
    reject_proposal,
)


print("\n========================================")
print("       CLOUDOPS AI APPROVAL TEST")
print("========================================")


# --------------------------------------------------
# HIGH CPU PROPOSAL
# --------------------------------------------------

result = create_remediation_proposal(
    server_id="server-002",
    server_name="Application Server",
    incident_type="High CPU utilization",
    severity="high",
    message="Application Server is running with high CPU utilization of 87.2%.",
)

proposal = result["proposal"]

print("\n--- POLICY GATE ---")

policy = policy_gate(proposal)

print("Allowed:", policy["allowed"])
print("Reason:", policy["reason"])


# --------------------------------------------------
# APPROVE PROPOSAL
# --------------------------------------------------

print("\n--- APPROVE PROPOSAL ---")

approval = approve_proposal(
    proposal,
    approver="admin",
)

print("Success:", approval["success"])
print("Status:", approval["approval_status"])
print("Approved by:", approval.get("approved_by"))
print("Approval ID:", approval.get("approval_id"))
print("Reason:", approval["reason"])
print("Execution status:", proposal["execution_status"])


# --------------------------------------------------
# REJECT PROPOSAL
# --------------------------------------------------

result = create_remediation_proposal(
    server_id="server-003",
    server_name="Database Server",
    incident_type="Server stopped",
    severity="critical",
    message="Database Server is currently stopped.",
)

proposal = result["proposal"]

print("\n--- REJECT PROPOSAL ---")

rejection = reject_proposal(
    proposal,
    approver="admin",
    reason="Recovery requires further investigation.",
)

print("Success:", rejection["success"])
print("Status:", rejection["approval_status"])
print("Rejected by:", rejection.get("rejected_by"))
print("Approval ID:", rejection.get("approval_id"))
print("Reason:", rejection["reason"])


# --------------------------------------------------
# UNSAFE ACTION TEST
# --------------------------------------------------

print("\n--- UNSAFE ACTION TEST ---")

unsafe_proposal = {
    "action": "delete_everything",
    "approval_status": "pending_approval",
    "execution_status": "not_executed",
}

policy = policy_gate(unsafe_proposal)

print("Allowed:", policy["allowed"])
print("Reason:", policy["reason"])


print("\n========================================")
print("           TEST COMPLETE")
print("========================================")