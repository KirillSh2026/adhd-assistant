from __future__ import annotations

from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb

from models.item import Item


class PostgresStorage:
    def __init__(self, dsn: str, project_name: str = "Inbox"):
        self.dsn = dsn
        self.project_name = project_name

    def supports_advanced_relations(self) -> bool:
        return True

    def _ensure_project_id(self, conn: psycopg.Connection) -> str:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM project WHERE name = %s LIMIT 1", (self.project_name,))
            row = cur.fetchone()
            if row:
                return str(row[0])

            cur.execute(
                """
                INSERT INTO project (name, description, status)
                VALUES (%s, %s, 'active')
                RETURNING id
                """,
                (self.project_name, "Created by CLI storage backend"),
            )
            created = cur.fetchone()
            if not created:
                raise RuntimeError("Failed to create default project")
            return str(created[0])

    def load_items(self) -> list[Item]:
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            return self._load_project_items(conn=conn, project_id=project_id, include_archived=False)

    def _load_project_items(
        self,
        conn: psycopg.Connection,
        project_id: str,
        include_archived: bool,
    ) -> list[Item]:
        archived_filter = "" if include_archived else "AND status <> 'archived'"
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    id,
                    type,
                    text,
                    to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') AS datetime,
                    status
                FROM item
                WHERE project_id = %s
                  {archived_filter}
                ORDER BY created_at ASC, id ASC
                """,
                (project_id,),
            )
            rows = cur.fetchall()
        return [
            Item(id=str(row[0]), type=row[1], text=row[2], datetime=row[3], status=row[4])
            for row in rows
        ]

    def load_items_for_relations(self, include_archived: bool = False) -> list[Item]:
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            return self._load_project_items(conn=conn, project_id=project_id, include_archived=include_archived)

    def add_item(self, item: Item) -> None:
        created_at = datetime.strptime(item.datetime, "%Y-%m-%d %H:%M:%S") if item.datetime else datetime.now()
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO item (project_id, type, text, source, created_at, updated_at)
                    VALUES (%s, %s, %s, 'cli', %s, %s)
                    """,
                    (project_id, item.type, item.text, created_at, created_at),
                )
            conn.commit()

    def clear_items(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM item WHERE project_id = %s", (project_id,))
            conn.commit()

    def save_relation_suggestions(self, suggestions: list[dict]) -> int:
        if not suggestions:
            return 0

        with psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    for suggestion in suggestions:
                        self._assert_relation_items_accessible(
                            cur=cur,
                            from_item_id=suggestion["from_item_id"],
                            to_item_id=suggestion["to_item_id"],
                        )
                        cur.execute(
                            """
                            INSERT INTO item_dependency (
                                from_item_id,
                                to_item_id,
                                relationship_type,
                                reason,
                                is_confirmed,
                                confirmed_at
                            )
                            VALUES (%s, %s, %s, %s, FALSE, NULL)
                            ON CONFLICT (from_item_id, to_item_id, relationship_type)
                            DO UPDATE SET
                                reason = EXCLUDED.reason,
                                updated_at = CURRENT_TIMESTAMP
                            """,
                            (
                                suggestion["from_item_id"],
                                suggestion["to_item_id"],
                                suggestion["relationship_type"],
                                suggestion["reason"],
                            ),
                        )
            conn.commit()
        return len(suggestions)

    def upsert_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str,
        is_confirmed: bool,
    ) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    self._assert_relation_items_accessible(
                        cur=cur,
                        from_item_id=from_item_id,
                        to_item_id=to_item_id,
                    )
                    cur.execute(
                        """
                        INSERT INTO item_dependency (
                            from_item_id,
                            to_item_id,
                            relationship_type,
                            reason,
                            is_confirmed,
                            confirmed_at
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END
                        )
                        ON CONFLICT (from_item_id, to_item_id, relationship_type)
                        DO UPDATE SET
                            reason = EXCLUDED.reason,
                            is_confirmed = item_dependency.is_confirmed OR EXCLUDED.is_confirmed,
                            confirmed_at = CASE
                                WHEN item_dependency.is_confirmed OR EXCLUDED.is_confirmed
                                    THEN COALESCE(item_dependency.confirmed_at, CURRENT_TIMESTAMP)
                                ELSE item_dependency.confirmed_at
                            END,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (
                            from_item_id,
                            to_item_id,
                            relationship_type,
                            reason,
                            is_confirmed,
                            is_confirmed,
                        ),
                    )
            conn.commit()

    def confirm_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    self._assert_relation_items_accessible(
                        cur=cur,
                        from_item_id=from_item_id,
                        to_item_id=to_item_id,
                    )
                    cur.execute(
                        """
                        UPDATE item_dependency
                        SET
                            is_confirmed = TRUE,
                            confirmed_at = COALESCE(confirmed_at, CURRENT_TIMESTAMP),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE from_item_id = %s
                          AND to_item_id = %s
                          AND relationship_type = %s
                        """,
                        (from_item_id, to_item_id, relationship_type),
                    )
                    if cur.rowcount == 0:
                        raise ValueError("Relation suggestion not found")
            conn.commit()

    def reject_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    self._assert_relation_items_accessible(
                        cur=cur,
                        from_item_id=from_item_id,
                        to_item_id=to_item_id,
                    )
                    cur.execute(
                        """
                        DELETE FROM item_dependency
                        WHERE from_item_id = %s
                          AND to_item_id = %s
                          AND relationship_type = %s
                          AND is_confirmed = FALSE
                        """,
                        (from_item_id, to_item_id, relationship_type),
                    )
                    if cur.rowcount == 0:
                        raise ValueError("Unconfirmed relation suggestion not found")
            conn.commit()

    def list_relations(self, item_id: str | None = None) -> list[dict]:
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            filter_sql = ""
            params: list[str] = [project_id]
            if item_id:
                filter_sql = "AND (d.from_item_id = %s OR d.to_item_id = %s)"
                params.extend([item_id, item_id])

            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        d.from_item_id,
                        d.to_item_id,
                        d.relationship_type,
                        d.reason,
                        d.is_confirmed,
                        to_char(d.created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at,
                        from_item.text,
                        to_item.text
                    FROM item_dependency d
                    JOIN item AS from_item ON from_item.id = d.from_item_id
                    JOIN item AS to_item ON to_item.id = d.to_item_id
                    WHERE from_item.project_id = %s
                      AND to_item.project_id = %s
                      {filter_sql}
                    ORDER BY d.is_confirmed ASC, d.created_at DESC, d.relationship_type ASC
                    """,
                    [project_id, project_id, *params[1:]],
                )
                rows = cur.fetchall()

        return [
            {
                "from_item_id": str(row[0]),
                "to_item_id": str(row[1]),
                "relationship_type": row[2],
                "reason": row[3] or "",
                "is_confirmed": row[4],
                "created_at": row[5],
                "from_text": row[6],
                "to_text": row[7],
            }
            for row in rows
        ]

    def merge_items(self, target_item_id: str, source_item_ids: list[str], merge_reason: str) -> None:
        unique_source_ids = [item_id for item_id in dict.fromkeys(source_item_ids) if item_id != target_item_id]
        if not unique_source_ids:
            raise ValueError("At least one source item is required for merge")

        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            all_ids = [target_item_id, *unique_source_ids]
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, type, text, status, to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at
                        FROM item
                        WHERE project_id = %s
                          AND id = ANY(%s)
                        ORDER BY created_at ASC, id ASC
                        """,
                        (project_id, all_ids),
                    )
                    rows = cur.fetchall()

                    if len(rows) != len(all_ids):
                        raise ValueError("One or more items were not found in the active project")

                    items_by_id = {
                        str(row[0]): {
                            "id": str(row[0]),
                            "type": row[1],
                            "text": row[2],
                            "status": row[3],
                            "created_at": row[4],
                        }
                        for row in rows
                    }
                    if any(items_by_id[item_id]["status"] == "archived" for item_id in all_ids):
                        raise ValueError("Archived items cannot be merged")

                    target_item = items_by_id[target_item_id]
                    source_items = [items_by_id[item_id] for item_id in unique_source_ids]
                    merged_text = self._build_merged_text(target_item["text"], [item["text"] for item in source_items])
                    merge_snapshot = {
                        "target_before": target_item,
                        "source_items": source_items,
                    }

                    cur.execute(
                        """
                        UPDATE item
                        SET text = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (merged_text, target_item_id),
                    )

                    cur.execute(
                        """
                        INSERT INTO item_merge (
                            merged_into_id,
                            merged_from_ids,
                            merged_from_content,
                            merge_reason
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            target_item_id,
                            unique_source_ids,
                            Jsonb(merge_snapshot),
                            merge_reason,
                        ),
                    )

                    cur.execute(
                        """
                        INSERT INTO item_audit (item_id, action, old_value, new_value, reason)
                        VALUES (%s, 'merged', %s, %s, %s)
                        """,
                        (
                            target_item_id,
                            Jsonb({"text": target_item["text"]}),
                            Jsonb({"text": merged_text, "merged_from_ids": unique_source_ids}),
                            merge_reason,
                        ),
                    )

                    for source_item in source_items:
                        cur.execute(
                            """
                            UPDATE item
                            SET status = 'archived', updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            """,
                            (source_item["id"],),
                        )
                        cur.execute(
                            """
                            INSERT INTO item_audit (item_id, action, old_value, new_value, reason)
                            VALUES (%s, 'archived', %s, %s, %s)
                            """,
                            (
                                source_item["id"],
                                Jsonb({"status": source_item["status"], "text": source_item["text"]}),
                                Jsonb({"status": "archived", "merged_into_id": target_item_id}),
                                merge_reason,
                            ),
                        )
                        cur.execute(
                            """
                            INSERT INTO item_dependency (
                                from_item_id,
                                to_item_id,
                                relationship_type,
                                reason,
                                is_confirmed,
                                confirmed_at
                            )
                            VALUES (%s, %s, 'duplicate_of', %s, TRUE, CURRENT_TIMESTAMP)
                            ON CONFLICT (from_item_id, to_item_id, relationship_type)
                            DO UPDATE SET
                                reason = EXCLUDED.reason,
                                is_confirmed = TRUE,
                                confirmed_at = COALESCE(item_dependency.confirmed_at, CURRENT_TIMESTAMP),
                                updated_at = CURRENT_TIMESTAMP
                            """,
                            (
                                source_item["id"],
                                target_item_id,
                                merge_reason,
                            ),
                        )
            conn.commit()

    def list_merges(self, limit: int = 20) -> list[dict]:
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        m.id,
                        m.merged_into_id,
                        m.merged_from_ids,
                        m.merge_reason,
                        m.can_undo,
                        to_char(m.performed_at, 'YYYY-MM-DD HH24:MI:SS') AS performed_at
                    FROM item_merge m
                    JOIN item target_item ON target_item.id = m.merged_into_id
                    WHERE target_item.project_id = %s
                    ORDER BY m.performed_at DESC
                    LIMIT %s
                    """,
                    (project_id, limit),
                )
                rows = cur.fetchall()

        return [
            {
                "merge_id": str(row[0]),
                "target_item_id": str(row[1]),
                "source_item_ids": [str(item_id) for item_id in (row[2] or [])],
                "reason": row[3] or "",
                "can_undo": row[4],
                "performed_at": row[5],
            }
            for row in rows
        ]

    def undo_last_merge(self, merge_id: str | None = None) -> dict:
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    if merge_id:
                        cur.execute(
                            """
                            SELECT
                                m.id,
                                m.merged_into_id,
                                m.merged_from_ids,
                                m.merged_from_content,
                                m.merge_reason,
                                m.can_undo
                            FROM item_merge m
                            JOIN item target_item ON target_item.id = m.merged_into_id
                            WHERE m.id = %s
                              AND target_item.project_id = %s
                            LIMIT 1
                            """,
                            (merge_id, project_id),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT
                                m.id,
                                m.merged_into_id,
                                m.merged_from_ids,
                                m.merged_from_content,
                                m.merge_reason,
                                m.can_undo
                            FROM item_merge m
                            JOIN item target_item ON target_item.id = m.merged_into_id
                            WHERE target_item.project_id = %s
                            ORDER BY m.performed_at DESC
                            LIMIT 1
                            """,
                            (project_id,),
                        )
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("No merge found to undo")

                    selected_merge_id = str(row[0])
                    target_item_id = str(row[1])
                    source_item_ids = [str(item_id) for item_id in (row[2] or [])]
                    merge_payload = row[3] or {}
                    merge_reason = row[4] or "Undo merge"
                    can_undo = bool(row[5])

                    if not can_undo:
                        raise ValueError("This merge can no longer be undone")

                    target_before = merge_payload.get("target_before")
                    source_items = merge_payload.get("source_items")
                    if not isinstance(target_before, dict) or not isinstance(source_items, list):
                        raise RuntimeError("Merge payload does not contain required rollback snapshot")

                    cur.execute("SELECT text FROM item WHERE id = %s LIMIT 1", (target_item_id,))
                    target_row = cur.fetchone()
                    if not target_row:
                        raise ValueError("Target item for merge rollback was not found")
                    current_target_text = str(target_row[0] or "")

                    cur.execute(
                        """
                        UPDATE item
                        SET text = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (str(target_before.get("text", "")), target_item_id),
                    )

                    for source_item in source_items:
                        source_id = str(source_item.get("id", ""))
                        if not source_id:
                            continue
                        original_status = str(source_item.get("status") or "pending")
                        original_text = str(source_item.get("text") or "")
                        cur.execute(
                            """
                            UPDATE item
                            SET
                                text = %s,
                                status = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            """,
                            (original_text, original_status, source_id),
                        )
                        cur.execute(
                            """
                            DELETE FROM item_dependency
                            WHERE from_item_id = %s
                              AND to_item_id = %s
                              AND relationship_type = 'duplicate_of'
                            """,
                            (source_id, target_item_id),
                        )
                        cur.execute(
                            """
                            INSERT INTO item_audit (item_id, action, old_value, new_value, reason)
                            VALUES (%s, 'updated', %s, %s, %s)
                            """,
                            (
                                source_id,
                                Jsonb({"status": "archived"}),
                                Jsonb({"status": original_status, "text": original_text}),
                                f"undo_merge:{selected_merge_id}",
                            ),
                        )

                    cur.execute(
                        """
                        INSERT INTO item_audit (item_id, action, old_value, new_value, reason)
                        VALUES (%s, 'updated', %s, %s, %s)
                        """,
                        (
                            target_item_id,
                            Jsonb({"text": current_target_text}),
                            Jsonb({"text": str(target_before.get("text", ""))}),
                            f"undo_merge:{selected_merge_id}",
                        ),
                    )

                    cur.execute(
                        """
                        UPDATE item_merge
                        SET can_undo = FALSE
                        WHERE id = %s
                        """,
                        (selected_merge_id,),
                    )
            conn.commit()

        return {
            "merge_id": selected_merge_id,
            "target_item_id": target_item_id,
            "source_item_ids": source_item_ids,
            "reason": merge_reason,
        }

    def _assert_relation_items_accessible(self, cur, from_item_id: str, to_item_id: str) -> None:
        if from_item_id == to_item_id:
            raise ValueError("Relation cannot reference the same item on both sides")

        cur.execute(
            """
            SELECT id, project_id, status
            FROM item
            WHERE id = ANY(%s)
            """,
            ([from_item_id, to_item_id],),
        )
        rows = cur.fetchall()
        if len(rows) != 2:
            raise ValueError("One or both relation items were not found")

        rows_by_id = {str(row[0]): (str(row[1]) if row[1] else None, row[2]) for row in rows}
        from_project_id, from_status = rows_by_id[from_item_id]
        to_project_id, to_status = rows_by_id[to_item_id]
        if not from_project_id or not to_project_id or from_project_id != to_project_id:
            raise ValueError("Relation items must belong to the same project")
        if from_status == "archived" or to_status == "archived":
            raise ValueError("Archived items cannot be linked")

    def _build_merged_text(self, target_text: str, source_texts: list[str]) -> str:
        ordered_texts: list[str] = []
        for text in [target_text, *source_texts]:
            normalized = text.strip()
            if normalized and normalized not in ordered_texts:
                ordered_texts.append(normalized)
        return "\n\n".join(ordered_texts)
