from datetime import datetime, timezone
import uuid
from backend.remediation import create_remediation_proposal
from backend.approval import approve_proposal, reject_proposal
from backend.executor import execute_remediation
from backend.aws_cost import get_cost_summary
from backend.aws_security import get_security_summary
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.database import get_connection, initialize_database
from backend.aws_monitor import (

    get_ec2_instances,

    get_ec2_cpu_utilization,

    get_all_ec2_instances,

    get_instance_health,

)
from backend.agents.incident_agent import analyze_incident
from backend.verification import verify_remediation

# ============================================================

# APPLICATION

# ============================================================

app = FastAPI(

    title="CloudOps AI API",

    description=(

        "Cloud infrastructure monitoring and "

        "AI incident investigation"

    ),

    version="1.0.0",

)

# ============================================================

# CORS CONFIGURATION

# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================

# SIMULATED SERVER DATA

# ============================================================

SERVERS = [

    {

        "id": "server-001",

        "name": "Web Server",

        "status": "running",

        "cpu_usage": 35.5,

        "region": "ap-south-1",

    },

    {

        "id": "server-002",

        "name": "Application Server",

        "status": "running",

        "cpu_usage": 87.2,

        "region": "ap-south-1",

    },

    {

        "id": "server-003",

        "name": "Database Server",

        "status": "stopped",

        "cpu_usage": 0.0,

        "region": "ap-south-1",

    },

]

# ============================================================
# REMEDIATION PROPOSALS
# ============================================================

# Temporary in-memory store for active remediation proposals.
#
# PostgreSQL stores approval/rejection audit records.
# This store keeps the proposal available between API calls.
#
# Later, this can be replaced with full PostgreSQL
# proposal persistence.

REMEDIATION_PROPOSALS = {}

# ============================================================

# REQUEST MODELS

# ============================================================

class CPUUpdate(BaseModel):

    server_id: str

    cpu_usage: float = Field(ge=0, le=100)

class StatusUpdate(BaseModel):

    server_id: str

    status: str

class RemediationProposalRequest(BaseModel):
    server_id: str
    server_name: str
    incident_type: str
    severity: str
    message: str
    cpu_usage: float | None = None

class RemediationApprovalRequest(BaseModel):
    approver: str


class RemediationRejectionRequest(BaseModel):
    approver: str
    reason: str

# ============================================================

# SERVER HELPERS

# ============================================================

def find_server(server_id: str):

    for server in SERVERS:

        if server["id"] == server_id:

            return server

    return None

def detect_server_incident(server: dict):

    """Create an incident when a simulated server has a problem."""

    if server["status"].lower() == "stopped":

        return {

            "type": "Server stopped",

            "severity": "critical",

            "message": (

                f'{server["name"]} is stopped and may be unavailable.'

            ),

        }

    if server["cpu_usage"] >= 80:

        return {

            "type": "High CPU utilization",

            "severity": "high",

            "message": (

                f'{server["name"]} CPU usage is '

                f'{server["cpu_usage"]}%.'

            ),

        }

    if server["cpu_usage"] >= 60:

        return {

            "type": "Elevated CPU utilization",

            "severity": "medium",

            "message": (

                f'{server["name"]} CPU usage is '

                f'{server["cpu_usage"]}%.'

            ),

        }

    return None

def normalize_incident_type(incident: dict) -> str:

    """Convert incident names to consistent database identifiers."""

    raw_type = incident["type"].strip().upper()

    if "CPU" in raw_type:

        if incident["severity"] == "high":

            return "HIGH_CPU"

        return "MEDIUM_CPU"

    if "STOPPED" in raw_type:

        return "SERVER_STOPPED"

    return raw_type.replace(" ", "_")

# ============================================================

# INCIDENT HISTORY SYNCHRONIZATION

# ============================================================

