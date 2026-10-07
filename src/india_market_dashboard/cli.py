from __future__ import annotations

import argparse
from pathlib import Path
from .pipeline import publish_site, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the India Market Leadership & Breadth dashboard")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--project-root", default=".")
    build.add_argument("--history-dir", required=True)
    build.add_argument("--classification-file", required=True)
    build.add_argument("--demo", action="store_true")
    publish = subparsers.add_parser("publish")
    publish.add_argument("--project-root", default=".")
    publish.add_argument("--destination", default="build")
    args = parser.parse_args()
    if args.command == "build":
        dashboard = run_pipeline(Path(args.project_root), args.history_dir, args.classification_file, demo=args.demo)
        state = "PUBLISHABLE" if dashboard["metadata"]["publishable"] else "BLOCKED"
        print(f"Dashboard build complete: {state}")
    else:
        publish_site(args.project_root, args.destination)
        print(f"Validated site copied to {args.destination}")


if __name__ == "__main__":
    main()
