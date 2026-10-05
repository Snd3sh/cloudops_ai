from remediation import (
    create_remediation_proposal,
    validate_proposal,
)


print("\n========================================")
print("      CLOUDOPS AI REMEDIATION TEST")
print("========================================")


# ============================================================
# TEST 1 — HIGH CPU
# ============================================================

result = create_remediation_proposal(
    server_id="server-002",
    server_name="Application Server",
    incident_type="High CPU utilization",
    severity="high",
    message="Application Server is running with high CPU utilization of 87.2%.",
)

print("\n--- HIGH CPU INCIDENT ---")

if result["success"]:

    proposal = result["proposal"]

    print("Action:", proposal["action"])
    print("Description:", proposal["action_description"])
    print("Reason:", proposal["reason"])
    print("Impact:", proposal["impact"])
    print("Approval:", proposal["approval_status"])
    print("Execution:", proposal["execution_status"])

    validation = validate_proposal(proposal)

    print("Policy validation:", validation["valid"])
    print("Validation reason:", validation["reason"])

else:
    print("❌ No proposal generated")


# ============================================================
# TEST 2 — SECURITY
# ============================================================

result = create_remediation_proposal(
    server_id="i-test123",
    server_name="Test EC2",
    incident_type="SSH exposed to internet",
    severity="critical",
    message="Security group allows Port 22 from 0.0.0.0/0.",
)

print("\n--- SECURITY INCIDENT ---")

if result["success"]:

    proposal = result["proposal"]

    print("Action:", proposal["action"])
    print("Description:", proposal["action_description"])
    print("Impact:", proposal["impact"])
    print("Approval:", proposal["approval_status"])
    print("Execution:", proposal["execution_status"])

    validation = validate_proposal(proposal)

    print("Policy validation:", validation["valid"])
    print("Validation reason:", validation["reason"])

else:
    print("❌ No proposal generated")


# ============================================================
# TEST 3 — UNKNOWN ACTION
# ============================================================

fake_proposal = {
    "action": "delete_everything",
    "approval_status": "pending_approval",
    "execution_status": "not_executed",
}

validation = validate_proposal(fake_proposal)

print("\n--- UNSAFE ACTION TEST ---")
print("Policy validation:", validation["valid"])
print("Validation reason:", validation["reason"])


print("\n========================================")
print("           TEST COMPLETE")
print("========================================")