def synchronize_incident_history():

    """

    Synchronize active simulated incidents with PostgreSQL.

    Existing unresolved incidents are reused instead of creating

    duplicate records on every API request.

    """

    now = datetime.now(timezone.utc)

    with get_connection() as connection:

        for server in SERVERS:

            incident = detect_server_incident(server)

            if incident:

                incident_type = normalize_incident_type(incident)

                incident["type"] = incident_type

                existing = connection.execute(

                    """

                    SELECT id

                    FROM incident_history

                    WHERE server_id = %s

                      AND resolved_at IS NULL

                      AND (

                          UPPER(REPLACE(type, ' ', '_')) = %s

                          OR (

                              type ILIKE '%%CPU%%'

                              AND %s IN ('HIGH_CPU', 'MEDIUM_CPU')

                          )

                          OR (

                              type ILIKE '%%STOPPED%%'

                              AND %s = 'SERVER_STOPPED'

                          )

                      )

                    ORDER BY detected_at DESC

                    LIMIT 1

                    """,

                    (

                        server["id"],

                        incident_type,

                        incident_type,

                        incident_type,

                    ),

                ).fetchone()

                if existing:

                    connection.execute(

                        """

                        UPDATE incident_history

                        SET

                            server_name = %s,

                            type = %s,

                            severity = %s,

                            message = %s

                        WHERE id = %s

                        """,

                        (

                            server["name"],

                            incident_type,

                            incident["severity"],

                            incident["message"],

                            existing[0],

                        ),

                    )

                    # Close any additional active duplicates.

                    connection.execute(

                        """

                        UPDATE incident_history

                        SET resolved_at = %s

                        WHERE server_id = %s

                          AND resolved_at IS NULL

                          AND id <> %s

                          AND (

                              UPPER(REPLACE(type, ' ', '_')) = %s

                              OR (

                                  type ILIKE '%%CPU%%'

                                  AND %s IN ('HIGH_CPU', 'MEDIUM_CPU')

                              )

                              OR (

                                  type ILIKE '%%STOPPED%%'

                                  AND %s = 'SERVER_STOPPED'

                              )

                          )

                        """,

                        (

                            now,

                            server["id"],

                            existing[0],

                            incident_type,

                            incident_type,

                            incident_type,

                        ),

                    )

                else:

                    incident_id = str(uuid.uuid4())

                    connection.execute(

                        """

                        INSERT INTO incident_history (

                            id,

                            server_id,

                            server_name,

                            type,

                            severity,

                            message,

                            detected_at,

                            resolved_at

                        )

                        VALUES (

                            %s,

                            %s,

                            %s,

                            %s,

                            %s,

                            %s,

                            %s,

                            NULL

                        )

                        """,

                        (

                            incident_id,

                            server["id"],

                            server["name"],

                            incident_type,

                            incident["severity"],

                            incident["message"],

                            now,

                        ),

                    )

            else:

                # Resolve active incidents when the server recovers.

                connection.execute(

                    """

                    UPDATE incident_history

                    SET resolved_at = %s

                    WHERE server_id = %s

                      AND resolved_at IS NULL

                    """,

                    (

                        now,

                        server["id"],

                    ),

                )

# ============================================================

# AWS INCIDENT HELPERS

# ============================================================

def build_aws_incident(instance: dict, health: dict):

    """

    Convert AWS health information into the same incident

    structure used by CloudOps AI.

    Returns None when no incident is detected.

    """

    health_info = health.get("health", {})

    health_status = health_info.get("health")

    severity = health_info.get("severity")

    if health_status == "stopped":

        return {

            "type": "AWS Server stopped",

            "severity": "critical",

            "message": (

                f'{instance["name"]} ({instance["id"]}) '

                "is stopped."

            ),

        }

    if health_status == "critical":

        return {

            "type": "AWS High CPU utilization",

            "severity": "high",

            "message": (

                f'{instance["name"]} ({instance["id"]}) '

                f'has high CPU utilization '

                f'({health_info.get("average_cpu")}%).'

            ),

        }

    if health_status == "warning":

        return {

            "type": "AWS Elevated CPU utilization",

            "severity": "medium",

            "message": (

                f'{instance["name"]} ({instance["id"]}) '

                f'has elevated CPU utilization '

                f'({health_info.get("average_cpu")}%).'

            ),

        }

    return None

