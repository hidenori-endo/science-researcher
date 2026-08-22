#!/usr/bin/env python3
"""Mirror research-store claims to GitHub issues (1 claim = 1 issue).

- Each claim gets one issue labeled by its record type.
- The issue body renders the human-readable card (statement, axes,
  metadata, evidence, relation links) and ends with a fenced JSON
  payload so the issue alone is sufficient to reconstruct the claim.
- Idempotent: existing issues are found via the claim external_id in
  the issue body and updated in place.

Usage: scripts/sync-issues.py [--store postgres]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LABELS = {
    "known_result": ("claim/known-result", "Established result / breakthrough card", "0e8a16"),
    "conjecture": ("claim/open-problem", "Open problem / conjecture card", "d93f0b"),
    "hypothesis": ("claim/hypothesis", "Speculative cross-domain hypothesis", "5319e7"),
    "methodological_lesson": ("claim/precedent", "Cross-field methodological precedent", "fbca04"),
}
MARKER = "science-researcher:claim-payload v1"
TESTABILITY_LABELS = {
    "formal": ("testability/formal", "Agent-provable / computationally falsifiable", "0e8a16"),
    "simulable": ("testability/simulable", "Hypothesis-checkable via reduced simulations", "1d76db"),
    "empirical": ("testability/empirical", "Resolution requires experiments/observations; not planned for agent work", "b60205"),
}


def apply_testability_labels(num: int, claim: dict) -> None:
    meta = claim.get("metadata") or {}
    tag = meta.get("agent_testability")
    labels = []
    if tag in TESTABILITY_LABELS:
        labels.append(TESTABILITY_LABELS[tag][0])
    if meta.get("planned") is False:
        labels.append("not-planned")
        subprocess.run(["gh", "label", "create", "not-planned",
                        "--description", "Deprioritized per research policy", "--color", "cccccc"],
                       capture_output=True)
    if labels:
        subprocess.run(["gh", "issue", "edit", str(num), "--add-label", ",".join(labels)],
                       capture_output=True, text=True)


def gh(*args: str, input: str | None = None) -> str:
    proc = subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True, input=input
    )
    return proc.stdout.strip()


def ensure_labels() -> None:
    for name, desc, color in LABELS.values():
        subprocess.run(
            ["gh", "label", "create", name, "--description", desc, "--color", color],
            capture_output=True,
        )
    for name, desc, color in TESTABILITY_LABELS.values():
        subprocess.run(
            ["gh", "label", "create", name, "--description", desc, "--color", color],
            capture_output=True,
        )


def load_bundle(store: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
        path = fh.name
    subprocess.run(
        ["uv", "run", "science-researcher", "export-research", "--store", store, "--out", path],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    )
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_issue(external_id: str) -> int | None:
    """Locate the mirror issue by scanning all issues once.

    GitHub's search API tokenizes hyphens/colons and may skip HTML
    comments, so text search is unreliable for our marker. A full scan
    is one or two API calls and exact.
    """
    for num, body in scan_issue_bodies():
        if f"science-researcher:claim-id {external_id}" in body:
            return num
    return None


_SCAN_CACHE: list[tuple[int, str]] | None = None


def scan_issue_bodies() -> list[tuple[int, str]]:
    global _SCAN_CACHE
    if _SCAN_CACHE is None:
        out = gh(
            "api", "repos/{owner}/{repo}/issues?state=all&per_page=100",
            "--paginate", "--jq",
            '.[] | [.number, (.body // "")]',
        )
        _SCAN_CACHE = [
            (int(num), body)
            for num, body in (json.loads(line) for line in out.splitlines() if line.strip())
        ]
    return _SCAN_CACHE


def render_body(claim: dict, evidence_items: list[dict], relations: list[dict], issue_no: int | None) -> str:
    lines: list[str] = []
    lines.append(f"<!-- science-researcher:claim-id {claim['external_id']} -->")
    lines.append("")
    lines.append(f"`{claim['external_id']}`")
    lines.append("")
    lines.append(f"**{claim['statement']}**")
    lines.append("")
    lines.append(f"- record_type: `{claim['record_type']}`")
    lines.append(f"- epistemic_status: `{claim['epistemic_status']}`")
    lines.append(f"- domain: {claim['domain']}")
    meta = claim.get("metadata") or {}
    if meta:
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        for key, value in meta.items():
            if isinstance(value, (dict, list)):
                value = f"`{json.dumps(value, ensure_ascii=False)}`"
            elif isinstance(value, bool):
                value = "`true`" if value else "`false`"
            lines.append(f"- {key}: {value}")
    axes = {k: v for k, v in (claim.get("axis_texts") or {}).items() if v}
    if axes:
        lines.append("")
        lines.append("## Axes")
        lines.append("")
        for key, value in axes.items():
            lines.append(f"- **{key}**: {value}")

    supported = [r for r in relations if r.get("target_claim") == claim["external_id"] and r.get("evidence")]
    outgoing = [r for r in relations if r["claim"] == claim["external_id"]]
    incoming = [r for r in relations if r.get("target_claim") == claim["external_id"] and not r.get("evidence")]

    if supported:
        lines.append("")
        lines.append("## Evidence")
        for rel in supported:
            ev = evidence_items.get(rel["evidence"])
            if not ev:
                continue
            lines.append(f"- **{ev['title']}** ({rel['relation']}): {ev['summary']}")
            if ev.get("citation"):
                lines.append(f"  - {ev['citation']}")
            if ev.get("source_uri"):
                lines.append(f"  - {ev['source_uri']}")
    if outgoing:
        lines.append("")
        lines.append("## Outgoing relations")
        for rel in outgoing:
            target = rel.get("target_claim") or rel.get("evidence")
            num = issue_no(target) if issue_no else None
            ref = f" #{num}" if num else ""
            lines.append(f"- {rel['relation']} -> `{target}`{ref}")
    if incoming:
        lines.append("")
        lines.append("## Incoming relations")
        for rel in incoming:
            num = issue_no(rel["claim"]) if issue_no else None
            ref = f" #{num}" if num else None
            suffix = f" (#{num})" if num else ""
            lines.append(f"- {rel['relation']} <- `{rel['claim']}`{suffix}")

    lines.append("")
    lines.append("---")
    lines.append(f"<!-- {MARKER} -->")
    lines.append("```json")
    lines.append(json.dumps(claim, ensure_ascii=False, indent=2, sort_keys=True))
    lines.append("```")
    return "\n".join(lines) + "\n"


ISSUE_MAP: dict[str, int] = {}
NODE_ID_CACHE: dict[int, str] = {}


def issue_no(external_id: str) -> int | None:
    return ISSUE_MAP.get(external_id)


def node_id(num: int) -> str:
    if num not in NODE_ID_CACHE:
        NODE_ID_CACHE[num] = gh("issue", "view", str(num), "--json", "id", "-q", ".id")
    return NODE_ID_CACHE[num]


def link_sub_issue(parent_num: int, child_num: int) -> bool:
    query = (
        'mutation($p:ID!,$c:ID!){ addSubIssue(input:{issueId:$p, subIssueId:$c})'
        ' { issue { number } } }'
    )
    proc = subprocess.run(
        ["gh", "api", "graphql",
         "-f", f"query={query}",
         "-f", f"p={node_id(parent_num)}",
         "-f", f"c={node_id(child_num)}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        msg = (proc.stderr or "").lower()
        if "already" in msg or "sub-issue" in msg:
            return False
        print(f"warn: addSubIssue #{parent_num}<-#{child_num}: {(proc.stderr or '').strip()[:200]}", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="postgres", choices=["postgres", "sqlite"])
    args = parser.parse_args()

    ensure_labels()
    bundle = load_bundle(args.store)
    claims = bundle["claims"]
    evidence_items = {e["external_id"]: e for e in bundle["evidence"]}
    relations = bundle["relations"]

    # Pass 1: locate or create one issue per claim.
    for claim in claims:
        ext = claim["external_id"]
        num = find_issue(ext)
        if num is None:
            label = LABELS[claim["record_type"]][0]
            url = gh(
                "issue", "create",
                "--title", f"[{claim['record_type']}] {claim['title']}",
                "--body", f"(syncing) `{ext}`",
                "--label", label,
            )
            num = int(url.rsplit("/", 1)[-1])
            print(f"created #{num} for {ext}")
        ISSUE_MAP[ext] = num

    # Pass 2: render final bodies with resolved cross-links.
    created_or_updated = 0
    for claim in claims:
        ext = claim["external_id"]
        num = ISSUE_MAP[ext]
        body = render_body(claim, evidence_items, relations, issue_no)
        title = f"[{claim['record_type']}] {claim['title']}"
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write(body)
            body_path = fh.name
        gh("issue", "edit", str(num), "--title", title, "--body-file", body_path)
        Path(body_path).unlink(missing_ok=True)
        apply_testability_labels(num, claim)
        created_or_updated += 1
    print(f"synced {created_or_updated} claim issues")

    # Pass 3: hierarchy - open problems are parents; hypotheses and
    # cross-field precedents targeting a problem become its sub-issues.
    linked = 0
    for claim in claims:
        meta = claim.get("metadata") or {}
        parent_ext = meta.get("target_problem")
        if not parent_ext:
            continue
        if claim["record_type"] not in ("hypothesis", "methodological_lesson"):
            continue
        parent_num = ISSUE_MAP.get(parent_ext)
        child_num = ISSUE_MAP[claim["external_id"]]
        if parent_num is None or parent_num == child_num:
            continue
        if link_sub_issue(parent_num, child_num):
            linked += 1
    print(f"linked {linked} sub-issues under open-problem parents")


    # Evidence without a supporting claim relation would be orphaned;
    # every current evidence row is linked, so assert that invariant.
    linked = {r["evidence"] for r in relations if r.get("evidence")}
    orphans = set(evidence_items) - linked
    if orphans:
        print(f"warning: evidence without SUPPORTS link (not mirrored): {sorted(orphans)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
