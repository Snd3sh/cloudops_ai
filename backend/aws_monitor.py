
import boto3
from botocore.exceptions import BotoCoreError, ClientError


def get_ec2_instances(region="eu-central-1"):
    """Fetch EC2 instance information using read-only AWS APIs."""
    try:
        ec2 = boto3.client("ec2", region_name=region)
        response = ec2.describe_instances()

        instances = []

        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                name = next(
                    (
                        tag["Value"]
                        for tag in instance.get("Tags", [])
                        if tag["Key"] == "Name"
                    ),
                    instance["InstanceId"],
                )

                instances.append({
                    "id": instance["InstanceId"],
                    "name": name,
                    "status": instance["State"]["Name"],
                    "instance_type": instance["InstanceType"],
                    "region": region,
                })

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
            "error": str(error),
            "instances": [],
            "data_source": "aws",
        }


def get_ec2_cpu_utilization(instance_id, region="eu-central-1"):
    """Fetch recent CPU utilization for an EC2 instance from CloudWatch."""
    from datetime import datetime, timedelta, timezone

    try:
        cloudwatch = boto3.client("cloudwatch", region_name=region)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=30)

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
            Statistics=["Average", "Maximum"],
        )

        datapoints = sorted(
            response.get("Datapoints", []),
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
                "message": "No CPU metrics found for this instance in the last 30 minutes.",
            }

        return {
            "success": True,
            "instance_id": instance_id,
            "region": region,
            "average_cpu": round(
                sum(point["Average"] for point in datapoints)
                / len(datapoints),
                2,
            ),
            "maximum_cpu": round(
                max(point["Maximum"] for point in datapoints),
                2,
            ),
            "datapoints": [
                {
                    "timestamp": point["Timestamp"].isoformat(),
                    "average": round(point["Average"], 2),
                    "maximum": round(point["Maximum"], 2),
                }
                for point in datapoints
            ],
            "message": "CPU metrics retrieved successfully.",
        }

    except (BotoCoreError, ClientError) as error:
        return {
            "success": False,
            "instance_id": instance_id,
            "region": region,
            "error": str(error),
            "datapoints": [],
        }