def normalize_aws_incident_type(incident: dict) -> str:

    """Normalize AWS incident names for PostgreSQL."""

    raw_type = incident["type"].strip().upper()

    if "CPU" in raw_type:

        if incident["severity"] == "high":

            return "AWS_HIGH_CPU"

        return "AWS_MEDIUM_CPU"

    if "STOPPED" in raw_type:

        return "AWS_SERVER_STOPPED"

    return raw_type.replace(" ", "_")

def save_aws_incident(

    instance: dict,

    incident: dict,

):

    """

    Save an active AWS incident to incident_history.

    Existing unresolved incidents for the same instance and

    incident family are reused.

    """

    now = datetime.now(timezone.utc)

    server_id = instance["id"]

    server_name = instance["name"]

    incident_type = normalize_aws_incident_type(incident)

    with get_connection() as connection:

        existing = connection.execute(

            """

            SELECT id

            FROM incident_history

            WHERE server_id = %s

              AND resolved_at IS NULL

              AND type = %s

            ORDER BY detected_at DESC

            LIMIT 1

            """,

            (

                server_id,

                incident_type,

            ),

        ).fetchone()

        if existing:

            connection.execute(

                """

                UPDATE incident_history

                SET

                    server_name = %s,

                    severity = %s,

                    message = %s

                WHERE id = %s

                """,

                (

                    server_name,

                    incident["severity"],

                    incident["message"],

                    existing[0],

                ),

            )

            return existing[0]

        incident_id = str(uuid.uuid4())

        connection.execute(

            """

            INSERT INTO incident_history (

                id,

                server_id,

                server_name,

                type,

                severity,

                message,

                detected_at,

                resolved_at

            )

            VALUES (

                %s,

                %s,

                %s,

                %s,

                %s,

                %s,

                %s,

                NULL

            )

            """,

            (

                incident_id,

                server_id,

                server_name,

                incident_type,

                incident["severity"],

                incident["message"],

                now,

            ),

        )

        return incident_id

# ============================================================

# ACTIVE INCIDENTS

# ============================================================


def get_active_aws_incidents():
    """
    Collect active incidents from real AWS EC2 infrastructure.

    This function is read-only. It:
    - discovers EC2 instances across configured AWS regions
    - reads CloudWatch health/CPU information
    - saves detected AWS incidents to PostgreSQL
    - does not start, stop, terminate, or modify AWS resources
    """
    try:
        aws_result = get_all_ec2_instances()

        # A partial regional scan can still be useful. Only return an
        # empty result when no instances can be obtained at all.
        if not aws_result.get("success") and not aws_result.get("instances"):
            return {
                "success": False,
                "incidents": [],
                "total": 0,
                "error": "Unable to collect AWS EC2 instances",
                "scan_status": aws_result.get("scan_status", "failed"),
                "total_regions": aws_result.get("total_regions", 0),
                "successful_regions": aws_result.get("successful_regions", 0),
                "failed_regions": aws_result.get("failed_regions", 0),
                "total_instances": aws_result.get("total_instances", 0),
                "data_source": "aws",
            }

        incidents = []

        for instance in aws_result.get("instances", []):
            try:
                health = get_instance_health(instance)

                incident = build_aws_incident(
                    instance,
                    health,
                )

                if incident:
                    incident_id = save_aws_incident(
                        instance,
                        incident,
                    )

                    incidents.append(
                        {
                            "id": incident_id,
                            "server_id": instance["id"],
                            "server_name": instance["name"],
                            "region": instance.get("region"),
                            **incident,
                            "detected_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                            "data_source": "aws",
                        }
                    )

            except Exception as instance_error:
                print(
                    "AWS incident check failed for "
                    f"{instance.get('id', 'unknown')}: {instance_error}"
                )

        return {
            "success": True,
            "incidents": incidents,
            "total": len(incidents),
            "scan_status": aws_result.get("scan_status", "unknown"),
            "total_regions": aws_result.get("total_regions", 0),
            "successful_regions": aws_result.get("successful_regions", 0),
            "failed_regions": aws_result.get("failed_regions", 0),
            "total_instances": aws_result.get("total_instances", 0),
            "data_source": "aws",
        }

    except Exception as error:
        print(f"AWS incident collection failed: {error}")

        return {
            "success": False,
            "incidents": [],
            "total": 0,
            "error": str(error),
            "scan_status": "failed",
            "total_regions": 0,
            "successful_regions": 0,
            "failed_regions": 0,
            "total_instances": 0,
            "data_source": "aws",
        }

