#!/usr/bin/env python3
"""Tell GitHub Actions whether the newly built dashboard differs from the live site."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from pathlib import Path


def normalized(payload: dict) -> dict:
    copy = json.loads(json.dumps(payload))
    metadata = copy.get("metadata", {})
    metadata.pop("generated_at_utc", None)
    if isinstance(metadata.get("data_sources"), dict):
        metadata["data_sources"].pop("generated_at_utc", None)
    return copy


def digest(payload: dict) -> str:
    encoded = json.dumps(normalized(payload), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", default="site/data/dashboard.json")
    parser.add_argument(
        "--remote",
        default="https://pradeepalphatrader.github.io/india-market-leadership-dashboard/data/dashboard.json",
    )
    args = parser.parse_args()
    local = json.loads(Path(args.local).read_text(encoding="utf-8"))
    deploy = True
    reason = "Live dashboard is unavailable"
    try:
        request = urllib.request.Request(
            f"{args.remote}?check={local['metadata']['generated_at_utc']}",
            headers={"User-Agent": "IndiaMarketLeadershipDashboard/1.0", "Cache-Control": "no-cache"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            remote = json.load(response)
        deploy = digest(local) != digest(remote)
        reason = "Validated dashboard changed" if deploy else "Live dashboard already matches this validated build"
    except Exception as error:
        reason = f"{reason}: {error}"
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"deploy={'true' if deploy else 'false'}\n")
    print(f"deploy={'true' if deploy else 'false'} · {reason}")


if __name__ == "__main__":
    main()
