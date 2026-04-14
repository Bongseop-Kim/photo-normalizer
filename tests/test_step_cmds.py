from __future__ import annotations

import json
from pathlib import Path

import pytest

import normalize
from normalizer.cli.step_cmds import (
    _prepare_output_dir,
    _resolve_inputs,
    _resolve_output,
)
from tests.conftest import make_product_image


def test_resolve_inputs_directory(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "b.PNG").write_bytes(b"")
    (tmp_path / "readme.txt").write_bytes(b"")

    paths, is_dir = _resolve_inputs(tmp_path)

    assert is_dir is True
    assert {path.name for path in paths} == {"a.jpg", "b.PNG"}


def test_resolve_inputs_single_file(tmp_path):
    file_path = tmp_path / "photo.jpg"
    file_path.write_bytes(b"")

    paths, is_dir = _resolve_inputs(file_path)

    assert is_dir is False
    assert paths == [file_path]


def test_resolve_inputs_unsupported_file_exits(tmp_path):
    file_path = tmp_path / "doc.pdf"
    file_path.write_bytes(b"")

    with pytest.raises(SystemExit):
        _resolve_inputs(file_path)


def test_resolve_inputs_missing_path_exits(tmp_path):
    with pytest.raises(SystemExit):
        _resolve_inputs(tmp_path / "nonexistent")


def test_resolve_output_dir_mode_default(tmp_path):
    result = _resolve_output(None, tmp_path / "photos", "step0", is_dir_mode=True)

    assert result == (tmp_path / "photos_step0").resolve()


def test_resolve_output_file_mode_default(tmp_path):
    file_path = tmp_path / "photo1.jpg"

    result = _resolve_output(None, file_path, "step2", is_dir_mode=False)

    assert result == (tmp_path / "photo1_step2.jpg").resolve()


def test_resolve_output_explicit(tmp_path):
    explicit = tmp_path / "my_output"

    result = _resolve_output(explicit, tmp_path / "photos", "step0", is_dir_mode=True)

    assert result == explicit.resolve()


def test_prepare_output_dir_creates(tmp_path):
    target = tmp_path / "new_dir"

    _prepare_output_dir(target)

    assert target.is_dir()


def test_prepare_output_dir_nonempty_exits(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "file.txt").write_bytes(b"x")

    with pytest.raises(SystemExit):
        _prepare_output_dir(target)


def test_step0_file_mode_routes_to_step0_fn(tmp_path, monkeypatch):
    make_product_image(tmp_path, "photo1.jpg")
    called = []

    def mock_step0(record):
        called.append(record.source_path.name)
        return record

    monkeypatch.setattr("normalizer.cli.step_cmds.step0_color_normalize", mock_step0, raising=False)
    monkeypatch.setattr("sys.argv", ["normalize.py", "step0", str(tmp_path / "photo1.jpg")])

    normalize.main()

    assert called == ["photo1.jpg"]
    assert (tmp_path / "photo1_step0.jpg").exists()


