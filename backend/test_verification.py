from backend.verification import verify_remediation


proposal = {
    "proposal_id": "proposal-test-123",
    "server_id": "server-002",
    "server_name": "Application Server",
    "action": "investigate_high_cpu",
    "execution_status": "simulated",
}


print("\n--- CPU IMPROVED ---")

result = verify_remediation(
    proposal=proposal,
    previous_cpu=87.2,
    current_cpu=65.0,
)

print(result)


print("\n--- CPU PARTIALLY IMPROVED ---")

result = verify_remediation(
    proposal=proposal,
    previous_cpu=87.2,
    current_cpu=82.0,
)

print(result)


print("\n--- CPU NOT IMPROVED ---")

result = verify_remediation(
    proposal=proposal,
    previous_cpu=87.2,
    current_cpu=90.0,
)

print(result)


print("\n--- NO CPU DATA ---")

result = verify_remediation(
    proposal=proposal,
    previous_cpu=87.2,
    current_cpu=None,
)

print(result)