def collect_active_incidents():

    """Collect active incidents from simulated and real AWS infrastructure."""

    incidents = []

    for server in SERVERS:

        incident = detect_server_incident(server)

        if incident:

            incident_type = normalize_incident_type(incident)

            incidents.append({"id": f'{server["id"]}-{incident_type}', "server_id": server["id"], "server_name": server["name"], **incident, "type": incident_type, "detected_at": datetime.now(timezone.utc).isoformat(), "data_source": "simulated", "region": server.get("region")})

    aws_result = get_active_aws_incidents()

    incidents.extend(aws_result.get("incidents", []))

    return {"incidents": incidents, "aws": aws_result}

def get_active_incidents():

    """Return currently active incidents from all data sources."""

    return collect_active_incidents()["incidents"]

# STARTUP

# ============================================================

@app.on_event("startup")

def startup_event():

    initialize_database()

    synchronize_incident_history()

# ============================================================

# GENERAL ENDPOINTS

# ============================================================

@app.get("/")

def root():

    return {

        "message": "CloudOps AI API is running",

        "docs": "/docs",

    }

@app.get("/health")

def health_check():

    return {

        "status": "healthy",

        "service": "CloudOps AI",

    }

# ============================================================

# SIMULATED MONITORING

# ============================================================

@app.get("/api/monitoring")

def get_monitoring():

    return {

        "servers": SERVERS,

        "total_servers": len(SERVERS),

        "running_servers": sum(

            1

            for server in SERVERS

            if server["status"] == "running"

        ),

        "stopped_servers": sum(

            1

            for server in SERVERS

            if server["status"] == "stopped"

        ),

        "data_source": "simulated",

    }

@app.get("/api/incidents")

def get_incidents():

    synchronize_incident_history()

    return get_active_incidents()

@app.get("/api/incidents/history")

def get_incident_history():

    synchronize_incident_history()

    with get_connection() as connection:

        rows = connection.execute(

            """

            SELECT

                id,

                server_id,

                server_name,

                type,

                severity,

                message,

                detected_at,

                resolved_at,

                diagnosis,

                recommendation,

                investigated_at

            FROM incident_history

            ORDER BY detected_at DESC

            """

        ).fetchall()

    return [

        {

            "id": row[0],

            "server_id": row[1],

            "server_name": row[2],

            "type": row[3],

            "severity": row[4],

            "message": row[5],

            "detected_at": row[6].isoformat(),

            "resolved_at": (

                row[7].isoformat()

                if row[7]

                else None

            ),

            "diagnosis": row[8],

            "recommendation": row[9],

            "investigated_at": (

                row[10].isoformat()

                if row[10]

                else None

            ),

        }

        for row in rows

    ]

@app.get("/api/dashboard")
def get_dashboard():
    """
    Return a fast dashboard summary.

    AWS multi-region scans are intentionally handled by
    dedicated AWS endpoints instead of blocking the main dashboard.
    """

    synchronize_incident_history()

    running = sum(
        1
        for server in SERVERS
        if server["status"] == "running"
    )

    stopped = sum(
        1
        for server in SERVERS
        if server["status"] == "stopped"
    )

    simulated_incidents = []

    for server in SERVERS:
        incident = detect_server_incident(server)

        if incident:
            incident_type = normalize_incident_type(incident)

            simulated_incidents.append({
                "id": f'{server["id"]}-{incident_type}',
                "server_id": server["id"],
                "server_name": server["name"],
                **incident,
                "type": incident_type,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "data_source": "simulated",
                "region": server.get("region"),
            })

    return {
        "total_servers": len(SERVERS),
        "simulated_servers": len(SERVERS),

        "aws_instances": 0,

        "running_servers": running,
        "stopped_servers": stopped,

        "active_incidents": len(simulated_incidents),

        "critical_incidents": sum(
            1
            for incident in simulated_incidents
            if incident["severity"] == "critical"
        ),

        "high_incidents": sum(
            1
            for incident in simulated_incidents
            if incident["severity"] == "high"
        ),

        "medium_incidents": sum(
            1
            for incident in simulated_incidents
            if incident["severity"] == "medium"
        ),

        "average_cpu": round(
            sum(server["cpu_usage"] for server in SERVERS)
            / len(SERVERS),
            2,
        ),

        "aws_scan_status": "not_requested",
        "aws_total_regions": 0,
        "aws_successful_regions": 0,
        "aws_failed_regions": 0,
        "aws_active_incidents": 0,

        "data_source": "simulated",
    }
