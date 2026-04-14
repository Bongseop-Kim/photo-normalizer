from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

from normalizer.color import step0_color_normalize
from normalizer.config import find_config, load_config
from normalizer.detect import detect_subject
from normalizer.models import ImageRecord, NormalizerConfig
from normalizer.pipeline import _SUFFIXES
from normalizer.transform import step2_rotate, step3_crop_resize, step4_brightness, step5_finalize


def _resolve_inputs(input_path: Path) -> tuple[list[Path], bool]:
    if input_path.is_dir():
        paths = sorted(
            path
            for path in input_path.iterdir()
            if path.is_file() and path.suffix.lower() in _SUFFIXES
        )
        return paths, True
    if input_path.is_file():
        if input_path.suffix.lower() not in _SUFFIXES:
            print(f"Error: not a supported image file: {input_path}", file=sys.stderr)
            raise SystemExit(1)
        return [input_path], False

    print(f"Error: input path does not exist: {input_path}", file=sys.stderr)
    raise SystemExit(1)


def _resolve_output(
    output: Path | None, input_path: Path, step_name: str, is_dir_mode: bool
) -> Path:
    if output is not None:
        return output.resolve()
    if is_dir_mode:
        return (input_path.parent / f"{input_path.name}_{step_name}").resolve()
    return (input_path.parent / f"{input_path.stem}_{step_name}{input_path.suffix}").resolve()


def _prepare_output_dir(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"Error: output directory must be empty: {output_dir}", file=sys.stderr)
        raise SystemExit(1)
    output_dir.mkdir(parents=True, exist_ok=True)


def _load_config_for_step(args: argparse.Namespace, input_path: Path) -> NormalizerConfig:
    search_dir = input_path if input_path.is_dir() else input_path.parent
    try:
        config_path = find_config(search_dir, explicit=getattr(args, "config", None))
    except FileNotFoundError as exc:
        raise SystemExit(f"Error: invalid --config path: {args.config}") from exc

    overrides: dict[str, object] = {}
    if getattr(args, "target_ratio", None) is not None:
        overrides["target_ratio"] = args.target_ratio
    if getattr(args, "no_angle", False):
        overrides["angle_enabled"] = False
    if getattr(args, "morphology", False):
        overrides["morphology_enabled"] = True
    if getattr(args, "morph_kernel", None) is not None:
        overrides["morphology_kernel_size"] = args.morph_kernel
    if getattr(args, "dry_run", False):
        overrides["dry_run"] = True

    return load_config(config_path=config_path, overrides=overrides)


def _add_step0_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("step0", help="Step 0: color normalize (sRGB, ICC, EXIF)")
    parser.add_argument("input", type=Path, help="Image file or directory")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.set_defaults(func=cmd_step0)


def cmd_step0(args: argparse.Namespace) -> None:
    input_path = args.input.resolve()
    config = _load_config_for_step(args, input_path)
    inputs, is_dir_mode = _resolve_inputs(input_path)
    output = _resolve_output(args.output, input_path, "step0", is_dir_mode)

    if is_dir_mode:
        _prepare_output_dir(output)
        errors: list[tuple[str, str]] = []
        for src in inputs:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / src.name
                shutil.copy2(src, tmp_path)
                record = ImageRecord(
                    source_path=src,
                    work_path=tmp_path,
                    config=config,
                )
                try:
                    step0_color_normalize(record)
                    shutil.copy2(record.work_path, output / src.name)
                except Exception as exc:
                    errors.append((src.name, str(exc)))
        print(f"\nDone: {len(inputs) - len(errors)} processed, {len(errors)} failed")
        for name, error in errors:
            print(f"  SKIP {name}: {error}", file=sys.stderr)
        return

    src = inputs[0]
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / src.name
        shutil.copy2(src, tmp_path)
        record = ImageRecord(
            source_path=src,
            work_path=tmp_path,
            config=config,
        )
        try:
            step0_color_normalize(record)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record.work_path, output)
            print(f"Output: {output}")
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc


def _add_step1_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("step1", help="Step 1: detect subject (bbox, angle, brightness)")
    parser.add_argument("input", type=Path, help="Image file or directory")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--morphology", action="store_true")
    parser.add_argument("--morph-kernel", type=int, default=None)
    parser.set_defaults(func=cmd_step1)


