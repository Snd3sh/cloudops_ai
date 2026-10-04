from datetime import datetime, timezone
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import get_connection, initialize_database
from backend.aws_monitor import (
    get_ec2_instances,
    get_ec2_cpu_utilization,
)
from backend.agents.incident_agent import analyze_incident


app = FastAPI(
    title="CloudOps AI API",
    description="Cloud infrastructure monitoring and AI incident investigation",
    version="1.0.0",
)

# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# SIMULATED SERVER DATA
# --------------------------------------------------

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

# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------


class CPUUpdate(BaseModel):
    server_id: str
    cpu_usage: float = Field(ge=0, le=100)


class StatusUpdate(BaseModel):
    server_id: str
    status: str


# --------------------------------------------------
# SERVER HELPERS
# --------------------------------------------------


def find_server(server_id: str):
    for server in SERVERS:
        if server["id"] == server_id:
            return server
    return None


def detect_server_incident(server: dict):
    """Create an incident when a server has a problem."""

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


# --------------------------------------------------
# INCIDENT HISTORY SYNCHRONIZATION
# --------------------------------------------------


def synchronize_incident_history():
    """
    Synchronize active incidents with PostgreSQL.

    Reuse an existing unresolved incident of the same server and
    incident family. Create a new record only when none exists.
    Preserve resolved incident history and investigation details.
    """

    now = datetime.now(timezone.utc)

    with get_connection() as connection:
        for server in SERVERS:
            incident = detect_server_incident(server)

            if incident:
                incident_type = normalize_incident_type(incident)
                incident["type"] = incident_type

                # Find an existing unresolved incident in the same family.
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
                    # Refresh the existing active incident without
                    # overwriting its diagnosis or recommendation.
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

                    # Close any additional active records in this family.
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
                    # Create a distinct historical record for this
                    # occurrence instead of reopening an old incident.
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
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
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
                # Resolve active incidents when the server has recovered.
                connection.execute(
                    """
                    UPDATE incident_history
                    SET resolved_at = %s
                    WHERE server_id = %s
                      AND resolved_at IS NULL
                    """,
                    (now, server["id"]),
                )


# --------------------------------------------------
# ACTIVE INCIDENTS
# --------------------------------------------------


def get_active_incidents():
    """Return currently active incidents from simulated servers."""

    incidents = []

    for server in SERVERS:
        incident = detect_server_incident(server)

        if incident:
            incident_type = normalize_incident_type(incident)

            incidents.append(
                {
                    "id": f'{server["id"]}-{incident_type}',
                    "server_id": server["id"],
                    "server_name": server["name"],
                    **incident,
                    "type": incident_type,
                    "detected_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
            )

    return incidents


# --------------------------------------------------
# STARTUP
# --------------------------------------------------


@app.on_event("startup")
def startup_event():
    initialize_database()
    synchronize_incident_history()


# --------------------------------------------------
# GENERAL ENDPOINTS
# --------------------------------------------------


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


# --------------------------------------------------
# SIMULATED MONITORING
# --------------------------------------------------


@app.get("/api/monitoring")
def get_monitoring():
    return {
        "servers": SERVERS,
        "total_servers": len(SERVERS),
        "running_servers": sum(
            1 for server in SERVERS
            if server["status"] == "running"
        ),
        "stopped_servers": sum(
            1 for server in SERVERS
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
                row[7].isoformat() if row[7] else None
            ),
            "diagnosis": row[8],
            "recommendation": row[9],
            "investigated_at": (
                row[10].isoformat() if row[10] else None
            ),
        }
        for row in rows
    ]


@app.get("/api/dashboard")
def get_dashboard():
    synchronize_incident_history()

    running = sum(
        1 for server in SERVERS
        if server["status"] == "running"
    )

    stopped = sum(
        1 for server in SERVERS
        if server["status"] == "stopped"
    )

    incidents = get_active_incidents()

    return {
        "total_servers": len(SERVERS),
        "running_servers": running,
        "stopped_servers": stopped,
        "active_incidents": len(incidents),
        "critical_incidents": sum(
            1 for incident in incidents
            if incident["severity"] == "critical"
        ),
        "high_incidents": sum(
            1 for incident in incidents
            if incident["severity"] == "high"
        ),
        "medium_incidents": sum(
            1 for incident in incidents
            if incident["severity"] == "medium"
        ),
        "average_cpu": round(
            sum(server["cpu_usage"] for server in SERVERS)
            / len(SERVERS),
            2,
        ),
        "data_source": "simulated",
    }


# --------------------------------------------------
# AWS MONITORING
# --------------------------------------------------


@app.get("/api/aws/instances")
def get_aws_instances(region: str = "eu-central-1"):
    result = get_ec2_instances(region=region)

    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Unable to retrieve AWS EC2 instances",
                "error": result.get("error"),
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
                "message": "Unable to retrieve CloudWatch CPU metrics",
                "error": result.get("error"),
            },
        )

    return result


# --------------------------------------------------
# LANGGRAPH INCIDENT INVESTIGATION
# --------------------------------------------------


@app.get("/api/ai/investigate/{server_id}")
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

        # Save the investigation to the newest unresolved incident
        # belonging to this server.
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
                    result.get("diagnosis", ""),
                    result.get("recommendation", ""),
                    server_id,
                ),
            ).fetchone()

        return {
            "server_id": server["id"],
            "server_name": server["name"],
            "investigation": result,
            "data_source": "simulated",
            "agent_type": result.get("agent_type", "unknown"),
            "saved_to_database": updated is not None,
        }

    except Exception as error:
        print(f"Incident investigation failed: {error}")

        raise HTTPException(
            status_code=500,
            detail="Incident investigation failed",
        ) from error


# --------------------------------------------------
# SIMULATION ENDPOINTS
# --------------------------------------------------


@app.post("/api/simulation/cpu")
def simulate_cpu(update: CPUUpdate):
    server = find_server(update.server_id)

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
        "incident": detect_server_incident(server),
    }


@app.post("/api/simulation/status")
def simulate_status(update: StatusUpdate):
    server = find_server(update.server_id)

    if server is None:
        raise HTTPException(
            status_code=404,
            detail="Server not found",
        )

    allowed_statuses = {"running", "stopped"}

    if update.status.lower() not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Status must be running or stopped",
        )

    server["status"] = update.status.lower()

    if server["status"] == "stopped":
        server["cpu_usage"] = 0.0

    synchronize_incident_history()

    return {
        "message": "Server status updated",
        "server": server,
        "incident": detect_server_incident(server),
    }