#!/usr/bin/env python3
"""Validate the claims ledger and the claim citations in written products.

Checks schema and status vocabulary, unique IDs, references between claims,
that each evidence path exists in its pinned commit, and that claim citations
in the article, brief and guide agree with the ledger. Publication figures
must cite their claims. --strict requires supported claims in the sources
used by the submission profile.
"""

from __future__ import annotations

import argparse
import json
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
MARKDOWN_READER = "markdown+yaml_metadata_block+tex_math_dollars+tex_math_single_backslash"


def in_commit(root: Path, commit: str, path: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"], cwd=root, capture_output=True
    ).returncode == 0


def publication_sources(root: Path, strict: bool) -> dict[Path, set[str]]:
    sources = {}
    for config in ("build.yaml", "native_energy_brief.yaml"):
        settings = root / "settings" / config
        profiles = yaml.safe_load(settings.read_text())["profiles"]
        for name, profile in profiles.items():
            allowed = {"supported"} if strict and name == "submission" else CITABLE
            for source in profile["manuscript_sources"]:
                path = (settings.parent / source).resolve().relative_to(root)
                sources[path] = sources.get(path, CITABLE) & allowed
    return sources


def elements(value):
    if isinstance(value, dict):
        yield value
        yield from elements(value.get("c"))
    elif isinstance(value, list):
        for item in value:
            yield from elements(item)


def publication_citations(path: Path, product: Path, errors: list[str]) -> list[str]:
    # Use the same Markdown reader as the renderer. Commented plots and code
    # examples never become images in the document.
    parsed = subprocess.run(
        ["pandoc", "--from", MARKDOWN_READER, "--to=json", str(path)], capture_output=True, text=True,
    )
    if parsed.returncode:
        errors.append(f"{product}: Pandoc could not read this source: {parsed.stderr.strip()}")
        return []
    blocks = json.loads(parsed.stdout)["blocks"]
    citations = []
    for i, block in enumerate(blocks):
        for node in elements(block):
            kind = node.get("t")
            if kind in ("RawBlock", "RawInline") and node["c"][0] == "html":
                citations.extend(CITATION.findall(node["c"][1]))
            if kind == "Image":
                following = blocks[i + 1] if i + 1 < len(blocks) else {}
                if not (block["t"] == "Figure" and following.get("t") == "RawBlock"
                        and following["c"][0] == "html" and CITATION.fullmatch(following["c"][1].strip())):
                    image_path = node["c"][2][0]
                    errors.append(f"{product}: {image_path} needs a separate figure paragraph "
                                  "followed by its own <!-- claims: ... --> paragraph")
    return citations


def check(root: Path, strict: bool = False) -> list[str]:
    root = root.resolve()
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
    publications = publication_sources(root, strict)
    for product, allowed in {**publications, Path("AGENT_GUIDE.md"): STATUSES}.items():
        path = root / product
        if not path.is_file():
            errors.append(f"Missing product source: {product}")
            continue
        citations = (publication_citations(path, product, errors) if product in publications
                     else CITATION.findall(path.read_text()))
        cited = set()
        for group in citations:
            ids = group.replace(",", " ").split()
            if not ids:
                errors.append(f"{product}: empty claim citation")
            cited.update(ids)
        for cid in sorted(cited):
            if cid not in status:
                errors.append(f"{product}: cites unknown claim {cid}")
            elif status[cid] not in allowed:
                errors.append(f"{product}: cites {cid}, which is {status[cid]}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--strict", action="store_true",
                        help="require supported claims in every source used by the submission profile")
    args = parser.parse_args()
    errors = check(args.root, strict=args.strict)
    if errors:
        sys.exit("\n".join(errors))
    print("claims ledger OK")


if __name__ == "__main__":
    main()
