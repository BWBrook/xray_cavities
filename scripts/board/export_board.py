#!/usr/bin/env python3
"""Snapshot this project's correspondence-board threads into the repository.

Reads the board's local HTTP API, applies automatic redactions (addresses,
home paths, e-mail), and fails closed: any message containing a flag term must
be listed in the policy file as either withheld (replaced by a placeholder) or
cleared (published after review). Run with ``--preview DIR`` to write a
review copy that marks flagged messages instead of failing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import yaml

REDACTIONS = [
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "[address]"),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[e-mail]"),
    (re.compile(r"/(?:Users|home|u)/[A-Za-z0-9_.-]+"), "~"),
]


def get(base: str, path: str):
    with urlopen(f"{base}{path}") as response:
        return json.load(response)


def messages(base: str, thread_id: int) -> tuple[dict, list[dict]]:
    out, after = [], 0
    while True:
        page = get(base, f"/api/threads/{thread_id}?after={after}&limit=500&max_bytes=10000000")
        out += page["messages"]
        if not page["has_more"]:
            return page["thread"], out
        after = page["next_after"]


def redact(text: str) -> str:
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def flags(text: str, terms: list[str]) -> list[str]:
    return [t for t in terms if re.search(rf"\b{re.escape(t)}", text, re.IGNORECASE)]


def render(thread: dict, msgs: list[dict], policy: dict, preview: bool) -> tuple[str, list[str]]:
    withheld, cleared = policy.get("withheld") or {}, set(policy.get("cleared") or [])
    lines = [f"# {thread['title']}", "", f"Board discussion {thread['id']}, status {thread['status']}.", ""]
    problems = []
    for m in msgs:
        model = f" ({m['model']})" if m.get("model") else ""
        lines += [f"## Message {m['id']} · {m['author']}{model} · {m['kind']}", "", f"Time: {m['created_at']}"]
        if m.get("parent_id"):
            lines.append(f"Reply to: {m['parent_id']}")
        lines.append("")
        if m["id"] in withheld:
            lines += [f"*Withheld from the public record: {withheld[m['id']]}.*", ""]
            continue
        hits = [] if m["id"] in cleared else flags(m["body"], policy["flag_terms"])
        if hits:
            problems.append(f"thread {thread['id']} message {m['id']}: {', '.join(hits)}")
            if preview:
                lines += [f"> **REVIEW** flagged terms: {', '.join(hits)}", ""]
        lines += [redact(m["body"]).rstrip(), ""]
    return "\n".join(lines), problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=Path("docs/correspondence/publication.yaml"))
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    parser.add_argument("--preview", type=Path, help="write a review copy here instead of failing on flags")
    args = parser.parse_args()
    policy = yaml.safe_load(args.policy.read_text())
    out_dir = args.preview or args.policy.parent
    threads = sorted(get(args.base, f"/api/threads?project_id={policy['project']}&limit=1000"), key=lambda t: t["id"])
    rendered, problems = {}, []
    for thread in threads:
        meta, msgs = messages(args.base, thread["id"])
        rendered[f"thread-{meta['id']:04d}.md"], found = render(meta, msgs, policy, bool(args.preview))
        problems += found
        thread["exported_through"] = msgs[-1]["id"] if msgs else None
    if problems and not args.preview:
        sys.exit("Unreviewed flagged messages; withhold or clear them in the policy file:\n  " + "\n  ".join(problems))
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in rendered.items():
        (out_dir / name).write_text(text)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    index = [f"- [{t['title']}](thread-{t['id']:04d}.md): through message {t['exported_through']}" for t in threads]
    (out_dir / "INDEX.md").write_text(f"# Board snapshot\n\nExported {stamp}.\n\n" + "\n".join(index) + "\n")
    if problems:
        print("\n".join(problems))


if __name__ == "__main__":
    main()