# AWS MONITORING

# ============================================================

@app.get("/api/aws/instances")

def get_aws_instances(

    region: str = "eu-central-1",

):

    result = get_ec2_instances(

        region=region

    )

    if not result.get("success"):

        raise HTTPException(

            status_code=502,

            detail={

                "message": (

                    "Unable to retrieve AWS "

                    "EC2 instances"

                ),

                "error": result.get("error"),

            },

        )

    return result

@app.get("/api/aws/instances/all")

def get_all_aws_instances():

    """

    Discover EC2 instances across all configured

    AWS regions.

    A partial scan is returned successfully if at least

    one region is available.

    """

    result = get_all_ec2_instances()

    if not result.get("success"):

        raise HTTPException(

            status_code=502,

            detail={

                "message": (

                    "Unable to retrieve AWS EC2 "

                    "instances from any region"

                ),

                "scan_status": result.get(

                    "scan_status"

                ),

                "regions": result.get(

                    "regions",

                    [],

                ),

            },

        )

    return result

@app.get("/api/aws/cpu/{instance_id}")

def get_aws_cpu(

    instance_id: str,

    region: str = "eu-central-1",

):

    if not instance_id.startswith("i-"):

        raise HTTPException(

            status_code=400,

            detail="Invalid EC2 instance ID",

        )

    result = get_ec2_cpu_utilization(

        instance_id=instance_id,

        region=region,

    )

    if not result.get("success"):

        raise HTTPException(

            status_code=502,

            detail={

                "message": (

                    "Unable to retrieve "

                    "CloudWatch CPU metrics"

                ),

                "error": result.get("error"),

            },

        )

    return result

# ============================================================

# AWS HEALTH

# ============================================================

@app.get("/api/aws/health")

def get_aws_health(

    region: str = "eu-central-1",

):

    """

    Retrieve EC2 instances and evaluate their health

    using CloudWatch CPU metrics.

    """

    inventory = get_ec2_instances(

        region=region

    )

    if not inventory.get("success"):

        raise HTTPException(

            status_code=502,

            detail={

                "message": (

                    "Unable to retrieve AWS "

                    "EC2 inventory"

                ),

                "error": inventory.get("error"),

            },

        )

    health_results = []

    detected_incidents = []

    for instance in inventory.get(

        "instances",

        [],

    ):

        health = get_instance_health(

            instance

        )

        health_results.append(health)

        incident = build_aws_incident(

            instance,

            health,

        )

        if incident:

            incident_id = save_aws_incident(

                instance,

                incident,

            )

            detected_incidents.append(

                {

                    "id": incident_id,

                    "server_id": instance["id"],

                    "server_name": instance["name"],

                    "region": instance["region"],

                    **incident,

                }

            )

    return {

        "success": True,

        "region": region,

        "total_instances": len(

            inventory.get(

                "instances",

                [],

            )

        ),

        "health_results": health_results,

        "detected_incidents": detected_incidents,

        "data_source": "aws",

    }

@app.get("/api/aws/health/all")

