
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