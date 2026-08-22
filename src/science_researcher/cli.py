from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

from .embedding_openai import OpenAIEmbeddingProvider
from .embeddings import HashEmbedder
from .models import (
    EpistemicStatus,
    Evidence,
    EvidenceType,
    RecordType,
    ResearchClaim,
    ResearchRelationType,
)
from .provider import HeuristicProvider
from .provider_http import OpenAICompatibleChatProvider
from .research import ResearchIndex
from .service import (
    build_engine,
    initialize_postgres_store,
    initialize_store,
    seed_store,
)


def _json_dump(value: object) -> None:
    json.dump(value, sys.stdout, indent=2, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


def _make_store(args: argparse.Namespace):
    if args.store == "sqlite":
        return initialize_store(args.db)
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Postgres store requires --database-url or DATABASE_URL")
    return initialize_postgres_store(database_url)


def _make_embedder(args: argparse.Namespace):
    if args.embedder == "hash":
        return HashEmbedder(dimensions=args.hash_dimensions)
    return OpenAIEmbeddingProvider.from_env(
        api_key_env=args.embedding_api_key_env,
        model=args.embedding_model,
        base_url=args.embedding_base_url,
        dimensions=args.embedding_dimensions,
    )


def cmd_init(args: argparse.Namespace) -> int:
    store = _make_store(args)
    if args.seed:
        seed_store(store, _make_embedder(args))
    target = args.db if args.store == "sqlite" else "postgres"
    print(f"initialized {target}")
    return 0


def _make_provider(args: argparse.Namespace, *, critic: bool = False):
    if args.provider == "heuristic":
        return HeuristicProvider()
    model = args.critic_model if critic and args.critic_model else args.model
    return OpenAICompatibleChatProvider.from_env(
        model=model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
    )


def cmd_demo(args: argparse.Namespace) -> int:
    store = _make_store(args)
    embedder = _make_embedder(args)
    seed_store(store, embedder)
    problem_id = args.problem if args.problem.startswith("problem:") else f"problem:{args.problem}"
    result = build_engine(
        store,
        generator=_make_provider(args, critic=False),
        critic=_make_provider(args, critic=True),
        embedder=embedder,
    ).run(problem_id, candidates_per_reframing=args.candidates)
    _json_dump(result)
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    store = _make_store(args)
    _json_dump(store.list_runs())
    return 0


def cmd_show_run(args: argparse.Namespace) -> int:
    store = _make_store(args)
    _json_dump(store.get_run(args.run_id))
    return 0


def _metadata_from_args(args: argparse.Namespace) -> dict[str, object]:
    raw = getattr(args, "metadata_json", None)
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise TypeError("--metadata-json must decode to an object")
    return value


def _axis_texts_from_args(args: argparse.Namespace) -> dict[str, str]:
    values = {
        "mechanism": getattr(args, "mechanism", None),
        "math_structure": getattr(args, "math_structure", None),
        "problem_shape": getattr(args, "problem_shape", None),
        "failure": getattr(args, "failure", None),
    }
    return {axis: text for axis, text in values.items() if text}


def _search_axis_texts_from_args(args: argparse.Namespace) -> dict[str, str]:
    values = {
        "semantic": getattr(args, "semantic", None),
        "domain": getattr(args, "domain", None),
        "mechanism": getattr(args, "mechanism", None),
        "math_structure": getattr(args, "math_structure", None),
        "problem_shape": getattr(args, "problem_shape", None),
        "failure": getattr(args, "failure", None),
    }
    return {axis: text for axis, text in values.items() if text}


def cmd_search(args: argparse.Namespace) -> int:
    store = _make_store(args)
    embedder = _make_embedder(args)
    query = ResearchClaim(
        id="query",
        title="",
        statement="",
        record_type=RecordType.HYPOTHESIS.value,
        epistemic_status=EpistemicStatus.UNKNOWN.value,
        domain="",
        axis_texts=_search_axis_texts_from_args(args),
    )
    hits = ResearchIndex(store, embedder).search(query, entity_kind=args.entity_kind, limit=args.limit)
    _json_dump(hits)
    return 0


def cmd_add_claim(args: argparse.Namespace) -> int:
    store = _make_store(args)
    claim = ResearchClaim(
        id=str(uuid.uuid4()),
        external_id=args.external_id,
        title=args.title,
        statement=args.statement,
        record_type=args.record_type,
        epistemic_status=args.epistemic_status,
        domain=args.domain,
        source=args.source,
        axis_texts=_axis_texts_from_args(args),
        metadata=_metadata_from_args(args),
    )
    ResearchIndex(store, _make_embedder(args)).index_claim(claim)
    _json_dump(store.get_research_claim(claim.id).to_dict())
    return 0


def cmd_add_evidence(args: argparse.Namespace) -> int:
    store = _make_store(args)
    metadata = _metadata_from_args(args)
    if args.domain:
        metadata.setdefault("domain", args.domain)
    evidence = Evidence(
        id=str(uuid.uuid4()),
        external_id=args.external_id,
        title=args.title,
        summary=args.summary,
        evidence_type=args.evidence_type,
        epistemic_status=args.epistemic_status,
        source_uri=args.source_uri,
        citation=args.citation,
        axis_texts=_axis_texts_from_args(args),
        metadata=metadata,
    )
    ResearchIndex(store, _make_embedder(args)).index_evidence(evidence)
    _json_dump(store.get_evidence(evidence.id).to_dict())
    return 0


def cmd_link_evidence(args: argparse.Namespace) -> int:
    store = _make_store(args)
    relation_id = store.link_evidence(
        args.claim_id,
        args.evidence_id,
        args.relation,
        metadata=_metadata_from_args(args),
    )
    _json_dump({"id": relation_id})
    return 0


def cmd_link_claim(args: argparse.Namespace) -> int:
    store = _make_store(args)
    relation_id = store.link_claims(
        args.claim_id,
        args.target_claim_id,
        args.relation,
        metadata=_metadata_from_args(args),
    )
    _json_dump({"id": relation_id})
    return 0


def cmd_list_claims(args: argparse.Namespace) -> int:
    store = _make_store(args)
    _json_dump([claim.to_dict() for claim in store.list_research_claims(record_type=args.record_type)])
    return 0


def cmd_list_evidence(args: argparse.Namespace) -> int:
    store = _make_store(args)
    _json_dump([item.to_dict() for item in store.list_evidence()])
    return 0


def cmd_show_claim(args: argparse.Namespace) -> int:
    store = _make_store(args)
    _json_dump(store.get_claim_with_relations(args.claim_id))
    return 0


def cmd_import_research(args: argparse.Namespace) -> int:
    store = _make_store(args)
    data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    result = store.import_research_bundle(data)
    index = ResearchIndex(store, _make_embedder(args))
    for claim_id in result["claims"].values():
        index.index_existing_claim(store.get_research_claim(claim_id))
    for evidence_id in result["evidence"].values():
        index.index_existing_evidence(store.get_evidence(evidence_id))
    _json_dump(result)
    return 0


def cmd_export_research(args: argparse.Namespace) -> int:
    store = _make_store(args)
    data = store.export_research_bundle()
    if args.out:
        Path(args.out).write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"exported {len(data['claims'])} claims, {len(data['evidence'])} evidence, "
              f"{len(data['relations'])} relations to {args.out}")
    else:
        _json_dump(data)
    return 0