def test_step0_dir_mode_processes_all_images(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    make_product_image(input_dir, "a.jpg")
    make_product_image(input_dir, "b.jpg")
    called = []

    def mock_step0(record):
        called.append(record.source_path.name)
        return record

    monkeypatch.setattr("normalizer.cli.step_cmds.step0_color_normalize", mock_step0, raising=False)
    monkeypatch.setattr("sys.argv", ["normalize.py", "step0", str(input_dir)])

    normalize.main()

    assert sorted(called) == ["a.jpg", "b.jpg"]
    output_dir = tmp_path / "input_step0"
    assert output_dir.is_dir()
    assert (output_dir / "a.jpg").exists()
    assert (output_dir / "b.jpg").exists()


def test_step1_dir_mode_writes_measurements(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    make_product_image(input_dir, "photo1.jpg")
    make_product_image(input_dir, "photo2.jpg")

    monkeypatch.setattr("sys.argv", ["normalize.py", "step1", str(input_dir)])

    normalize.main()

    output_dir = tmp_path / "input_step1"
    assert output_dir.is_dir()
    assert (output_dir / "photo1.jpg").exists()
    assert (output_dir / "photo2.jpg").exists()
    data = json.loads((output_dir / "_measurements.json").read_text())
    assert len(data["images"]) == 2
    assert "reference_angle" in data["batch"]
    assert "reference_brightness" in data["batch"]
    assert {entry["file"] for entry in data["images"]} == {"photo1.jpg", "photo2.jpg"}


def test_step1_file_mode_prints_to_stdout(tmp_path, monkeypatch, capsys):
    make_product_image(tmp_path, "photo1.jpg")

    monkeypatch.setattr("sys.argv", ["normalize.py", "step1", str(tmp_path / "photo1.jpg")])

    normalize.main()

    out = capsys.readouterr().out
    assert "bbox:" in out
    assert "angle:" in out
    assert "brightness:" in out


def test_step2_requires_reference_angle(tmp_path, monkeypatch):
    make_product_image(tmp_path, "photo1.jpg")

    monkeypatch.setattr("sys.argv", ["normalize.py", "step2", str(tmp_path / "photo1.jpg")])

    with pytest.raises(SystemExit):
        normalize.main()


def test_step2_file_mode_calls_rotate_with_reference_angle(tmp_path, monkeypatch):
    make_product_image(tmp_path, "photo1.jpg")
    calls = []

    def mock_rotate(record, *, reference_angle):
        calls.append(reference_angle)
        return record

    monkeypatch.setattr("normalizer.cli.step_cmds.step2_rotate", mock_rotate, raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["normalize.py", "step2", str(tmp_path / "photo1.jpg"), "--reference-angle", "3.5"],
    )

    normalize.main()

    assert calls == [3.5]
    assert (tmp_path / "photo1_step2.jpg").exists()


def test_step3_file_mode_auto_detects_bbox(tmp_path, monkeypatch):
    make_product_image(tmp_path, "photo1.jpg")
    crop_calls = []

    def mock_crop(record, *, bbox):
        crop_calls.append(bbox)
        return record

    monkeypatch.setattr("normalizer.cli.step_cmds.step3_crop_resize", mock_crop, raising=False)
    monkeypatch.setattr("sys.argv", ["normalize.py", "step3", str(tmp_path / "photo1.jpg")])

    normalize.main()

    assert len(crop_calls) == 1
    assert (tmp_path / "photo1_step3.jpg").exists()


def test_step3_uses_explicit_bbox(tmp_path, monkeypatch):
    make_product_image(tmp_path, "photo1.jpg")
    crop_calls = []

    def mock_crop(record, *, bbox):
        crop_calls.append(bbox)
        return record

    monkeypatch.setattr("normalizer.cli.step_cmds.step3_crop_resize", mock_crop, raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["normalize.py", "step3", str(tmp_path / "photo1.jpg"), "--bbox", "10,20,300,400"],
    )

    normalize.main()

    assert crop_calls[0] == (10, 20, 300, 400)


def test_step4_requires_reference_brightness(tmp_path, monkeypatch):
    make_product_image(tmp_path, "photo1.jpg")

    monkeypatch.setattr("sys.argv", ["normalize.py", "step4", str(tmp_path / "photo1.jpg")])

    with pytest.raises(SystemExit):
        normalize.main()


def test_step4_file_mode_calls_brightness_with_reference(tmp_path, monkeypatch):
    make_product_image(tmp_path, "photo1.jpg")
    calls = []

    def mock_brightness(record, *, reference_bg):
        calls.append(reference_bg)
        return record

    monkeypatch.setattr("normalizer.cli.step_cmds.step4_brightness", mock_brightness, raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["normalize.py", "step4", str(tmp_path / "photo1.jpg"), "--reference-brightness", "245.0"],
    )

    normalize.main()

    assert calls == [245.0]
    assert (tmp_path / "photo1_step4.jpg").exists()


def test_step5_file_mode_calls_finalize_with_output_path(tmp_path, monkeypatch):
    make_product_image(tmp_path, "photo1.jpg")
    calls = []

    def mock_finalize(record, *, output_path):
        calls.append(str(output_path))
        return record

    monkeypatch.setattr("normalizer.cli.step_cmds.step5_finalize", mock_finalize, raising=False)
    monkeypatch.setattr("sys.argv", ["normalize.py", "step5", str(tmp_path / "photo1.jpg")])

    normalize.main()

    expected = str((tmp_path / "photo1_step5.jpg").resolve())
    assert calls == [expected]
