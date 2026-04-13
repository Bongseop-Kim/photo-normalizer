from __future__ import annotations

from pathlib import Path

from normalizer.models import ImageRecord, NormalizerConfig
from normalizer.transform import step4_brightness, step5_finalize


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
    assert commands[0][3] == "0%,96.08%"


def test_step5_finalize_respects_strip_and_preserve_flags(tmp_path, monkeypatch):
    record = _record(tmp_path)
    record.config.strip_exif = False
    record.config.preserve_icc = False
    commands: list[list[str]] = []

    monkeypatch.setattr("normalizer.transform._run", lambda cmd: commands.append(cmd))

    step5_finalize(record, output_path=tmp_path / "out.jpg")

    assert commands
    assert "-strip" not in commands[0]
    assert "-profile" not in commands[0]