def _add_storage_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--store",
        choices=["sqlite", "postgres"],
        default="sqlite",
        help="storage backend; postgres expects pgvector and is Neon-compatible",
    )
    parser.add_argument("--db", default="science.db", help="SQLite database path")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Postgres connection URL; defaults to DATABASE_URL",
    )


def _add_embedding_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--embedder",
        choices=["hash", "openai"],
        default="hash",
        help="embedding backend; hash is deterministic/offline",
    )
    parser.add_argument("--hash-dimensions", type=int, default=128)
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--embedding-dimensions", type=int, default=None)
    parser.add_argument("--embedding-base-url", default=None)
    parser.add_argument("--embedding-api-key-env", default="OPENAI_API_KEY")


def _add_research_content_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mechanism", default=None)
    parser.add_argument("--math-structure", default=None)
    parser.add_argument("--problem-shape", default=None)
    parser.add_argument("--failure", default=None)
    parser.add_argument("--metadata-json", default=None, help="JSON object with additional metadata")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="science-researcher",
        description="Structural analogy and falsification engine for AI-assisted scientific discovery.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize the graph store")
    _add_storage_args(init_parser)
    _add_embedding_args(init_parser)
    init_parser.add_argument("--seed", action="store_true")
    init_parser.set_defaults(func=cmd_init)

    demo_parser = subparsers.add_parser("demo", help="run the deterministic MVP discovery loop")
    _add_storage_args(demo_parser)
    _add_embedding_args(demo_parser)
    demo_parser.add_argument(
        "--problem",
        default="riemann-hypothesis",
        choices=[
            "riemann-hypothesis",
            "navier-stokes",
            "origin-of-life",
            "grokking",
            "problem:riemann-hypothesis",
            "problem:navier-stokes",
            "problem:origin-of-life",
            "problem:grokking",
        ],
    )
    demo_parser.add_argument("--candidates", type=int, default=3)
    demo_parser.add_argument(
        "--provider",
        choices=["heuristic", "openai-compatible"],
        default="heuristic",
        help="reasoning backend; heuristic is deterministic/offline",
    )
    demo_parser.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL")
    demo_parser.add_argument("--model", default="qwen3:8b", help="generator model name")
    demo_parser.add_argument("--critic-model", default=None, help="optional separate critic model")
    demo_parser.add_argument(
        "--api-key-env",
        default="SCIENCE_RESEARCHER_API_KEY",
        help="environment variable containing the reasoning provider API key",
    )
    demo_parser.set_defaults(func=cmd_demo)

    runs_parser = subparsers.add_parser("runs", help="list discovery runs")
    _add_storage_args(runs_parser)
    runs_parser.set_defaults(func=cmd_runs)

    show_parser = subparsers.add_parser("show-run", help="show a persisted discovery trace")
    _add_storage_args(show_parser)
    show_parser.add_argument("--run-id", required=True)
    show_parser.set_defaults(func=cmd_show_run)

    search_parser = subparsers.add_parser(
        "search", help="multi-axis structural search over claims/evidence (mechanism-near, domain-far)"
    )
    _add_storage_args(search_parser)
    _add_embedding_args(search_parser)
    search_parser.add_argument("--entity-kind", choices=["claim", "evidence"], default=None)
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--semantic", default=None, help="free-text semantic query")
    search_parser.add_argument("--domain", default=None)
    search_parser.add_argument("--mechanism", default=None)
    search_parser.add_argument("--math-structure", default=None)
    search_parser.add_argument("--problem-shape", default=None)
    search_parser.add_argument("--failure", default=None, help="known failure mode to penalize overlap with")
    search_parser.set_defaults(func=cmd_search)

    add_claim_parser = subparsers.add_parser("add-claim", help="register a first-class research claim")
    _add_storage_args(add_claim_parser)
    _add_embedding_args(add_claim_parser)
    _add_research_content_args(add_claim_parser)
    add_claim_parser.add_argument("--title", required=True)
    add_claim_parser.add_argument("--statement", required=True)
    add_claim_parser.add_argument("--record-type", choices=[item.value for item in RecordType], required=True)
    add_claim_parser.add_argument(
        "--epistemic-status", choices=[item.value for item in EpistemicStatus], required=True
    )
    add_claim_parser.add_argument("--domain", required=True)
    add_claim_parser.add_argument("--source", default="")
    add_claim_parser.add_argument("--external-id", default=None)
    add_claim_parser.set_defaults(func=cmd_add_claim)

    add_evidence_parser = subparsers.add_parser("add-evidence", help="register independently addressable evidence")
    _add_storage_args(add_evidence_parser)
    _add_embedding_args(add_evidence_parser)
    _add_research_content_args(add_evidence_parser)
    add_evidence_parser.add_argument("--title", required=True)
    add_evidence_parser.add_argument("--summary", required=True)
    add_evidence_parser.add_argument(
        "--evidence-type", choices=[item.value for item in EvidenceType], required=True
    )
    add_evidence_parser.add_argument(
        "--epistemic-status", choices=[item.value for item in EpistemicStatus], required=True
    )
    add_evidence_parser.add_argument("--domain", default="")
    add_evidence_parser.add_argument("--source-uri", default="")
    add_evidence_parser.add_argument("--citation", default="")
    add_evidence_parser.add_argument("--external-id", default=None)
    add_evidence_parser.set_defaults(func=cmd_add_evidence)

    link_evidence_parser = subparsers.add_parser("link-evidence", help="link evidence to a research claim")
    _add_storage_args(link_evidence_parser)
    link_evidence_parser.add_argument("--claim-id", required=True)
    link_evidence_parser.add_argument("--evidence-id", required=True)
    link_evidence_parser.add_argument(
        "--relation", choices=[item.value for item in ResearchRelationType], required=True
    )
    link_evidence_parser.add_argument("--metadata-json", default=None)
    link_evidence_parser.set_defaults(func=cmd_link_evidence)

    link_claim_parser = subparsers.add_parser("link-claim", help="link one research claim to another")
    _add_storage_args(link_claim_parser)
    link_claim_parser.add_argument("--claim-id", required=True)
    link_claim_parser.add_argument("--target-claim-id", required=True)
    link_claim_parser.add_argument(
        "--relation", choices=[item.value for item in ResearchRelationType], required=True
    )
    link_claim_parser.add_argument("--metadata-json", default=None)
    link_claim_parser.set_defaults(func=cmd_link_claim)

    list_claims_parser = subparsers.add_parser("list-claims", help="list registered research claims")
    _add_storage_args(list_claims_parser)
    list_claims_parser.add_argument("--record-type", choices=[item.value for item in RecordType], default=None)
    list_claims_parser.set_defaults(func=cmd_list_claims)

    list_evidence_parser = subparsers.add_parser("list-evidence", help="list registered evidence")
    _add_storage_args(list_evidence_parser)
    list_evidence_parser.set_defaults(func=cmd_list_evidence)

    show_claim_parser = subparsers.add_parser("show-claim", help="show a claim and its outgoing research relations")
    _add_storage_args(show_claim_parser)
    show_claim_parser.add_argument("--claim-id", required=True)
    show_claim_parser.set_defaults(func=cmd_show_claim)

    import_parser = subparsers.add_parser("import-research", help="transactionally import a versioned research bundle")
    _add_storage_args(import_parser)
    _add_embedding_args(import_parser)
    import_parser.add_argument("path")
    import_parser.set_defaults(func=cmd_import_research)

    export_parser = subparsers.add_parser(
        "export-research",
        help="export all claims/evidence/relations from the store as a versioned bundle",
    )
    _add_storage_args(export_parser)
    export_parser.add_argument("--out", default=None, help="write bundle to this path instead of stdout")
    export_parser.set_defaults(func=cmd_export_research)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Load .env from the current directory (and parents) before any store or
    # provider reads DATABASE_URL / API keys. Existing environment variables win.
    load_dotenv()
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
