"""
aws_security.py

Read-only AWS security analysis for CloudOps AI.

Checks:
- EC2 public IP exposure
- Security group inbound rules
- SSH exposed to the internet
- RDP exposed to the internet
- unrestricted IPv4 access
- unrestricted IPv6 access

No AWS resources are modified.
"""

from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


# ============================================================
# CONFIGURATION
# ============================================================

AWS_PROFILE = "default"

AWS_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "ca-central-1",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "eu-central-1",
    "eu-north-1",
    "eu-south-1",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-northeast-3",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-south-1",
]


# ============================================================
# AWS CLIENT
# ============================================================

def get_ec2_client(region: str):
    """
    Create a read-only EC2 client for the selected region.
    """
    session = boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=region,
    )

    return session.client("ec2")


# ============================================================
# HELPERS
# ============================================================

def get_instance_name(instance: dict[str, Any]) -> str:
    """
    Get the Name tag from an EC2 instance.
    """
    for tag in instance.get("Tags", []):
        if tag.get("Key") == "Name":
            return tag.get("Value", instance.get("InstanceId", "Unknown"))

    return instance.get("InstanceId", "Unknown")


def port_description(
    from_port: int | None,
    to_port: int | None,
    protocol: str,
) -> str:
    """
    Convert a security group rule into a readable port description.
    """

    if protocol == "-1":
        return "All traffic"

    if from_port is None or to_port is None:
        return protocol

    if from_port == to_port:
        return f"Port {from_port}"

    return f"Ports {from_port}-{to_port}"


def determine_severity(
    *,
    unrestricted: bool,
    sensitive_port: bool,
    public_ip: bool,
) -> str:
    """
    Determine the security finding severity.
    """

    if unrestricted and sensitive_port:
        return "critical"

    if unrestricted:
        return "high"

    if sensitive_port and public_ip:
        return "high"

    if sensitive_port:
        return "medium"

    if public_ip:
        return "low"

    return "low"


# ============================================================
# SECURITY GROUP ANALYSIS
# ============================================================

