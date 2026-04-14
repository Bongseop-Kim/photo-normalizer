#!/usr/bin/env python3
"""Photo normalizer CLI entry point."""

from __future__ import annotations

import argparse

from normalizer.cli.run_cmd import add_run_parser
from normalizer.cli.step_cmds import add_step_parsers


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize product photo brightness, position, size, and angle."
    )
    subparsers = parser.add_subparsers(dest="command")
    add_run_parser(subparsers)
    add_step_parsers(subparsers)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        raise SystemExit(1)
    args.func(args)


if __name__ == "__main__":
    main()
