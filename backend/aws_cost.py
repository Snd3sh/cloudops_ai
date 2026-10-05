"""
aws_cost.py

AWS Cost Explorer integration for CloudOps AI.

This module is READ-ONLY.
It retrieves AWS billing/cost information and does not
create, modify, or delete AWS resources.
"""

from datetime import date, timedelta
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


# Cost Explorer is accessed through the us-east-1 endpoint.
COST_EXPLORER_REGION = "us-east-1"

# The AWS profile used by CloudOps AI.
AWS_PROFILE = "default"


def get_cost_explorer_client():
    """
    Create an AWS Cost Explorer client.

    Cost Explorer uses the us-east-1 endpoint.
    """

    session = boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=COST_EXPLORER_REGION,
    )

    return session.client("ce")


def get_date_range(days: int = 30) -> tuple[str, str]:
    """
    Return a date range suitable for Cost Explorer.

    AWS Cost Explorer uses:
        Start = inclusive
        End   = exclusive

    Example:
        2026-09-01 -> 2026-10-01
    """

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    return start_date.isoformat(), end_date.isoformat()


def get_total_cost(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Retrieve the total AWS cost for a date range.

    Returns a normalized response that the FastAPI backend
    can send directly to the frontend.
    """

    if start_date is None or end_date is None:
        start_date, end_date = get_date_range(30)

    try:
        client = get_cost_explorer_client()

        response = client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date,
                "End": end_date,
            },
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )

        results = response.get("ResultsByTime", [])

        total_cost = 0.0

        daily_costs = []

        for result in results:
            amount = float(
                result.get("Total", {})
                .get("UnblendedCost", {})
                .get("Amount", 0)
            )

            total_cost += amount

            daily_costs.append(
                {
                    "date": result.get("TimePeriod", {}).get("Start"),
                    "cost": round(amount, 4),
                }
            )

        return {
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "total_cost": round(total_cost, 2),
            "daily_costs": daily_costs,
            "data_source": "aws-cost-explorer",
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get(
            "Code",
            "Unknown",
        )

        error_message = error.response.get("Error", {}).get(
            "Message",
            str(error),
        )

        return {
            "success": False,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "total_cost": 0.0,
            "daily_costs": [],
            "data_source": "aws-cost-explorer",
            "error_code": error_code,
            "error": error_message,
        }

    except (BotoCoreError, Exception) as error:
        return {
            "success": False,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "total_cost": 0.0,
            "daily_costs": [],
            "data_source": "aws-cost-explorer",
            "error": str(error),
        }


def get_cost_by_service(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Retrieve AWS cost grouped by service.

    Example:

        EC2       $12.50
        S3        $ 3.20
        RDS       $ 7.10
    """

    if start_date is None or end_date is None:
        start_date, end_date = get_date_range(30)

    try:
        client = get_cost_explorer_client()

        response = client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date,
                "End": end_date,
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SERVICE",
                }
            ],
        )

        results = response.get("ResultsByTime", [])

        services = []

        for result in results:
            groups = result.get("Groups", [])

            for group in groups:
                keys = group.get("Keys", [])

                if not keys:
                    continue

                service_name = keys[0]

                amount = float(
                    group.get("Metrics", {})
                    .get("UnblendedCost", {})
                    .get("Amount", 0)
                )

                services.append(
                    {
                        "service": service_name,
                        "cost": round(amount, 2),
                    }
                )

        services.sort(
            key=lambda item: item["cost"],
            reverse=True,
        )

        total_cost = round(
            sum(item["cost"] for item in services),
            2,
        )

        return {
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "total_cost": total_cost,
            "services": services,
            "data_source": "aws-cost-explorer",
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get(
            "Code",
            "Unknown",
        )

        error_message = error.response.get("Error", {}).get(
            "Message",
            str(error),
        )

        return {
            "success": False,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "total_cost": 0.0,
            "services": [],
            "data_source": "aws-cost-explorer",
            "error_code": error_code,
            "error": error_message,
        }

    except (BotoCoreError, Exception) as error:
        return {
            "success": False,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "total_cost": 0.0,
            "services": [],
            "data_source": "aws-cost-explorer",
            "error": str(error),
        }


def get_cost_by_region(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Retrieve AWS cost grouped by AWS region.
    """

    if start_date is None or end_date is None:
        start_date, end_date = get_date_range(30)

    try:
        client = get_cost_explorer_client()

        response = client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date,
                "End": end_date,
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "REGION",
                }
            ],
        )

        results = response.get("ResultsByTime", [])

        regions = []

        for result in results:
            groups = result.get("Groups", [])

            for group in groups:
                keys = group.get("Keys", [])

                if not keys:
                    continue

                region_name = keys[0]

                amount = float(
                    group.get("Metrics", {})
                    .get("UnblendedCost", {})
                    .get("Amount", 0)
                )

                regions.append(
                    {
                        "region": region_name,
                        "cost": round(amount, 2),
                    }
                )

        regions.sort(
            key=lambda item: item["cost"],
            reverse=True,
        )

        return {
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "regions": regions,
            "data_source": "aws-cost-explorer",
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get(
            "Code",
            "Unknown",
        )

        error_message = error.response.get("Error", {}).get(
            "Message",
            str(error),
        )

        return {
            "success": False,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "regions": [],
            "data_source": "aws-cost-explorer",
            "error_code": error_code,
            "error": error_message,
        }

    except (BotoCoreError, Exception) as error:
        return {
            "success": False,
            "start_date": start_date,
            "end_date": end_date,
            "currency": "USD",
            "regions": [],
            "data_source": "aws-cost-explorer",
            "error": str(error),
        }


def get_cost_summary(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Return a combined cost summary.

    This will eventually be used by the CloudOps AI dashboard.
    """

    total = get_total_cost(
        start_date=start_date,
        end_date=end_date,
    )

    services = get_cost_by_service(
        start_date=start_date,
        end_date=end_date,
    )

    regions = get_cost_by_region(
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "success": (
            total["success"]
            and services["success"]
            and regions["success"]
        ),
        "start_date": total["start_date"],
        "end_date": total["end_date"],
        "currency": "USD",
        "total_cost": total["total_cost"],
        "daily_costs": total["daily_costs"],
        "services": services["services"],
        "regions": regions["regions"],
        "data_source": "aws-cost-explorer",
        "errors": [
            result["error"]
            for result in [total, services, regions]
            if not result["success"] and result.get("error")
        ],
    }