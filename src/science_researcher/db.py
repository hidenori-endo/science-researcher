from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import Evidence, ProofObligation, ResearchClaim, ScientificNode
from .research import (
    validate_claim,
    validate_evidence,
    validate_relation_type,
    validate_research_bundle,
)

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

CREATE TABLE IF NOT EXISTS research_claims (
    id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE,
    title TEXT NOT NULL,
    statement TEXT NOT NULL,
    record_type TEXT NOT NULL,
    epistemic_status TEXT NOT NULL,
    domain TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    axis_texts_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidences (
    id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    epistemic_status TEXT NOT NULL,
    source_uri TEXT NOT NULL DEFAULT '',
    citation TEXT NOT NULL DEFAULT '',
    axis_texts_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_relations (
    id TEXT PRIMARY KEY,
    source_claim_id TEXT NOT NULL REFERENCES research_claims(id) ON DELETE CASCADE,
    target_claim_id TEXT REFERENCES research_claims(id) ON DELETE CASCADE,
    evidence_id TEXT REFERENCES evidences(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((target_claim_id IS NOT NULL) != (evidence_id IS NOT NULL)),
    UNIQUE(source_claim_id, target_claim_id, relation),
    UNIQUE(source_claim_id, evidence_id, relation)
);

CREATE TABLE IF NOT EXISTS research_vectors (
    entity_kind TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    axis TEXT NOT NULL,
    vector_json TEXT NOT NULL,
    canonical_text TEXT NOT NULL DEFAULT '',
    dimensions INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (entity_kind, entity_id, axis),
    CHECK (entity_kind IN ('claim', 'evidence'))
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
    claim_id TEXT REFERENCES research_claims(id),
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


def _claim_from_row(row: sqlite3.Row) -> ResearchClaim:
    return ResearchClaim(
        id=row["id"],
        external_id=row["external_id"],
        title=row["title"],
        statement=row["statement"],
        record_type=row["record_type"],
        epistemic_status=row["epistemic_status"],
        domain=row["domain"],
        source=row["source"],
        axis_texts=json.loads(row["axis_texts_json"]),
        metadata=json.loads(row["metadata_json"]),
        created_at=row["created_at"],
    )


def _evidence_from_row(row: sqlite3.Row) -> Evidence:
    return Evidence(
        id=row["id"],
        external_id=row["external_id"],
        title=row["title"],
        summary=row["summary"],
        evidence_type=row["evidence_type"],
        epistemic_status=row["epistemic_status"],
        source_uri=row["source_uri"],
        citation=row["citation"],
        axis_texts=json.loads(row["axis_texts_json"]),
        metadata=json.loads(row["metadata_json"]),
        created_at=row["created_at"],
    )


def _upsert_claim_row(connection: sqlite3.Connection, claim: ResearchClaim) -> str:
    connection.execute(
        """
        INSERT INTO research_claims (
            id, external_id, title, statement, record_type, epistemic_status,
            domain, source, axis_texts_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            external_id=excluded.external_id,
            title=excluded.title,
            statement=excluded.statement,
            record_type=excluded.record_type,
            epistemic_status=excluded.epistemic_status,
            domain=excluded.domain,
            source=excluded.source,
            axis_texts_json=excluded.axis_texts_json,
            metadata_json=excluded.metadata_json
        """,
        (
            claim.id,
            claim.external_id,
            claim.title,
            claim.statement,
            claim.record_type,
            claim.epistemic_status,
            claim.domain,
            claim.source,
            json.dumps(claim.axis_texts, sort_keys=True),
            json.dumps(claim.metadata, sort_keys=True),
        ),
    )
    return claim.id


def _upsert_evidence_row(connection: sqlite3.Connection, evidence: Evidence) -> str:
    connection.execute(
        """
        INSERT INTO evidences (
            id, external_id, title, summary, evidence_type, epistemic_status,
            source_uri, citation, axis_texts_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            external_id=excluded.external_id,
            title=excluded.title,
            summary=excluded.summary,
            evidence_type=excluded.evidence_type,
            epistemic_status=excluded.epistemic_status,
            source_uri=excluded.source_uri,
            citation=excluded.citation,
            axis_texts_json=excluded.axis_texts_json,
            metadata_json=excluded.metadata_json
        """,
        (
            evidence.id,
            evidence.external_id,
            evidence.title,
            evidence.summary,
            evidence.evidence_type,
            evidence.epistemic_status,
            evidence.source_uri,
            evidence.citation,
            json.dumps(evidence.axis_texts, sort_keys=True),
            json.dumps(evidence.metadata, sort_keys=True),
        ),
    )
    return evidence.id


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
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(hypotheses)").fetchall()
            }
            if "claim_id" not in columns:
                connection.execute(
                    "ALTER TABLE hypotheses ADD COLUMN claim_id TEXT REFERENCES research_claims(id)"
                )

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

    def upsert_research_claim(self, claim: ResearchClaim) -> str:
        validate_claim(claim)
        with self.connect() as connection:
            return _upsert_claim_row(connection, claim)

    def get_research_claim(self, claim_id: str) -> ResearchClaim:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM research_claims WHERE id = ?", (claim_id,)
            ).fetchone()
        if row is None:
            raise KeyError(claim_id)
        return _claim_from_row(row)

    def list_research_claims(self, *, record_type: str | None = None) -> list[ResearchClaim]:
        query = "SELECT * FROM research_claims"
        params: tuple[Any, ...] = ()
        if record_type is not None:
            query += " WHERE record_type = ?"
            params = (record_type,)
        query += " ORDER BY created_at, id"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_claim_from_row(row) for row in rows]

    def upsert_evidence(self, evidence: Evidence) -> str:
        validate_evidence(evidence)
        with self.connect() as connection:
            return _upsert_evidence_row(connection, evidence)

    def get_evidence(self, evidence_id: str) -> Evidence:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM evidences WHERE id = ?", (evidence_id,)
            ).fetchone()
        if row is None:
            raise KeyError(evidence_id)
        return _evidence_from_row(row)

    def list_evidence(self) -> list[Evidence]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM evidences ORDER BY created_at, id").fetchall()
        return [_evidence_from_row(row) for row in rows]

    def link_evidence(
        self,
        claim_id: str,
        evidence_id: str,
        relation: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        relation = validate_relation_type(relation)
        relation_id = str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO research_relations (
                    id, source_claim_id, evidence_id, relation, metadata_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_claim_id, evidence_id, relation) DO UPDATE SET
                    metadata_json=excluded.metadata_json
                """,
                (relation_id, claim_id, evidence_id, relation, json.dumps(metadata or {}, sort_keys=True)),
            )
            row = connection.execute(
                """
                SELECT id FROM research_relations
                WHERE source_claim_id = ? AND evidence_id = ? AND relation = ?
                """,
                (claim_id, evidence_id, relation),
            ).fetchone()
        assert row is not None
        return str(row["id"])

    def link_claims(
        self,
        source_claim_id: str,
        target_claim_id: str,
        relation: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        relation = validate_relation_type(relation)
        relation_id = str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO research_relations (
                    id, source_claim_id, target_claim_id, relation, metadata_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_claim_id, target_claim_id, relation) DO UPDATE SET
                    metadata_json=excluded.metadata_json
                """,
                (
                    relation_id,
                    source_claim_id,
                    target_claim_id,
                    relation,
                    json.dumps(metadata or {}, sort_keys=True),
                ),
            )
            row = connection.execute(
                """
                SELECT id FROM research_relations
                WHERE source_claim_id = ? AND target_claim_id = ? AND relation = ?
                """,
                (source_claim_id, target_claim_id, relation),
            ).fetchone()
        assert row is not None
        return str(row["id"])

    def get_claim_with_relations(self, claim_id: str) -> dict[str, Any]:
        claim = self.get_research_claim(claim_id)
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM research_relations WHERE source_claim_id = ? ORDER BY created_at, id",
                (claim_id,),
            ).fetchall()
        evidence_links: list[dict[str, Any]] = []
        claim_links: list[dict[str, Any]] = []
        for row in rows:
            relation = {
                "id": row["id"],
                "relation": row["relation"],
                "metadata": json.loads(row["metadata_json"]),
            }
            if row["evidence_id"] is not None:
                relation["evidence"] = self.get_evidence(row["evidence_id"]).to_dict()
                evidence_links.append(relation)
            else:
                relation["claim"] = self.get_research_claim(row["target_claim_id"]).to_dict()
                claim_links.append(relation)
        result = claim.to_dict()
        result["evidence"] = evidence_links
        result["claim_relations"] = claim_links
        return result

    def put_research_vector(
        self,
        entity_kind: str,
        entity_id: str,
        axis: str,
        vector: list[float],
        *,
        canonical_text: str = "",
    ) -> None:
        if entity_kind not in ("claim", "evidence"):
            raise ValueError("entity_kind must be claim or evidence")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO research_vectors (
                    entity_kind, entity_id, axis, vector_json, canonical_text, dimensions
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_kind, entity_id, axis) DO UPDATE SET
                    vector_json=excluded.vector_json,
                    canonical_text=excluded.canonical_text,
                    dimensions=excluded.dimensions
                """,
                (entity_kind, entity_id, axis, json.dumps(vector), canonical_text, len(vector)),
            )

    def get_research_vector(self, entity_kind: str, entity_id: str, axis: str) -> list[float]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT vector_json FROM research_vectors
                WHERE entity_kind = ? AND entity_id = ? AND axis = ?
                """,
                (entity_kind, entity_id, axis),
            ).fetchone()
        if row is None:
            raise KeyError((entity_kind, entity_id, axis))
        return list(json.loads(row["vector_json"]))

    def import_research_bundle(self, data: dict[str, Any]) -> dict[str, Any]:
        bundle = validate_research_bundle(data)
        claim_ids: dict[str, str] = {}
        evidence_ids: dict[str, str] = {}
        with self.connect() as connection:
            for claim in bundle.claims:
                existing = connection.execute(
                    "SELECT id FROM research_claims WHERE external_id = ?", (claim.external_id,)
                ).fetchone()
                if existing is not None:
                    claim.id = str(existing["id"])
                _upsert_claim_row(connection, claim)
                assert claim.external_id is not None
                claim_ids[claim.external_id] = claim.id

            for evidence in bundle.evidence:
                existing = connection.execute(
                    "SELECT id FROM evidences WHERE external_id = ?", (evidence.external_id,)
                ).fetchone()
                if existing is not None:
                    evidence.id = str(existing["id"])
                _upsert_evidence_row(connection, evidence)
                assert evidence.external_id is not None
                evidence_ids[evidence.external_id] = evidence.id

            for relation in bundle.relations:
                source_id = claim_ids[relation.claim_external_id]
                metadata_json = json.dumps(relation.metadata or {}, sort_keys=True)
                if relation.evidence_external_id is not None:
                    target_id = evidence_ids[relation.evidence_external_id]
                    relation_id = str(uuid.uuid4())
                    connection.execute(
                        """
                        INSERT INTO research_relations (
                            id, source_claim_id, evidence_id, relation, metadata_json
                        ) VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(source_claim_id, evidence_id, relation) DO UPDATE SET
                            metadata_json=excluded.metadata_json
                        """,
                        (relation_id, source_id, target_id, relation.relation, metadata_json),
                    )
                else:
                    assert relation.target_claim_external_id is not None
                    target_id = claim_ids[relation.target_claim_external_id]
                    relation_id = str(uuid.uuid4())
                    connection.execute(
                        """
                        INSERT INTO research_relations (
                            id, source_claim_id, target_claim_id, relation, metadata_json
                        ) VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(source_claim_id, target_claim_id, relation) DO UPDATE SET
                            metadata_json=excluded.metadata_json
                        """,
                        (relation_id, source_id, target_id, relation.relation, metadata_json),
                    )

        return {
            "schema_version": bundle.schema_version,
            "claims": claim_ids,
            "evidence": evidence_ids,
            "relations": len(bundle.relations),
        }

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
        claim_id = str(uuid.uuid4())
        with self.connect() as connection:
            problem = connection.execute(
                "SELECT domain FROM nodes WHERE id = ?", (problem_id,)
            ).fetchone()
            if problem is None:
                raise KeyError(problem_id)
            generated_claim = ResearchClaim(
                id=claim_id,
                title=title,
                statement=bridge,
                record_type="hypothesis",
                epistemic_status="conjectural" if status == "candidate" else "speculative",
                domain=problem["domain"],
                source=f"discovery_run:{run_id}",
                axis_texts={
                    "semantic": f"{title}. {bridge} Prediction: {prediction}",
                    "mechanism": bridge,
                    "problem_shape": prediction,
                    "failure": failure_reason,
                },
                metadata={
                    "generated_hypothesis_id": hypothesis_id,
                    "analogy_node_id": analogy_node_id,
                    "rationale": rationale,
                    "critic_score": critic_score,
                    "discovery_status": status,
                },
            )
            _upsert_claim_row(connection, generated_claim)
            connection.execute(
                """
                INSERT INTO hypotheses (
                    id, run_id, problem_id, analogy_node_id, claim_id, title, bridge,
                    prediction, rationale, status, critic_score, failure_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hypothesis_id,
                    run_id,
                    problem_id,
                    analogy_node_id,
                    claim_id,
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

    def get_hypothesis_claim(self, hypothesis_id: str) -> ResearchClaim:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT claim_id FROM hypotheses WHERE id = ?", (hypothesis_id,)
            ).fetchone()
        if row is None or row["claim_id"] is None:
            raise KeyError(hypothesis_id)
        return self.get_research_claim(row["claim_id"])

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
