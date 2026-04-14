from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from normalizer.models import ImageRecord, NormalizerConfig
from normalizer.transform import _run, step2_rotate, step3_crop_resize, step4_brightness, step5_finalize


def _record(tmp_path) -> ImageRecord:
    source = tmp_path / "source.jpg"
    source.touch()
    work = tmp_path / "work.jpg"
    work.touch()
    return ImageRecord(
        source_path=source,
        work_path=work,
        config=NormalizerConfig(),
        measurements={},
        warnings=[],
    )


def test_step4_level_uses_reference_background(tmp_path, monkeypatch):
    record = _record(tmp_path)
    record.measurements["original_brightness_mean"] = 230.0
    commands: list[list[str]] = []

    monkeypatch.setattr("normalizer.transform._run", lambda cmd: commands.append(cmd))

    step4_brightness(record, reference_bg=245.0)

    assert commands
    assert commands[0][2] == "-level"
    assert commands[0][3] == "0%,93.88%"


def test_step4_level_allows_white_point_above_100(tmp_path, monkeypatch):
    record = _record(tmp_path)
    record.measurements["original_brightness_mean"] = 250.0
    commands: list[list[str]] = []

    monkeypatch.setattr("normalizer.transform._run", lambda cmd: commands.append(cmd))

    step4_brightness(record, reference_bg=200.0)

    assert commands
    assert commands[0][2] == "-level"
    assert commands[0][3] == "0%,125.00%"


def test_step4_level_handles_zero_reference_background(tmp_path, monkeypatch):
    record = _record(tmp_path)
    record.measurements["original_brightness_mean"] = 25.0
    commands: list[list[str]] = []

    monkeypatch.setattr("normalizer.transform._run", lambda cmd: commands.append(cmd))

    step4_brightness(record, reference_bg=0.0)

    assert commands
    assert commands[0][2] == "-level"
    assert commands[0][3] == "0%,0.00%"


def test_step5_finalize_respects_strip_and_preserve_flags(tmp_path, monkeypatch):
    record = _record(tmp_path)
    record.config.strip_exif = False
    record.config.preserve_icc = False
    commands: list[list[str]] = []

    monkeypatch.setattr("normalizer.transform._run", lambda cmd: commands.append(cmd))

    step5_finalize(record, output_path=tmp_path / "out.jpg")

    assert commands
    assert "-strip" not in commands[0]
    assert "+profile" in commands[0]
    assert "-profile" not in commands[0]


def test_step2_rotate_dry_run_does_not_mark_angle_corrected(tmp_path):
    record = _record(tmp_path)
    record.config.dry_run = True
    record.measurements["original_angle"] = 0.0

    step2_rotate(record, reference_angle=10.0)

    assert record.measurements["angle_corrected"] is False
    assert record.work_path == tmp_path / "work.jpg"


def test_step3_crop_resize_clamps_negative_offsets(tmp_path, monkeypatch):
    record = _record(tmp_path)
    record.config.canvas_width = 1000
    commands: list[list[str]] = []

    monkeypatch.setattr("normalizer.transform._run", lambda cmd: commands.append(cmd))

    step3_crop_resize(record, bbox=(0, 0, 400, 400))

    assert commands
    assert commands[0][2] == "-crop"
    assert commands[0][3] == "500x500+0+0"


def test_run_raises_clear_error_on_timeout(monkeypatch):
    cmd = ["magick", "input.jpg", "-rotate", "5", "output.jpg"]

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr("normalizer.transform.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="ImageMagick command timed out"):
        _run(cmd)
