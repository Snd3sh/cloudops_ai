from remediation import create_remediation_proposal
from approval import approve_proposal
from executor import execute_remediation


print("\n========================================")
print("       CLOUDOPS AI EXECUTOR TEST")
print("========================================")


# --------------------------------------------------
# CREATE PROPOSAL
# --------------------------------------------------

result = create_remediation_proposal(
    server_id="server-002",
    server_name="Application Server",
    incident_type="High CPU utilization",
    severity="high",
    message="Application Server is running with high CPU utilization of 87.2%.",
)

proposal = result["proposal"]


# --------------------------------------------------
# TRY EXECUTION BEFORE APPROVAL
# --------------------------------------------------

print("\n--- BEFORE APPROVAL ---")

execution = execute_remediation(proposal)

print("Success:", execution["success"])
print("Status:", execution["execution_status"])
print("Reason:", execution["reason"])


# --------------------------------------------------
# APPROVE
# --------------------------------------------------

print("\n--- HUMAN APPROVAL ---")

approval = approve_proposal(
    proposal,
    approver="admin",
)

print("Success:", approval["success"])
print("Status:", approval["approval_status"])
print("Approved by:", approval["approved_by"])


# --------------------------------------------------
# EXECUTE AFTER APPROVAL
# --------------------------------------------------

print("\n--- EXECUTION ---")

execution = execute_remediation(proposal)

print("Success:", execution["success"])
print("Status:", execution["execution_status"])
print("Action:", execution["action"])
print("Message:", execution["message"])
print("AWS modified:", execution["aws_modified"])


# --------------------------------------------------
# TRY DUPLICATE EXECUTION
# --------------------------------------------------

print("\n--- DUPLICATE EXECUTION ---")

execution = execute_remediation(proposal)

print("Success:", execution["success"])
print("Status:", execution["execution_status"])
print("Reason:", execution["reason"])


# --------------------------------------------------
# UNSAFE ACTION
# --------------------------------------------------

print("\n--- UNSAFE ACTION ---")

unsafe_proposal = {
    "proposal_id": "unsafe-001",
    "server_id": "server-002",
    "server_name": "Application Server",
    "action": "delete_everything",
    "approval_status": "approved",
    "execution_status": "not_executed",
}

execution = execute_remediation(unsafe_proposal)

print("Success:", execution["success"])
print("Status:", execution["execution_status"])
print("Reason:", execution["reason"])


print("\n========================================")
print("           TEST COMPLETE")
print("========================================")