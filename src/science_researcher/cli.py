from __future__ import annotations

import argparse
import json
import sys

from .provider import HeuristicProvider
from .provider_http import OpenAICompatibleChatProvider
from .service import build_engine, initialize_store, seed_store


def _json_dump(value: object) -> None:
    json.dump(value, sys.stdout, indent=2, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


def cmd_init(args: argparse.Namespace) -> int:
    store = initialize_store(args.db)
    if args.seed:
        seed_store(store)
    print(f"initialized {args.db}")
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
    store = initialize_store(args.db)
    seed_store(store)
    problem_id = args.problem if args.problem.startswith("problem:") else f"problem:{args.problem}"
    result = build_engine(
        store,
        generator=_make_provider(args, critic=False),
        critic=_make_provider(args, critic=True),
    ).run(problem_id, candidates_per_reframing=args.candidates)
    _json_dump(result)
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    store = initialize_store(args.db)
    _json_dump(store.list_runs())
    return 0


def cmd_show_run(args: argparse.Namespace) -> int:
    store = initialize_store(args.db)
    _json_dump(store.get_run(args.run_id))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="science-researcher",
        description="Structural analogy and falsification engine for AI-assisted scientific discovery.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize the graph store")
    init_parser.add_argument("--db", default="science.db")
    init_parser.add_argument("--seed", action="store_true")
    init_parser.set_defaults(func=cmd_init)

    demo_parser = subparsers.add_parser("demo", help="run the deterministic MVP discovery loop")
    demo_parser.add_argument("--db", default="science.db")
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
        help="environment variable containing the provider API key",
    )
    demo_parser.set_defaults(func=cmd_demo)

    runs_parser = subparsers.add_parser("runs", help="list discovery runs")
    runs_parser.add_argument("--db", default="science.db")
    runs_parser.set_defaults(func=cmd_runs)

    show_parser = subparsers.add_parser("show-run", help="show a persisted discovery trace")
    show_parser.add_argument("--db", default="science.db")
    show_parser.add_argument("--run-id", required=True)
    show_parser.set_defaults(func=cmd_show_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
