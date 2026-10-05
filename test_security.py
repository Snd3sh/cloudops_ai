from backend.aws_security import analyze_security_group


test_cases = [
    {
        "name": "SSH exposed to internet",
        "group": {
            "GroupId": "sg-test-ssh",
            "GroupName": "ssh-public",
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [
                        {"CidrIp": "0.0.0.0/0"}
                    ],
                    "Ipv6Ranges": []
                }
            ]
        }
    },

    {
        "name": "RDP exposed to internet",
        "group": {
            "GroupId": "sg-test-rdp",
            "GroupName": "rdp-public",
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 3389,
                    "ToPort": 3389,
                    "IpRanges": [
                        {"CidrIp": "0.0.0.0/0"}
                    ],
                    "Ipv6Ranges": []
                }
            ]
        }
    },

    {
        "name": "All traffic exposed to internet",
        "group": {
            "GroupId": "sg-test-all",
            "GroupName": "all-public",
            "IpPermissions": [
                {
                    "IpProtocol": "-1",
                    "IpRanges": [
                        {"CidrIp": "0.0.0.0/0"}
                    ],
                    "Ipv6Ranges": []
                }
            ]
        }
    },

    {
        "name": "IPv6 unrestricted access",
        "group": {
            "GroupId": "sg-test-ipv6",
            "GroupName": "ipv6-public",
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 8080,
                    "ToPort": 8080,
                    "IpRanges": [],
                    "Ipv6Ranges": [
                        {"CidrIpv6": "::/0"}
                    ]
                }
            ]
        }
    },

    {
        "name": "Secure private access",
        "group": {
            "GroupId": "sg-test-safe",
            "GroupName": "private-only",
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [
                        {"CidrIp": "10.0.0.0/16"}
                    ],
                    "Ipv6Ranges": []
                }
            ]
        }
    }
]


print("\n========================================")
print("       CLOUDOPS AI SECURITY TEST")
print("========================================")


for test in test_cases:

    print(f"\n--- {test['name']} ---")

    findings = analyze_security_group(
        test["group"]
    )

    if not findings:
        print("✅ No security findings")
        continue

    for finding in findings:

        print(f"Type:       {finding['type']}")
        print(f"Severity:   {finding['severity']}")
        print(f"Source:     {finding['source']}")
        print(f"Ports:      {finding['ports']}")
        print(f"Message:    {finding['message']}")
        print(
            f"Recommendation: "
            f"{finding['recommendation']}"
        )


print("\n========================================")
print("             TEST COMPLETE")
print("========================================")