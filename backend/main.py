
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import get_connection, initialize_database
from backend.aws_monitor import get_ec2_instances


app = FastAPI(title="CloudOps AI")

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


# Simulated server data
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


class CPUUpdate(BaseModel):
    server_id: str
    cpu_usage: float = Field(ge=0, le=100)


class StatusUpdate(BaseModel):
    server_id: str
    status: str


def current_timestamp():
    return datetime.now(timezone.utc)


def find_server(server_id: str):
    for server in SERVERS:
        if server["id"] == server_id:
            return server
    return None


def detect_server_incident(server: dict):
    if server["status"] != "running":
        return {
            "server_id": server["id"],
            "server_name": server["name"],
            "type": "SERVER_STOPPED",
            "severity": "high",
            "message": f'{server["name"]} is not running.',
        }

    if server["cpu_usage"] > 80:
        return {
            "server_id": server["id"],
            "server_name": server["name"],
            "type": "HIGH_CPU",
            "severity": "high",
            "message": (
                f'{server["name"]} CPU usage is '
                f'{server["cpu_usage"]}%.'
            ),
        }

    if server["cpu_usage"] >= 60:
        return {
            "server_id": server["id"],
            "server_name": server["name"],
            "type": "ELEVATED_CPU",
            "severity": "medium",
            "message": (
                f'{server["name"]} CPU usage is '
                f'{server["cpu_usage"]}%.'
            ),
        }

    return None


def synchronize_incident_history():
    current_incidents = []

    with get_connection() as connection:
        for server in SERVERS:
            incident = detect_server_incident(server)

            row = connection.execute(
                """
                SELECT id, type
                FROM incident_history
                WHERE server_id = %s AND resolved_at IS NULL
                ORDER BY detected_at DESC
                LIMIT 1
                """,
                (server["id"],),
            ).fetchone()

            if incident is None:
                if row is not None:
                    connection.execute(
                        """
                        UPDATE incident_history
                        SET resolved_at = %s
                        WHERE id = %s
                        """,
                        (current_timestamp(), row[0]),
                    )
                continue

            current_incidents.append(incident)

            if row is not None and row[1] == incident["type"]:
                connection.execute(
                    """
                    UPDATE incident_history
                    SET message = %s, severity = %s
                    WHERE id = %s
                    """,
                    (
                        incident["message"],
                        incident["severity"],
                        row[0],
                    ),
                )
                continue

            if row is not None:
                connection.execute(
                    """
                    UPDATE incident_history
                    SET resolved_at = %s
                    WHERE id = %s
                    """,
                    (current_timestamp(), row[0]),
                )

            connection.execute(
                """
                INSERT INTO incident_history (
                    id, server_id, server_name, type,
                    severity, message, detected_at, resolved_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
                """,
                (
                    str(uuid4()),
                    incident["server_id"],
                    incident["server_name"],
                    incident["type"],
                    incident["severity"],
                    incident["message"],
                    current_timestamp(),
                ),
            )

    return current_incidents


def serialize_incident(row):
    keys = [
        "id",
        "server_id",
        "server_name",
        "type",
        "severity",
        "message",
        "detected_at",
        "resolved_at",
    ]

    incident = dict(zip(keys, row))

    for field in ("detected_at", "resolved_at"):
        if incident[field] is not None:
            incident[field] = incident[field].isoformat()

    return incident


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def home():
    return {
        "project": "CloudOps AI",
        "message": "Cloud operations assistant is running!",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# Simulated monitoring
@app.get("/api/monitoring")
def get_monitoring():
    return {
        "servers": SERVERS,
        "data_source": "simulation",
    }


# Real AWS EC2 monitoring
@app.get("/api/aws/instances")
def get_aws_instances_endpoint():
    result = get_ec2_instances()

    if not result["success"]:
        raise HTTPException(
            status_code=502,
            detail=result["error"],
        )

    return result


# Current active incidents
@app.get("/api/incidents")
def get_incidents():
    incidents = synchronize_incident_history()

    return {
        "total_incidents": len(incidents),
        "incidents": incidents,
        "data_source": "simulation",
    }


# Dashboard summary
@app.get("/api/dashboard")
def get_dashboard():
    running_servers = sum(
        1 for server in SERVERS
        if server["status"] == "running"
    )

    incidents = synchronize_incident_history()

    return {
        "total_servers": len(SERVERS),
        "running_servers": running_servers,
        "stopped_servers": len(SERVERS) - running_servers,
        "total_incidents": len(incidents),
        "high_severity_incidents": sum(
            1 for incident in incidents
            if incident["severity"] == "high"
        ),
        "medium_severity_incidents": sum(
            1 for incident in incidents
            if incident["severity"] == "medium"
        ),
    }


# Persistent incident history
@app.get("/api/incidents/history")
def get_incident_history():
    synchronize_incident_history()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, server_id, server_name, type,
                   severity, message, detected_at, resolved_at
            FROM incident_history
            ORDER BY detected_at DESC
            """
        ).fetchall()

    history = [serialize_incident(row) for row in rows]

    return {
        "total_records": len(history),
        "history": history,
        "data_source": "postgresql",
    }


# Simulation: update CPU usage
@app.post("/api/simulation/cpu")
def update_simulated_cpu(update: CPUUpdate):
    server = find_server(update.server_id)

    if server is None:
        raise HTTPException(
            status_code=404,
            detail="Server not found",
        )

    server["cpu_usage"] = update.cpu_usage

    return {
        "message": "CPU usage updated",
        "server": server,
    }


# Simulation: start or stop a server
@app.post("/api/simulation/status")
def update_simulated_status(update: StatusUpdate):
    if update.status not in ["running", "stopped"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be running or stopped",
        )

    server = find_server(update.server_id)

    if server is None:
        raise HTTPException(
            status_code=404,
            detail="Server not found",
        )

    server["status"] = update.status

    if update.status == "stopped":
        server["cpu_usage"] = 0.0

    return {
        "message": "Server status updated",
        "server": server,
    }