def analyze_security_group(
    security_group: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Analyze inbound rules in a security group.

    This function only reads security group information.
    """

    findings = []

    group_id = security_group.get("GroupId", "unknown")
    group_name = security_group.get("GroupName", "unknown")

    for permission in security_group.get("IpPermissions", []):
        protocol = permission.get("IpProtocol", "-1")

        from_port = permission.get("FromPort")
        to_port = permission.get("ToPort")

        description = port_description(
            from_port,
            to_port,
            protocol,
        )

        sensitive_port = (
            from_port in {22, 3389}
            or to_port in {22, 3389}
        )

        # ----------------------------------------------------
        # IPv4 rules
        # ----------------------------------------------------

        for ip_range in permission.get("IpRanges", []):
            cidr = ip_range.get("CidrIp")

            if cidr != "0.0.0.0/0":
                continue

            finding_type = (
                "SSH exposed to internet"
                if from_port == 22 and to_port == 22
                else "RDP exposed to internet"
                if from_port == 3389 and to_port == 3389
                else "Unrestricted inbound access"
            )

            severity = determine_severity(
                unrestricted=True,
                sensitive_port=sensitive_port,
                public_ip=False,
            )

            findings.append(
                {
                    "type": finding_type,
                    "severity": severity,
                    "security_group_id": group_id,
                    "security_group_name": group_name,
                    "protocol": protocol,
                    "ports": description,
                    "source": cidr,
                    "message": (
                        f"{group_name} ({group_id}) allows "
                        f"{description} from {cidr}."
                    ),
                    "recommendation": (
                        "Restrict inbound access to trusted "
                        "IP addresses or private network ranges."
                    ),
                }
            )

        # ----------------------------------------------------
        # IPv6 rules
        # ----------------------------------------------------

        for ipv6_range in permission.get("Ipv6Ranges", []):
            cidr = ipv6_range.get("CidrIpv6")

            if cidr != "::/0":
                continue

            severity = determine_severity(
                unrestricted=True,
                sensitive_port=sensitive_port,
                public_ip=False,
            )

            findings.append(
                {
                    "type": "Unrestricted IPv6 inbound access",
                    "severity": severity,
                    "security_group_id": group_id,
                    "security_group_name": group_name,
                    "protocol": protocol,
                    "ports": description,
                    "source": cidr,
                    "message": (
                        f"{group_name} ({group_id}) allows "
                        f"{description} from all IPv6 addresses."
                    ),
                    "recommendation": (
                        "Restrict IPv6 inbound access to trusted "
                        "networks and remove unnecessary ::/0 rules."
                    ),
                }
            )

    return findings


# ============================================================
# REGION SECURITY SCAN
# ============================================================

def scan_region(region: str) -> dict[str, Any]:
    """
    Scan EC2 instances and security groups in one AWS region.

    Returns findings without modifying AWS resources.
    """

    try:
        ec2 = get_ec2_client(region)

        instances: list[dict[str, Any]] = []
        security_groups: dict[str, dict[str, Any]] = {}

        # ----------------------------------------------------
        # EC2 inventory
        # ----------------------------------------------------

        paginator = ec2.get_paginator("describe_instances")

        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instances.append(instance)

                    for group in instance.get(
                        "SecurityGroups",
                        [],
                    ):
                        group_id = group.get("GroupId")

                        if group_id:
                            security_groups[group_id] = group

        # ----------------------------------------------------
        # Retrieve complete security group rules
        # ----------------------------------------------------

        if security_groups:
            group_ids = list(security_groups.keys())

            response = ec2.describe_security_groups(
                GroupIds=group_ids,
            )

            security_groups = {
                group["GroupId"]: group
                for group in response.get(
                    "SecurityGroups",
                    [],
                )
            }

        # ----------------------------------------------------
        # Analyze security groups
        # ----------------------------------------------------

        group_findings: dict[str, list[dict[str, Any]]] = {}

        for group_id, group in security_groups.items():
            group_findings[group_id] = analyze_security_group(
                group
            )

        # ----------------------------------------------------
        # Analyze instances
        # ----------------------------------------------------

        instance_results = []
        total_findings = 0

        for instance in instances:
            instance_id = instance.get(
                "InstanceId",
                "unknown",
            )

            instance_name = get_instance_name(instance)

            state = instance.get(
                "State",
                {},
            ).get(
                "Name",
                "unknown",
            )

            public_ip = instance.get("PublicIpAddress")

            security_group_ids = [
                group.get("GroupId")
                for group in instance.get(
                    "SecurityGroups",
                    [],
                )
                if group.get("GroupId")
            ]

            findings = []

            for group_id in security_group_ids:
                findings.extend(
                    group_findings.get(group_id, [])
                )

            # ------------------------------------------------
            # Public IP finding
            # ------------------------------------------------

            if public_ip:
                findings.append(
                    {
                        "type": "Public IP exposure",
                        "severity": "low",
                        "security_group_id": None,
                        "security_group_name": None,
                        "protocol": None,
                        "ports": None,
                        "source": public_ip,
                        "message": (
                            f"{instance_name} ({instance_id}) "
                            f"has public IP address {public_ip}."
                        ),
                        "recommendation": (
                            "Use private networking where possible "
                            "and expose services through controlled "
                            "networking layers such as load balancers."
                        ),
                    }
                )

            total_findings += len(findings)

            highest_severity = "secure"

            severity_order = {
                "critical": 4,
                "high": 3,
                "medium": 2,
                "low": 1,
                "secure": 0,
            }

            for finding in findings:
                if (
                    severity_order[finding["severity"]]
                    > severity_order[highest_severity]
                ):
                    highest_severity = finding["severity"]

            instance_results.append(
                {
                    "instance_id": instance_id,
                    "instance_name": instance_name,
                    "state": state,
                    "public_ip": public_ip,
                    "security_group_ids": security_group_ids,
                    "security_status": highest_severity,
                    "findings": findings,
                    "finding_count": len(findings),
                    "region": region,
                }
            )

        return {
            "success": True,
            "region": region,
            "instances": instance_results,
            "total_instances": len(instances),
            "total_findings": total_findings,
            "data_source": "aws",
        }

    except (ClientError, BotoCoreError) as error:
        return {
            "success": False,
            "region": region,
            "instances": [],
            "total_instances": 0,
            "total_findings": 0,
            "error": str(error),
            "data_source": "aws",
        }

    except Exception as error:
        return {
            "success": False,
            "region": region,
            "instances": [],
            "total_instances": 0,
            "total_findings": 0,
            "error": str(error),
            "data_source": "aws",
        }


# ============================================================
# ALL REGIONS
# ============================================================

def scan_all_regions() -> dict[str, Any]:
    """
    Perform a read-only security scan across all configured
    AWS regions.
    """

    all_instances = []
    regions = []

    successful_regions = 0
    failed_regions = 0

    errors = []

    for region in AWS_REGIONS:
        result = scan_region(region)

        regions.append(
            {
                "region": region,
                "success": result.get("success", False),
                "instances": result.get(
                    "total_instances",
                    0,
                ),
                "findings": result.get(
                    "total_findings",
                    0,
                ),
                "error": result.get("error"),
            }
        )

        if result.get("success"):
            successful_regions += 1
            all_instances.extend(
                result.get("instances", [])
            )
        else:
            failed_regions += 1

            if result.get("error"):
                errors.append(
                    {
                        "region": region,
                        "error": result["error"],
                    }
                )

    total_findings = sum(
        instance.get("finding_count", 0)
        for instance in all_instances
    )

    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for instance in all_instances:
        for finding in instance.get("findings", []):
            severity = finding.get("severity")

            if severity in severity_counts:
                severity_counts[severity] += 1

    if failed_regions == 0:
        scan_status = "healthy"
    elif successful_regions > 0:
        scan_status = "partial"
    else:
        scan_status = "failed"

    return {
        "success": successful_regions > 0,
        "scan_status": scan_status,
        "total_regions": len(AWS_REGIONS),
        "successful_regions": successful_regions,
        "failed_regions": failed_regions,
        "total_instances": len(all_instances),
        "total_findings": total_findings,
        "severity_counts": severity_counts,
        "instances": all_instances,
        "regions": regions,
        "errors": errors,
        "data_source": "aws",
        "read_only": True,
    }


# ============================================================
# SUMMARY
# ============================================================

def get_security_summary() -> dict[str, Any]:
    """
    Return a compact security summary.
    """

    result = scan_all_regions()

    severity_counts = result.get(
        "severity_counts",
        {},
    )

    if severity_counts.get("critical", 0) > 0:
        overall_status = "critical"
    elif severity_counts.get("high", 0) > 0:
        overall_status = "high"
    elif severity_counts.get("medium", 0) > 0:
        overall_status = "medium"
    elif severity_counts.get("low", 0) > 0:
        overall_status = "low"
    else:
        overall_status = "secure"

    return {
        **result,
        "overall_status": overall_status,
    }