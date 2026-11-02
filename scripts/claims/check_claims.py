#!/usr/bin/env python3
"""Validate the claims ledger and the claim citations in written products.

Checks schema and status vocabulary, unique IDs, references between claims,
that each evidence path exists in its pinned commit, and that every
``<!-- claims: ID ... -->`` citation in a product names a real claim. The
article and the brief may cite only supported, provisional or open claims;
the agent guide may cite any, because dead ends are part of its job.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

STATUSES = {"supported", "provisional", "open", "refuted", "withdrawn", "superseded"}
CITABLE = {"supported", "provisional", "open"}
REQUIRED = {"id", "status", "statement", "evidence"}
ID = re.compile(r"^[A-Z]+-\d{2}$")
CITATION = re.compile(r"<!--\s*claims:\s*([^>]*?)\s*-->")
PRODUCTS = {
    "manuscript/text/main.md": CITABLE,
    "manuscript/text/brief.md": CITABLE,
    "AGENT_GUIDE.md": STATUSES,
}


def in_commit(root: Path, commit: str, path: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"], cwd=root, capture_output=True
    ).returncode == 0


def check(root: Path) -> list[str]:
    ledger = yaml.safe_load((root / "claims/claims.yaml").read_text())
    claims = ledger["claims"]
    errors, status = [], {}
    for c in claims:
        cid = c.get("id", "?")
        if missing := REQUIRED - c.keys():
            errors.append(f"{cid}: missing {sorted(missing)}")
        if not ID.match(cid):
            errors.append(f"{cid}: ID must look like ABC-01")
        if cid in status:
            errors.append(f"{cid}: duplicate ID")
        if c.get("status") not in STATUSES:
            errors.append(f"{cid}: unknown status {c.get('status')!r}")
        if c.get("status") in {"open", "provisional"} and not c.get("test"):
            errors.append(f"{cid}: {c['status']} claims need a test")
        if c.get("status") == "superseded" and not c.get("superseded_by"):
            errors.append(f"{cid}: superseded claims need superseded_by")
        for e in c.get("evidence", []):
            if not in_commit(root, e["commit"], e["path"]):
                errors.append(f"{cid}: {e['path']} not found at {e['commit']}")
        status[cid] = c.get("status")
    for c in claims:
        for ref in c.get("depends_on", []) + ([c["superseded_by"]] if c.get("superseded_by") else []):
            if ref not in status:
                errors.append(f"{c['id']}: refers to unknown claim {ref}")
    for product, allowed in PRODUCTS.items():
        path = root / product
        if not path.exists():
            continue
        for match in CITATION.finditer(path.read_text()):
            for cid in re.split(r"[\s,]+", match.group(1).strip()):
                if cid not in status:
                    errors.append(f"{product}: cites unknown claim {cid}")
                elif status[cid] not in allowed:
                    errors.append(f"{product}: cites {cid}, which is {status[cid]}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    errors = check(parser.parse_args().root)
    if errors:
        sys.exit("\n".join(errors))
    print("claims ledger OK")


if __name__ == "__main__":
    main()