def get_all_aws_health():

    """

    Evaluate EC2 health across all available regions.

    Failed regions are recorded rather than stopping

    the entire scan.

    """

    inventory = get_all_ec2_instances()

    if not inventory.get("success"):

        raise HTTPException(

            status_code=502,

            detail={

                "message": (

                    "Unable to retrieve AWS "

                    "instances from any region"

                ),

                "scan_status": inventory.get(

                    "scan_status"

                ),

            },

        )

    health_results = []

    detected_incidents = []

    for instance in inventory.get(

        "instances",

        [],

    ):

        health = get_instance_health(

            instance

        )

        health_results.append(health)

        incident = build_aws_incident(

            instance,

            health,

        )

        if incident:

            incident_id = save_aws_incident(

                instance,

                incident,

            )

            detected_incidents.append(

                {

                    "id": incident_id,

                    "server_id": instance["id"],

                    "server_name": instance["name"],

                    "region": instance["region"],

                    **incident,

                }

            )

    return {

        "success": True,

        "scan_status": inventory.get(

            "scan_status"

        ),

        "total_regions": inventory.get(

            "total_regions"

        ),

        "successful_regions": inventory.get(

            "successful_regions"

        ),

        "failed_regions": inventory.get(

            "failed_regions"

        ),

        "total_instances": inventory.get(

            "total_instances"

        ),

        "health_results": health_results,

        "detected_incidents": detected_incidents,

        "regions": inventory.get(

            "regions",

            [],

        ),

        "data_source": "aws",

    }

# ============================================================

# AWS INCIDENTS

@app.get("/api/aws/incidents")

def get_aws_incidents():

    """Return currently detected AWS incidents and scan status."""

    try:

        result = get_active_aws_incidents()

        return {"success": True, "scan_status": result.get("scan_status", "unknown"), "total_regions": result.get("total_regions", 0), "successful_regions": result.get("successful_regions", 0), "failed_regions": result.get("failed_regions", 0), "total_instances": result.get("total_instances", 0), "incidents": result.get("incidents", []), "data_source": "aws"}

    except Exception as error:

        print(f"AWS incident detection failed: {error}")

        raise HTTPException(status_code=502, detail={"message": "Unable to detect AWS incidents", "error": str(error)}) from error

# AWS INCIDENT INVESTIGATION

# ============================================================

@app.get(

    "/api/aws/investigate/{instance_id}"

)

def investigate_aws_instance(

    instance_id: str,

    region: str = "eu-central-1",

):

    """

    Investigate an AWS EC2 instance through the

    existing multi-agent LangGraph workflow.

    """

    if not instance_id.startswith("i-"):

        raise HTTPException(

            status_code=400,

            detail="Invalid EC2 instance ID",

        )

    inventory = get_ec2_instances(

        region=region

    )

    if not inventory.get("success"):

        raise HTTPException(

            status_code=502,

            detail={

                "message": (

                    "Unable to retrieve AWS "

                    "EC2 instances"

                ),

                "error": inventory.get("error"),

            },

        )

    instance = next(

        (

            item

            for item in inventory.get(

                "instances",

                [],

            )

            if item["id"] == instance_id

        ),

        None,

    )

    if instance is None:

        raise HTTPException(

            status_code=404,

            detail="AWS EC2 instance not found",

        )

    try:

        health = get_instance_health(

            instance

        )

        average_cpu = (

            health["cpu"].get("average_cpu")

        )

        # If CloudWatch has no CPU data, use 0

        # but preserve the unknown monitoring state.

        cpu_for_agent = (

            average_cpu

            if average_cpu is not None

            else 0.0

        )

        result = analyze_incident(

            server_name=instance["name"],

            cpu_usage=cpu_for_agent,

            status=instance["status"],

        )

        incident = build_aws_incident(

            instance,

            health,

        )

        saved_to_database = False

        incident_id = None

        if incident:

            incident_id = save_aws_incident(

                instance,

                incident,

            )

            with get_connection() as connection:

                updated = connection.execute(

                    """

                    UPDATE incident_history

                    SET

                        diagnosis = %s,

                        recommendation = %s,

                        investigated_at = NOW()

                    WHERE id = %s

                    RETURNING id

                    """,

                    (

                        result.get(

                            "diagnosis",

                            "",

                        ),

                        result.get(

                            "recommendation",

                            "",

                        ),

                        incident_id,

                    ),

                ).fetchone()

            saved_to_database = (

                updated is not None

            )

        return {

            "instance": instance,

            "health": health,

            "investigation": result,

            "incident": incident,

            "incident_id": incident_id,

            "data_source": "aws",

            "agent_type": result.get(

                "agent_type",

                "unknown",

            ),

            "saved_to_database": saved_to_database,

        }

    except Exception as error:

        print(

            f"AWS incident investigation failed: "

            f"{error}"

        )

        raise HTTPException(

            status_code=500,

            detail=(

                "AWS incident investigation failed"

            ),

        ) from error

