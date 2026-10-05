import boto3
from botocore.exceptions import BotoCoreError, ClientError


# AWS regions monitored by CloudOps AI.
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
# EC2 INVENTORY
# ============================================================

def _get_instance_name(instance):
    """Return the EC2 Name tag or fall back to the instance ID."""

    for tag in instance.get("Tags", []):
        if tag.get("Key") == "Name":
            return tag.get(
                "Value",
                instance["InstanceId"],
            )

    return instance["InstanceId"]


def _normalize_instance(instance, region):
    """
    Convert raw AWS EC2 data into the normalized format
    used by CloudOps AI.
    """

    state = instance.get("State", {})

    return {
        "id": instance["InstanceId"],
        "name": _get_instance_name(instance),
        "status": state.get("Name", "unknown"),
        "instance_type": instance.get(
            "InstanceType",
            "unknown",
        ),
        "region": region,
        "availability_zone": (
            instance.get("Placement", {})
            .get("AvailabilityZone")
        ),
        "private_ip": instance.get(
            "PrivateIpAddress"
        ),
        "public_ip": instance.get(
            "PublicIpAddress"
        ),
    }


def get_ec2_instances(region="eu-central-1"):
    """
    Fetch EC2 instances using read-only AWS APIs.
    """

    try:
        ec2 = boto3.client(
            "ec2",
            region_name=region,
        )

        instances = []

        paginator = ec2.get_paginator(
            "describe_instances"
        )

        for page in paginator.paginate():
            for reservation in page.get(
                "Reservations",
                [],
            ):
                for instance in reservation.get(
                    "Instances",
                    [],
                ):
                    instances.append(
                        _normalize_instance(
                            instance,
                            region,
                        )
                    )

        return {
            "success": True,
            "region": region,
            "total_instances": len(instances),
            "instances": instances,
            "data_source": "aws",
        }

    except (BotoCoreError, ClientError) as error:
        return {
            "success": False,
            "region": region,
            "total_instances": 0,
            "error": str(error),
            "instances": [],
            "data_source": "aws",
        }


def get_all_ec2_instances():
    """
    Discover EC2 instances across all configured regions.

    A failure in one region does not stop monitoring
    the remaining regions.
    """

    all_instances = []
    region_results = []

    successful_regions = 0
    failed_regions = 0

    for region in AWS_REGIONS:
        result = get_ec2_instances(region)

        region_results.append(result)

        if result["success"]:
            successful_regions += 1
            all_instances.extend(
                result["instances"]
            )
        else:
            failed_regions += 1

    if failed_regions == 0:
        scan_status = "healthy"
    elif successful_regions > 0:
        scan_status = "partial"
    else:
        scan_status = "failed"

    return {
        "success": successful_regions > 0,
        "scan_status": scan_status,
        "total_instances": len(all_instances),
        "total_regions": len(AWS_REGIONS),
        "successful_regions": successful_regions,
        "failed_regions": failed_regions,
        "instances": all_instances,
        "regions": region_results,
        "data_source": "aws",
    }


# ============================================================
# CLOUDWATCH CPU
# ============================================================

