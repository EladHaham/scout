from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from scout.service import get_repo_map
from scout.utils.errors import ScoutError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scout",
        description="Scout: return an Aider repo map for a git repository.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- map ---
    map_parser = subparsers.add_parser(
        "map",
        help="Generate or load a repo map for a repository.",
    )
    map_parser.add_argument(
        "repo",
        help="Path to a git repository, or to a subdirectory inside one.",
    )
    map_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    map_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore the cache and regenerate the map.",
    )
    map_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not read from or write to the cache.",
    )
    map_parser.add_argument(
        "--out",
        help="Optional file path to write the output to.",
    )

    # --- notes ---
    notes_parser = subparsers.add_parser(
        "notes",
        help="Generate structured notes for all symbols in a repository.",
    )
    notes_parser.add_argument(
        "repo",
        help="Path to a git repository, or to a subdirectory inside one.",
    )
    notes_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Regenerate all notes even if structural hash is unchanged.",
    )

    # --- init ---
    init_parser = subparsers.add_parser(
        "init",
        help="Write a default config file to .scout/config.json for editing.",
    )
    init_parser.add_argument(
        "repo",
        help="Path to a git repository, or to a subdirectory inside one.",
    )
    init_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing config file.",
    )

    # --- context ---
    context_parser = subparsers.add_parser(
        "context",
        help="Retrieve relevant context for a task query.",
    )
    context_parser.add_argument(
        "repo",
        help="Path to a git repository, or to a subdirectory inside one.",
    )
    context_parser.add_argument(
        "query",
        help="Natural language description of the task.",
    )
    context_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of direct symbol matches to retrieve (default: 5).",
    )
    context_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Call graph expansion depth (default: 1).",
    )
    context_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    context_parser.add_argument(
        "--repo-map",
        action="store_true",
        help="Include the repo map in the context packet.",
    )
    context_parser.add_argument(
        "--out",
        help="Optional file path to write the output to.",
    )

    return parser


def _render_text(result) -> str:
    return result.map_text.rstrip() + "\n"


def _render_json(result) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"


def _write_output(payload: str, out: str | None) -> None:
    if out is None:
        sys.stdout.write(payload)
        return

    out_path = Path(out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "map":
            use_cache = not args.no_cache
            result = get_repo_map(
                repo=args.repo,
                use_cache=use_cache,
                refresh=args.refresh,
            )

            if args.format == "json":
                payload = _render_json(result)
            else:
                payload = _render_text(result)

            _write_output(payload, args.out)
            return 0

        if args.command == "notes":
            from scout.adapters.filesystem import normalize_repo_path
            from scout.notes.service import generate_notes
            from scout.retrieval.service import build_retrieval_index

            repo_path = normalize_repo_path(args.repo)
            result = generate_notes(repo_root=repo_path, refresh=args.refresh)
            print(
                f"Notes complete: {result.generated} generated, "
                f"{result.skipped} skipped, "
                f"{result.total} symbols total."
            )

            print("Building embedding index...", end=" ", flush=True)
            indexed = build_retrieval_index(repo_root=repo_path)
            print(f"{indexed} symbols indexed.")
            return 0

        if args.command == "context":
            from scout.adapters.filesystem import normalize_repo_path
            from scout.retrieval.service import get_context

            repo_path = normalize_repo_path(args.repo)
            packet = get_context(
                repo_root=repo_path,
                query=args.query,
                top_k=args.top_k,
                depth=args.depth,
                include_repo_map=args.repo_map,
            )

            if args.format == "json":
                payload = json.dumps(packet.to_dict(), ensure_ascii=False, indent=2) + "\n"
            else:
                payload = packet.to_text()

            _write_output(payload, args.out)
            return 0

        if args.command == "init":
            from scout.adapters.filesystem import normalize_repo_path
            from scout.config import save_default_config

            repo_path = normalize_repo_path(args.repo)
            config_path = save_default_config(repo_path, overwrite=args.overwrite)
            print(f"Config written to {config_path.relative_to(repo_path)}")
            print("Edit it to tune Scout's retrieval behavior.")
            return 0

        parser.error("Unknown command")
        return 2

    except ScoutError as exc:
        print(f"scout error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())