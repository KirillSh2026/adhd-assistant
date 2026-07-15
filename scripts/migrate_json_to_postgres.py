from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime

import psycopg


def parse_datetime(raw_value: str | None) -> datetime:
    if not raw_value:
        return datetime.now()
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.now()


def ensure_migration_runs_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_run (
                id UUID PRIMARY KEY,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                note TEXT
            )
            """
        )
    conn.commit()


def ensure_project(conn: psycopg.Connection, project_name: str) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM project WHERE name = %s LIMIT 1", (project_name,))
        row = cur.fetchone()
        if row:
            return str(row[0])

        cur.execute(
            """
            INSERT INTO project (name, description, status)
            VALUES (%s, %s, 'active')
            RETURNING id
            """,
            (project_name, "Created by JSON migration"),
        )
        created = cur.fetchone()
        if not created:
            raise RuntimeError("Failed to create migration project")
        return str(created[0])


def run_import(dsn: str, json_path: str, project_name: str, dry_run: bool) -> None:
    with open(json_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    if dry_run:
        print(f"Dry run: {len(payload)} rows read from {json_path}")
        return

    run_id = str(uuid.uuid4())
    source_tag = f"cli_migration:{run_id}"
    imported_count = 0

    with psycopg.connect(dsn) as conn:
        ensure_migration_runs_table(conn)

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO migration_run (id, kind, status, note) VALUES (%s, 'json_import', 'running', %s)",
                (run_id, f"Import from {json_path}"),
            )
        conn.commit()

        project_id = ensure_project(conn, project_name)

        with conn.cursor() as cur:
            for note in payload:
                item_type = str(note.get("type", "note"))
                text = str(note.get("text", ""))
                created_at = parse_datetime(note.get("datetime"))

                cur.execute(
                    """
                    INSERT INTO item (project_id, type, text, source, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (project_id, item_type, text, source_tag, created_at, created_at),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError("Failed to insert item during migration")
                item_id = row[0]

                cur.execute(
                    """
                    INSERT INTO item_audit (item_id, action, reason, performed_at)
                    VALUES (%s, 'created', 'Migrated from JSON', %s)
                    """,
                    (item_id, created_at),
                )
                imported_count += 1

            cur.execute(
                """
                UPDATE migration_run
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP, note = %s
                WHERE id = %s
                """,
                (f"Imported {imported_count} rows from {json_path}", run_id),
            )
        conn.commit()

    print(f"Imported {imported_count} rows. Run ID: {run_id}")


def rollback_last_import(dsn: str) -> None:
    with psycopg.connect(dsn) as conn:
        ensure_migration_runs_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM migration_run
                WHERE kind = 'json_import' AND status = 'completed'
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                print("No completed migration_run found.")
                return

            run_id = str(row[0])
            source_tag = f"cli_migration:{run_id}"

            cur.execute("DELETE FROM item_audit WHERE reason = 'Migrated from JSON' AND item_id IN (SELECT id FROM item WHERE source = %s)", (source_tag,))
            cur.execute("DELETE FROM item WHERE source = %s", (source_tag,))
            cur.execute(
                """
                UPDATE migration_run
                SET status = 'rolled_back', completed_at = CURRENT_TIMESTAMP, note = %s
                WHERE id = %s
                """,
                ("Rollback completed", run_id),
            )
        conn.commit()

    print(f"Rolled back migration run: {run_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate data/notes.json into PostgreSQL item table.")
    parser.add_argument("--dsn", default=os.getenv("DATABASE_URL", ""), help="PostgreSQL DSN (or DATABASE_URL)")
    parser.add_argument("--json-path", default="data/notes.json", help="Path to legacy JSON file")
    parser.add_argument("--project-name", default="Inbox", help="Project to attach imported items")
    parser.add_argument("--dry-run", action="store_true", help="Validate JSON input without writing")
    parser.add_argument("--rollback-last", action="store_true", help="Rollback the latest completed JSON import")
    args = parser.parse_args()

    if not args.dsn:
        raise ValueError("PostgreSQL DSN is required. Use --dsn or DATABASE_URL.")

    if args.rollback_last:
        rollback_last_import(args.dsn)
        return

    run_import(
        dsn=args.dsn,
        json_path=args.json_path,
        project_name=args.project_name,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
