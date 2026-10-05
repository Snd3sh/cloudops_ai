import psycopg

DATABASE_URL = "dbname=cloudops_ai user=postgres host=/var/run/postgresql"


def get_connection():
    return psycopg.connect(DATABASE_URL)


def initialize_database():
    with get_connection() as connection:

        # --------------------------------------------------
        # INCIDENT HISTORY
        # --------------------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS incident_history (
                id TEXT PRIMARY KEY,
                server_id TEXT NOT NULL,
                server_name TEXT NOT NULL,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                detected_at TIMESTAMPTZ NOT NULL,
                resolved_at TIMESTAMPTZ,
                diagnosis TEXT,
                recommendation TEXT,
                investigated_at TIMESTAMPTZ
            )
        """)

        # Add new columns to existing databases safely.
        connection.execute("""
            ALTER TABLE incident_history
            ADD COLUMN IF NOT EXISTS diagnosis TEXT
        """)

        connection.execute("""
            ALTER TABLE incident_history
            ADD COLUMN IF NOT EXISTS recommendation TEXT
        """)

        connection.execute("""
            ALTER TABLE incident_history
            ADD COLUMN IF NOT EXISTS investigated_at TIMESTAMPTZ
        """)

        # --------------------------------------------------
        # REMEDIATION APPROVALS
        # --------------------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS remediation_approvals (
                id SERIAL PRIMARY KEY,

                proposal_id TEXT NOT NULL,

                server_id TEXT NOT NULL,

                server_name TEXT NOT NULL,

                action TEXT NOT NULL,

                incident_type TEXT NOT NULL,

                severity TEXT NOT NULL,

                approval_status TEXT NOT NULL,

                approver TEXT,

                rejection_reason TEXT,

                execution_status TEXT NOT NULL DEFAULT 'not_executed',

                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                decided_at TIMESTAMPTZ
            )
        """)

        connection.commit()


def save_remediation_approval(
    proposal: dict,
    approval_status: str,
    approver: str | None = None,
    rejection_reason: str | None = None,
):
    """
    Save a remediation approval or rejection decision.

    This function only records the decision.
    It does NOT execute any AWS action.
    """

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO remediation_approvals (
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
                decided_at
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, NOW()
            )
            RETURNING id
            """,
            (
                proposal["proposal_id"],
                proposal["server_id"],
                proposal["server_name"],
                proposal["action"],
                proposal["incident_type"],
                proposal["severity"],
                approval_status,
                approver,
                rejection_reason,
                proposal.get("execution_status", "not_executed"),
            ),
        )

        row = cursor.fetchone()

        connection.commit()

        return row[0] if row else None

def update_remediation_execution_status(
    proposal_id: str,
    execution_status: str,
):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE remediation_approvals
            SET execution_status = %s
            WHERE proposal_id = %s
            """,
            (execution_status, proposal_id),
        )
        connection.commit()