def cmd_step1(args: argparse.Namespace) -> None:
    input_path = args.input.resolve()
    config = _load_config_for_step(args, input_path)
    inputs, is_dir_mode = _resolve_inputs(input_path)
    output = _resolve_output(args.output, input_path, "step1", is_dir_mode)

    if is_dir_mode:
        _prepare_output_dir(output)
        image_data: list[dict[str, object]] = []
        for src in inputs:
            result = detect_subject(
                src,
                morphology_enabled=config.morphology_enabled,
                morphology_kernel_size=config.morphology_kernel_size,
                corner_sample_size=config.corner_sample_size,
            )
            if result is None:
                print(f"  WARN {src.name}: subject not detected", file=sys.stderr)
                continue
            shutil.copy2(src, output / src.name)
            bbox, angle, brightness = result
            image_data.append(
                {
                    "file": src.name,
                    "bbox": list(bbox),
                    "angle": round(angle, 2),
                    "brightness": round(brightness, 2),
                }
            )

        angles = [entry["angle"] for entry in image_data]
        brightnesses = [entry["brightness"] for entry in image_data]
        batch = {
            "reference_angle": round(statistics.median(angles), 2) if angles else 0.0,
            "reference_brightness": round(statistics.median(brightnesses), 2)
            if brightnesses
            else 245.0,
        }
        measurements = {"images": image_data, "batch": batch}
        (output / "_measurements.json").write_text(json.dumps(measurements, indent=2))
        print(f"\nDetected: {len(image_data)} images")
        print(f"Reference angle:      {batch['reference_angle']}")
        print(f"Reference brightness: {batch['reference_brightness']}")
        return

    src = inputs[0]
    result = detect_subject(
        src,
        morphology_enabled=config.morphology_enabled,
        morphology_kernel_size=config.morphology_kernel_size,
        corner_sample_size=config.corner_sample_size,
    )
    if result is None:
        print(f"Error: subject not detected in {src}", file=sys.stderr)
        raise SystemExit(1)

    bbox, angle, brightness = result
    if args.output is not None:
        data = {
            "images": [
                {
                    "file": src.name,
                    "bbox": list(bbox),
                    "angle": round(angle, 2),
                    "brightness": round(brightness, 2),
                }
            ],
            "batch": {
                "reference_angle": round(angle, 2),
                "reference_brightness": round(brightness, 2),
            },
        }
        args.output.write_text(json.dumps(data, indent=2))
        return

    print(f"file: {src.name}")
    print(f"bbox: {list(bbox)}")
    print(f"angle: {round(angle, 2):.2f}")
    print(f"brightness: {round(brightness, 2):.2f}")


def _add_step2_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("step2", help="Step 2: angle correction")
    parser.add_argument("input", type=Path, help="Image file or directory")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--reference-angle", type=float, required=True)
    parser.add_argument("--no-angle", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.set_defaults(func=cmd_step2)


def cmd_step2(args: argparse.Namespace) -> None:
    input_path = args.input.resolve()
    config = _load_config_for_step(args, input_path)
    inputs, is_dir_mode = _resolve_inputs(input_path)
    output = _resolve_output(args.output, input_path, "step2", is_dir_mode)

    if is_dir_mode:
        _prepare_output_dir(output)
        errors: list[tuple[str, str]] = []
        for src in inputs:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / src.name
                shutil.copy2(src, tmp_path)
                record = ImageRecord(
                    source_path=src,
                    work_path=tmp_path,
                    config=config,
                )
                try:
                    step2_rotate(record, reference_angle=args.reference_angle)
                    shutil.copy2(record.work_path, output / src.name)
                except Exception as exc:
                    errors.append((src.name, str(exc)))
        print(f"\nDone: {len(inputs) - len(errors)} processed, {len(errors)} failed")
        for name, error in errors:
            print(f"  SKIP {name}: {error}", file=sys.stderr)
        return

    src = inputs[0]
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / src.name
        shutil.copy2(src, tmp_path)
        record = ImageRecord(
            source_path=src,
            work_path=tmp_path,
            config=config,
        )
        try:
            step2_rotate(record, reference_angle=args.reference_angle)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record.work_path, output)
            print(f"Output: {output}")
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc


def _parse_bbox(bbox_str: str) -> tuple[int, int, int, int]:
    try:
        x, y, w, h = (int(value.strip()) for value in bbox_str.split(","))
        return x, y, w, h
    except ValueError as exc:
        print(f"Error: --bbox must be X,Y,W,H integers, got: {bbox_str!r}", file=sys.stderr)
        raise SystemExit(1) from exc


def _get_bbox(
    image_path: Path, bbox_override: tuple[int, int, int, int] | None, config: NormalizerConfig
) -> tuple[int, int, int, int]:
    if bbox_override is not None:
        return bbox_override

    result = detect_subject(
        image_path,
        morphology_enabled=config.morphology_enabled,
        morphology_kernel_size=config.morphology_kernel_size,
        corner_sample_size=config.corner_sample_size,
    )
    if result is None:
        raise RuntimeError(f"Subject detection failed for {image_path}")
    return result[0]


