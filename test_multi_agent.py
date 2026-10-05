from backend.agents.incident_agent import analyze_incident


tests = [
    {
        "name": "HIGH CPU",
        "server_name": "Application Server",
        "cpu_usage": 87.2,
        "status": "running",
    },
    {
        "name": "MEDIUM CPU",
        "server_name": "Test Server",
        "cpu_usage": 65.0,
        "status": "running",
    },
    {
        "name": "SERVER STOPPED",
        "server_name": "Database Server",
        "cpu_usage": 0.0,
        "status": "stopped",
    },
    {
        "name": "NORMAL SERVER",
        "server_name": "Web Server",
        "cpu_usage": 35.5,
        "status": "running",
    },
]


for test in tests:
    print("\n" + "=" * 60)
    print(f"TEST: {test['name']}")
    print("=" * 60)

    result = analyze_incident(
        server_name=test["server_name"],
        cpu_usage=test["cpu_usage"],
        status=test["status"],
    )

    print(f"Server:         {test['server_name']}")
    print(f"CPU:            {test['cpu_usage']}%")
    print(f"Status:         {test['status']}")
    print(f"Incident:       {result['incident_type']}")
    print(f"Severity:       {result['severity']}")
    print(f"Agent:          {result['agent_type']}")
    print(f"Diagnosis:      {result['diagnosis']}")
    print(f"Recommendation: {result['recommendation']}")
