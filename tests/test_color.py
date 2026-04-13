import shutil
import pytest
import subprocess
from pathlib import Path

from normalizer.color import detect_icc_profile, step0_color_normalize
from normalizer.models import ImageRecord, NormalizerConfig


def _make_srgb_jpeg(path: Path, icc: str) -> None:
    if shutil.which("magick") is None:
        pytest.skip("ImageMagick 'magick' binary is required for color tests")
    subprocess.run(
        ["magick", "-size", "100x100", "xc:white", "-profile", icc, str(path)],
        check=True,
    )


def _record(tmp_path) -> ImageRecord:
    icc = str((Path("assets/profiles/sRGB_IEC61966-2-1.icc")).resolve())
    config = NormalizerConfig()
    config.icc_profile = icc
    src = tmp_path / "test.jpg"
    _make_srgb_jpeg(src, icc)
    work = tmp_path / "work.jpg"
    shutil.copy(src, work)
    return ImageRecord(
        source_path=src,
        work_path=work,
        config=config,
        measurements={},
        warnings=[],
    )


def test_detect_icc_profile_returns_string(tmp_path):
    icc = str(Path("assets/profiles/sRGB_IEC61966-2-1.icc").resolve())
    src = tmp_path / "t.jpg"
    _make_srgb_jpeg(src, icc)
    profile = detect_icc_profile(src)
    assert isinstance(profile, str)


def test_step0_records_profile_in_measurements(tmp_path):
    record = _record(tmp_path)
    result = step0_color_normalize(record)
    assert "original_profile" in result.measurements
    assert "profile_converted" in result.measurements


def test_step0_srgb_not_converted(tmp_path):
    record = _record(tmp_path)
    result = step0_color_normalize(record)
    assert result.measurements["profile_converted"] is False


def test_step0_no_error_on_success(tmp_path):
    record = _record(tmp_path)
    result = step0_color_normalize(record)
    assert result.error is None


def test_step0_dry_run_skips_profile_conversion(tmp_path, monkeypatch):
    record = _record(tmp_path)
    record.config.dry_run = True

    monkeypatch.setattr("normalizer.color.detect_icc_profile", lambda _: "Adobe RGB")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("profile conversion should be skipped during dry-run")

    monkeypatch.setattr("normalizer.color.subprocess.run", fail_if_called)

    original_path = record.work_path
    result = step0_color_normalize(record)
    assert result.work_path == original_path
    assert result.measurements["profile_converted"] is False
