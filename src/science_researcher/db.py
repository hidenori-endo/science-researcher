from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .models import ProofObligation, ScientificNode


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    domain TEXT NOT NULL,
    summary TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    math_structure TEXT NOT NULL,
    problem_shape TEXT NOT NULL,
    failure_modes TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES nodes(id),
    target_id TEXT NOT NULL REFERENCES nodes(id),
    relation TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    evidence_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS vectors (
    node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    axis TEXT NOT NULL,
    vector_json TEXT NOT NULL,
    PRIMARY KEY (node_id, axis)
);

CREATE TABLE IF NOT EXISTS discovery_runs (
    id TEXT PRIMARY KEY,
    problem_id TEXT NOT NULL REFERENCES nodes(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    trace_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS hypotheses (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,
    problem_id TEXT NOT NULL REFERENCES nodes(id),
    analogy_node_id TEXT NOT NULL REFERENCES nodes(id),
    title TEXT NOT NULL,
    bridge TEXT NOT NULL,
    prediction TEXT NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL,
    critic_score REAL NOT NULL,
    failure_reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS proof_obligations (
    id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    statement TEXT NOT NULL,
    status TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);
"""


class GraphStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def upsert_node(self, node: ScientificNode) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO nodes (
                    id, kind, title, domain, summary, mechanism,
                    math_structure, problem_shape, failure_modes, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind,
                    title=excluded.title,
                    domain=excluded.domain,
                    summary=excluded.summary,
                    mechanism=excluded.mechanism,
                    math_structure=excluded.math_structure,
                    problem_shape=excluded.problem_shape,
                    failure_modes=excluded.failure_modes,
                    metadata_json=excluded.metadata_json
                """,
                (
                    node.id,
                    node.kind,
                    node.title,
                    node.domain,
                    node.summary,
                    node.mechanism,
                    node.math_structure,
                    node.problem_shape,
                    node.failure_modes,
                    json.dumps(node.metadata, sort_keys=True),
                ),
            )

    def get_node(self, node_id: str) -> ScientificNode:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if row is None:
            raise KeyError(node_id)
        return ScientificNode(
            id=row["id"],
            kind=row["kind"],
            title=row["title"],
            domain=row["domain"],
            summary=row["summary"],
            mechanism=row["mechanism"],
            math_structure=row["math_structure"],
            problem_shape=row["problem_shape"],
            failure_modes=row["failure_modes"],
            metadata=json.loads(row["metadata_json"]),
        )

    def list_nodes(self, *, kind: str | None = None) -> list[ScientificNode]:
        query = "SELECT id FROM nodes"
        params: tuple[Any, ...] = ()
        if kind is not None:
            query += " WHERE kind = ?"
            params = (kind,)
        query += " ORDER BY id"
        with self.connect() as connection:
            ids = [row["id"] for row in connection.execute(query, params).fetchall()]
        return [self.get_node(node_id) for node_id in ids]

    def put_vector(self, node_id: str, axis: str, vector: list[float]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO vectors (node_id, axis, vector_json)
                VALUES (?, ?, ?)
                ON CONFLICT(node_id, axis) DO UPDATE SET vector_json=excluded.vector_json
                """,
                (node_id, axis, json.dumps(vector)),
            )

    def get_vector(self, node_id: str, axis: str) -> list[float]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT vector_json FROM vectors WHERE node_id = ? AND axis = ?",
                (node_id, axis),
            ).fetchone()
        if row is None:
            raise KeyError((node_id, axis))
        return list(json.loads(row["vector_json"]))

    def create_run(self, problem_id: str) -> str:
        run_id = str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO discovery_runs (id, problem_id) VALUES (?, ?)",
                (run_id, problem_id),
            )
        return run_id

    def update_run_trace(self, run_id: str, trace: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE discovery_runs SET trace_json = ? WHERE id = ?",
                (json.dumps(trace, sort_keys=True), run_id),
            )

    def save_hypothesis(
        self,
        *,
        run_id: str,
        problem_id: str,
        analogy_node_id: str,
        title: str,
        bridge: str,
        prediction: str,
        rationale: str,
        status: str,
        critic_score: float,
        failure_reason: str,
        obligations: list[ProofObligation],
    ) -> str:
        hypothesis_id = str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO hypotheses (
                    id, run_id, problem_id, analogy_node_id, title, bridge,
                    prediction, rationale, status, critic_score, failure_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hypothesis_id,
                    run_id,
                    problem_id,
                    analogy_node_id,
                    title,
                    bridge,
                    prediction,
                    rationale,
                    status,
                    critic_score,
                    failure_reason,
                ),
            )
            for index, obligation in enumerate(obligations):
                connection.execute(
                    """
                    INSERT INTO proof_obligations (
                        id, hypothesis_id, position, statement, status,
                        verification_method, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        hypothesis_id,
                        index,
                        obligation.statement,
                        obligation.status,
                        obligation.verification_method,
                        obligation.notes,
                    ),
                )
        return hypothesis_id

    def list_runs(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, problem_id, created_at FROM discovery_runs ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            run = connection.execute(
                "SELECT * FROM discovery_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run is None:
                raise KeyError(run_id)
            hypotheses = connection.execute(
                "SELECT * FROM hypotheses WHERE run_id = ? ORDER BY critic_score DESC",
                (run_id,),
            ).fetchall()
            result_hypotheses: list[dict[str, Any]] = []
            for hypothesis in hypotheses:
                obligations = connection.execute(
                    """
                    SELECT statement, status, verification_method, notes
                    FROM proof_obligations
                    WHERE hypothesis_id = ?
                    ORDER BY position
                    """,
                    (hypothesis["id"],),
                ).fetchall()
                item = dict(hypothesis)
                item["proof_obligations"] = [dict(row) for row in obligations]
                result_hypotheses.append(item)

        return {
            "id": run["id"],
            "problem_id": run["problem_id"],
            "created_at": run["created_at"],
            "trace": json.loads(run["trace_json"]),
            "hypotheses": result_hypotheses,
        }