def _add_step3_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("step3", help="Step 3: crop and resize")
    parser.add_argument("input", type=Path, help="Image file or directory")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--bbox", type=str, default=None, metavar="X,Y,W,H")
    parser.add_argument("--target-ratio", type=float, default=None)
    parser.add_argument("--morphology", action="store_true")
    parser.add_argument("--morph-kernel", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.set_defaults(func=cmd_step3)


def cmd_step3(args: argparse.Namespace) -> None:
    input_path = args.input.resolve()
    config = _load_config_for_step(args, input_path)
    inputs, is_dir_mode = _resolve_inputs(input_path)
    output = _resolve_output(args.output, input_path, "step3", is_dir_mode)
    bbox_override = _parse_bbox(args.bbox) if args.bbox else None

    if is_dir_mode:
        _prepare_output_dir(output)
        errors: list[tuple[str, str]] = []
        for src in inputs:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / src.name
                shutil.copy2(src, tmp_path)
                record = ImageRecord(
                    source_path=src,
                    work_path=tmp_path,
                    config=config,
                )
                try:
                    bbox = _get_bbox(tmp_path, bbox_override, config)
                    step3_crop_resize(record, bbox=bbox)
                    shutil.copy2(record.work_path, output / src.name)
                except Exception as exc:
                    errors.append((src.name, str(exc)))
        print(f"\nDone: {len(inputs) - len(errors)} processed, {len(errors)} failed")
        for name, error in errors:
            print(f"  SKIP {name}: {error}", file=sys.stderr)
        return

    src = inputs[0]
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / src.name
        shutil.copy2(src, tmp_path)
        record = ImageRecord(
            source_path=src,
            work_path=tmp_path,
            config=config,
        )
        try:
            bbox = _get_bbox(tmp_path, bbox_override, config)
            step3_crop_resize(record, bbox=bbox)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record.work_path, output)
            print(f"Output: {output}")
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc


def _add_step4_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("step4", help="Step 4: brightness equalization")
    parser.add_argument("input", type=Path, help="Image file or directory")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--reference-brightness", type=float, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.set_defaults(func=cmd_step4)


def cmd_step4(args: argparse.Namespace) -> None:
    input_path = args.input.resolve()
    config = _load_config_for_step(args, input_path)
    inputs, is_dir_mode = _resolve_inputs(input_path)
    output = _resolve_output(args.output, input_path, "step4", is_dir_mode)

    if is_dir_mode:
        _prepare_output_dir(output)
        errors: list[tuple[str, str]] = []
        for src in inputs:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / src.name
                shutil.copy2(src, tmp_path)
                record = ImageRecord(
                    source_path=src,
                    work_path=tmp_path,
                    config=config,
                )
                try:
                    step4_brightness(record, reference_bg=args.reference_brightness)
                    shutil.copy2(record.work_path, output / src.name)
                except Exception as exc:
                    errors.append((src.name, str(exc)))
        print(f"\nDone: {len(inputs) - len(errors)} processed, {len(errors)} failed")
        for name, error in errors:
            print(f"  SKIP {name}: {error}", file=sys.stderr)
        return

    src = inputs[0]
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / src.name
        shutil.copy2(src, tmp_path)
        record = ImageRecord(
            source_path=src,
            work_path=tmp_path,
            config=config,
        )
        try:
            step4_brightness(record, reference_bg=args.reference_brightness)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record.work_path, output)
            print(f"Output: {output}")
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc


def _add_step5_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("step5", help="Step 5: finalize (white canvas, ICC embed)")
    parser.add_argument("input", type=Path, help="Image file or directory")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.set_defaults(func=cmd_step5)


def cmd_step5(args: argparse.Namespace) -> None:
    input_path = args.input.resolve()
    config = _load_config_for_step(args, input_path)
    inputs, is_dir_mode = _resolve_inputs(input_path)
    output = _resolve_output(args.output, input_path, "step5", is_dir_mode)

    if is_dir_mode:
        _prepare_output_dir(output)
        errors: list[tuple[str, str]] = []
        for src in inputs:
            record = ImageRecord(
                source_path=src,
                work_path=src,
                config=config,
            )
            dest = output / src.name
            try:
                step5_finalize(record, output_path=dest)
            except Exception as exc:
                errors.append((src.name, str(exc)))
        print(f"\nDone: {len(inputs) - len(errors)} processed, {len(errors)} failed")
        for name, error in errors:
            print(f"  SKIP {name}: {error}", file=sys.stderr)
        return

    src = inputs[0]
    record = ImageRecord(
        source_path=src,
        work_path=src,
        config=config,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        step5_finalize(record, output_path=output)
        print(f"Output: {output}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def add_step_parsers(subparsers: argparse._SubParsersAction) -> None:
    _add_step0_parser(subparsers)
    _add_step1_parser(subparsers)
    _add_step2_parser(subparsers)
    _add_step3_parser(subparsers)
    _add_step4_parser(subparsers)
    _add_step5_parser(subparsers)
