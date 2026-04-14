from __future__ import annotations

from pathlib import Path

import pytest

import normalize


def test_main_rejects_output_same_as_input(tmp_path, monkeypatch):
    input_dir = tmp_path / "images"
    input_dir.mkdir()
    monkeypatch.setattr(
        "sys.argv",
        ["normalize.py", "run", str(input_dir), "--output", str(input_dir)],
    )

    with pytest.raises(SystemExit, match="output directory must be different from input directory"):
        normalize.main()


def test_main_rejects_missing_explicit_config(tmp_path, monkeypatch):
    input_dir = tmp_path / "images"
    input_dir.mkdir()
    missing = tmp_path / "missing.yaml"
    monkeypatch.setattr(
        "sys.argv",
        ["normalize.py", "run", str(input_dir), "--config", str(missing)],
    )

    with pytest.raises(SystemExit, match=str(missing)):
        normalize.main()


def test_no_subcommand_exits(monkeypatch):
    monkeypatch.setattr("sys.argv", ["normalize.py"])

    with pytest.raises(SystemExit):
        normalize.main()