# ============================================================

# LANGGRAPH INCIDENT INVESTIGATION

# ============================================================

@app.get(

    "/api/ai/investigate/{server_id}"

)

def investigate_server(server_id: str):

    server = find_server(server_id)

    if server is None:

        raise HTTPException(

            status_code=404,

            detail="Server not found",

        )

    try:

        result = analyze_incident(

            server_name=server["name"],

            cpu_usage=server["cpu_usage"],

            status=server["status"],

        )

        with get_connection() as connection:

            updated = connection.execute(

                """

                UPDATE incident_history

                SET

                    diagnosis = %s,

                    recommendation = %s,

                    investigated_at = NOW()

                WHERE id = (

                    SELECT id

                    FROM incident_history

                    WHERE server_id = %s

                      AND resolved_at IS NULL

                    ORDER BY detected_at DESC

                    LIMIT 1

                )

                RETURNING id

                """,

                (

                    result.get(

                        "diagnosis",

                        "",

                    ),

                    result.get(

                        "recommendation",

                        "",

                    ),

                    server_id,

                ),

            ).fetchone()

        return {

            "server_id": server["id"],

            "server_name": server["name"],

            "investigation": result,

            "data_source": "simulated",

            "agent_type": result.get(

                "agent_type",

                "unknown",

            ),

            "saved_to_database": (

                updated is not None

            ),

        }

    except Exception as error:

        print(

            f"Incident investigation failed: "

            f"{error}"

        )

        raise HTTPException(

            status_code=500,

            detail="Incident investigation failed",

        ) from error

# ============================================================
# REMEDIATION WORKFLOW
# ============================================================


@app.post("/api/remediation/propose")
def create_remediation(request: RemediationProposalRequest):
    """
    Create a safe remediation proposal.

    This endpoint does NOT execute any infrastructure action.
    The proposal must pass the remediation rules before
    it can be submitted for human approval.
    """

    result = create_remediation_proposal(
        server_id=request.server_id,
        server_name=request.server_name,
        incident_type=request.incident_type,
        severity=request.severity,
        message=request.message,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "reason",
                "Unable to create remediation proposal.",
            ),
        )

    proposal = result["proposal"]
    proposal["cpu_usage"] = request.cpu_usage
    proposal_id = proposal["proposal_id"]

    REMEDIATION_PROPOSALS[proposal_id] = proposal

    return {
        "success": True,
        "proposal": proposal,
    }

@app.post("/api/remediation/{proposal_id}/verify")
def verify_remediation_action(
    proposal_id: str,
    current_cpu: float | None = None,
):
    proposal = REMEDIATION_PROPOSALS.get(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=404,
            detail="Remediation proposal not found.",
        )

    if current_cpu is None:
        current_cpu = proposal.get("current_cpu")

    previous_cpu = proposal.get("cpu_usage")

    result = verify_remediation(
        proposal=proposal,
        current_cpu=current_cpu,
        previous_cpu=previous_cpu,
    )

    proposal["verification_status"] = result["verification_status"]
    proposal["verification_result"] = result

    return {
        "success": result["success"],
        "proposal": proposal,
        "verification": result,
    }