def get_ec2_cpu_utilization(
    instance_id,
    region="eu-central-1",
):
    """
    Fetch recent CPU utilization for an EC2 instance
    from CloudWatch.
    """

    from datetime import datetime, timedelta, timezone

    try:
        cloudwatch = boto3.client(
            "cloudwatch",
            region_name=region,
        )

        end_time = datetime.now(timezone.utc)

        start_time = (
            end_time
            - timedelta(minutes=30)
        )

        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[
                {
                    "Name": "InstanceId",
                    "Value": instance_id,
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=[
                "Average",
                "Maximum",
            ],
        )

        datapoints = sorted(
            response.get(
                "Datapoints",
                [],
            ),
            key=lambda point: point["Timestamp"],
        )

        if not datapoints:
            return {
                "success": True,
                "instance_id": instance_id,
                "region": region,
                "average_cpu": None,
                "maximum_cpu": None,
                "datapoints": [],
                "message": (
                    "No CPU metrics found for this "
                    "instance in the last 30 minutes."
                ),
            }

        average_cpu = (
            sum(
                point["Average"]
                for point in datapoints
            )
            / len(datapoints)
        )

        maximum_cpu = max(
            point["Maximum"]
            for point in datapoints
        )

        return {
            "success": True,
            "instance_id": instance_id,
            "region": region,
            "average_cpu": round(
                average_cpu,
                2,
            ),
            "maximum_cpu": round(
                maximum_cpu,
                2,
            ),
            "datapoints": [
                {
                    "timestamp": (
                        point["Timestamp"]
                        .isoformat()
                    ),
                    "average": round(
                        point["Average"],
                        2,
                    ),
                    "maximum": round(
                        point["Maximum"],
                        2,
                    ),
                }
                for point in datapoints
            ],
            "message": (
                "CPU metrics retrieved successfully."
            ),
        }

    except (BotoCoreError, ClientError) as error:
        return {
            "success": False,
            "instance_id": instance_id,
            "region": region,
            "error": str(error),
            "average_cpu": None,
            "maximum_cpu": None,
            "datapoints": [],
        }


# ============================================================
# HEALTH EVALUATION
# ============================================================

def evaluate_instance_health(
    instance,
    cpu_data,
):
    """
    Convert EC2 state and CloudWatch CPU information
    into a normalized CloudOps AI health status.

    Health levels:

    healthy  -> CPU below 60%
    warning  -> CPU from 60% to below 80%
    critical -> CPU 80% or higher
    stopped  -> EC2 instance is stopped
    unknown  -> insufficient monitoring data
    """

    status = (
        instance.get("status", "unknown")
        .lower()
    )

    average_cpu = cpu_data.get(
        "average_cpu"
    )

    maximum_cpu = cpu_data.get(
        "maximum_cpu"
    )

    # --------------------------------------------------------
    # STOPPED INSTANCE
    # --------------------------------------------------------

    if status in {
        "stopped",
        "stopping",
    }:
        return {
            "health": "stopped",
            "severity": "critical",
            "reason": (
                "The EC2 instance is not running."
            ),
            "average_cpu": average_cpu,
            "maximum_cpu": maximum_cpu,
        }

    # --------------------------------------------------------
    # NO CPU DATA
    # --------------------------------------------------------

    if average_cpu is None:
        return {
            "health": "unknown",
            "severity": "unknown",
            "reason": (
                "No recent CloudWatch CPU metrics "
                "are available."
            ),
            "average_cpu": None,
            "maximum_cpu": maximum_cpu,
        }

    # --------------------------------------------------------
    # CRITICAL CPU
    # --------------------------------------------------------

    if average_cpu >= 80:
        return {
            "health": "critical",
            "severity": "high",
            "reason": (
                f"Average CPU utilization is "
                f"{average_cpu}%."
            ),
            "average_cpu": average_cpu,
            "maximum_cpu": maximum_cpu,
        }

    # --------------------------------------------------------
    # WARNING CPU
    # --------------------------------------------------------

    if average_cpu >= 60:
        return {
            "health": "warning",
            "severity": "medium",
            "reason": (
                f"Average CPU utilization is "
                f"{average_cpu}%."
            ),
            "average_cpu": average_cpu,
            "maximum_cpu": maximum_cpu,
        }

    # --------------------------------------------------------
    # HEALTHY
    # --------------------------------------------------------

    return {
        "health": "healthy",
        "severity": "low",
        "reason": (
            f"Average CPU utilization is "
            f"{average_cpu}%."
        ),
        "average_cpu": average_cpu,
        "maximum_cpu": maximum_cpu,
    }


# ============================================================
# COMPLETE INSTANCE HEALTH CHECK
# ============================================================

def get_instance_health(
    instance,
):
    """
    Retrieve CloudWatch CPU metrics and evaluate
    the overall health of an EC2 instance.
    """

    instance_id = instance["id"]
    region = instance["region"]

    cpu_data = get_ec2_cpu_utilization(
        instance_id,
        region,
    )

    health = evaluate_instance_health(
        instance,
        cpu_data,
    )

    return {
        "instance": instance,
        "cpu": cpu_data,
        "health": health,
        "data_source": "aws",
    }