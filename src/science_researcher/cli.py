from __future__ import annotations

import argparse
import json
import os
import sys

from .embedding_openai import OpenAIEmbeddingProvider
from .embeddings import HashEmbedder
from .provider import HeuristicProvider
from .provider_http import OpenAICompatibleChatProvider
from .service import build_engine, initialize_postgres_store, initialize_store, seed_store


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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