@app.post("/api/remediation/{proposal_id}/approve")
def approve_remediation(
    proposal_id: str,
    request: RemediationApprovalRequest,
):
    """
    Approve a remediation proposal.

    IMPORTANT:
    Approval does NOT execute the action.
    Execution requires a separate API request.
    """

    proposal = REMEDIATION_PROPOSALS.get(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=404,
            detail="Remediation proposal not found.",
        )

    result = approve_proposal(
        proposal=proposal,
        approver=request.approver,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["reason"],
        )

    return {
        "success": True,
        "proposal": proposal,
        "approval": result,
    }


@app.post("/api/remediation/{proposal_id}/reject")
def reject_remediation(
    proposal_id: str,
    request: RemediationRejectionRequest,
):
    """
    Reject a remediation proposal.

    A rejected proposal cannot be executed.
    """

    proposal = REMEDIATION_PROPOSALS.get(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=404,
            detail="Remediation proposal not found.",
        )

    result = reject_proposal(
        proposal=proposal,
        approver=request.approver,
        reason=request.reason,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["reason"],
        )

    return {
        "success": True,
        "proposal": proposal,
        "rejection": result,
    }


@app.post("/api/remediation/{proposal_id}/execute")
def execute_remediation_action(
    proposal_id: str,
):
    """
    Execute an approved remediation proposal.

    Current executor is simulation-only.
    No AWS resources are modified.
    """

    proposal = REMEDIATION_PROPOSALS.get(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=404,
            detail="Remediation proposal not found.",
        )

    result = execute_remediation(proposal)

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["reason"],
        )

    return {
        "success": True,
        "proposal": proposal,
        "execution": result,
    }


@app.get("/api/remediation/history")
def remediation_history():
    """
    Return remediation approval/rejection history
    from PostgreSQL.
    """

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                id,
                proposal_id,
                server_id,
                server_name,
                action,
                incident_type,
                severity,
                approval_status,
                approver,
                rejection_reason,
                execution_status,
                created_at,
                decided_at
            FROM remediation_approvals
            ORDER BY id DESC
            """
        ).fetchall()

    history = []

    for row in rows:
        history.append(
            {
                "id": row[0],
                "proposal_id": row[1],
                "server_id": row[2],
                "server_name": row[3],
                "action": row[4],
                "incident_type": row[5],
                "severity": row[6],
                "approval_status": row[7],
                "approver": row[8],
                "rejection_reason": row[9],
                "execution_status": row[10],
                "created_at": (
                    row[11].isoformat()
                    if row[11]
                    else None
                ),
                "decided_at": (
                    row[12].isoformat()
                    if row[12]
                    else None
                ),
            }
        )

    return {
        "success": True,
        "count": len(history),
        "history": history,
    }
# ============================================================

# SIMULATION ENDPOINTS

# ============================================================

@app.get("/api/aws/cost")

def aws_cost():

    """

    Return AWS cost information from Cost Explorer.

    This endpoint is read-only.

    """

    return get_cost_summary()

@app.get("/api/aws/security")
def aws_security():
    """
    Return AWS security analysis.

    This endpoint is read-only.
    It does not modify AWS resources.
    """
    return get_security_summary()


@app.post("/api/simulation/cpu")

def simulate_cpu(update: CPUUpdate):

    server = find_server(

        update.server_id

    )

    if server is None:

        raise HTTPException(

            status_code=404,

            detail="Server not found",

        )

    server["cpu_usage"] = update.cpu_usage

    synchronize_incident_history()

    return {

        "message": "CPU utilization updated",

        "server": server,

        "incident": detect_server_incident(

            server

        ),

    }

@app.post("/api/simulation/status")

def simulate_status(update: StatusUpdate):

    server = find_server(

        update.server_id

    )

    if server is None:

        raise HTTPException(

            status_code=404,

            detail="Server not found",

        )

    allowed_statuses = {

        "running",

        "stopped",

    }

    if update.status.lower() not in allowed_statuses:

        raise HTTPException(

            status_code=400,

            detail=(

                "Status must be running or stopped"

            ),

        )

    server["status"] = update.status.lower()

    if server["status"] == "stopped":

        server["cpu_usage"] = 0.0

    synchronize_incident_history()

    return {

        "message": "Server status updated",

        "server": server,

        "incident": detect_server_incident(

            server

        ),

    }
