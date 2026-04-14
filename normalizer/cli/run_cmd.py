from __future__ import annotations

import argparse
import sys
from pathlib import Path

from normalizer.config import find_config, load_config
from normalizer.pipeline import run_pipeline


def add_run_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("run", help="Run the full normalization pipeline")
    parser.add_argument("input_dir", type=Path, help="Folder containing input images")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--target-ratio", type=float, default=None)
    parser.add_argument("--fuzz", type=str, default=None)
    parser.add_argument("--no-angle", action="store_true")
    parser.add_argument("--morphology", action="store_true")
    parser.add_argument("--morph-kernel", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.set_defaults(func=run_main)


def run_main(args: argparse.Namespace) -> None:
    input_dir = args.input_dir.resolve()
    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        raise SystemExit(1)

    output_dir = (args.output or input_dir / "normalized").resolve()
    if args.output is not None and output_dir == input_dir:
        raise SystemExit("Error: output directory must be different from input directory")

    try:
        config_path = find_config(input_dir, explicit=args.config)
    except FileNotFoundError as exc:
        raise SystemExit(f"Error: invalid --config path: {args.config}") from exc

    overrides = {
        key: value
        for key, value in {
            "target_ratio": args.target_ratio,
            "trim_fuzz": args.fuzz,
            "angle_enabled": False if args.no_angle else None,
            "morphology_enabled": True if args.morphology else None,
            "morphology_kernel_size": args.morph_kernel,
            "dry_run": True if args.dry_run else None,
        }.items()
        if value is not None
    }

    config = load_config(config_path=config_path, overrides=overrides)

    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Config: {config_path or 'built-in defaults'}")
    if config.dry_run:
        print("Mode:   dry-run")

    result = run_pipeline(input_dir=input_dir, output_dir=output_dir, config=config)
    successes = [record for record in result.records if not record.error]
    failures = [record for record in result.records if record.error]

    print(f"\nDone: {len(successes)} processed, {len(failures)} skipped")
    for record in failures:
        print(f"  SKIP {record.source_path.name}: {record.error}")
    print(f"\nReport:  {output_dir / '_report.json'}")
    if not config.dry_run:
        print(f"Preview: {output_dir / '_preview.html'}")

