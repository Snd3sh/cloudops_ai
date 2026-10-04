
import psycopg

DATABASE_URL = "dbname=cloudops_ai user=postgres host=/var/run/postgresql"


def get_connection():
    return psycopg.connect(DATABASE_URL)


def initialize_database():
    with get_connection() as connection:
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
