import textwrap
from pathlib import Path

import pytest

from normalizer.config import find_config, load_config
from normalizer.models import NormalizerConfig


@pytest.fixture
def yaml_file(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        textwrap.dedent(
            """
            framing:
              target_ratio: 0.75
              max_upscale: 1.2
            angle:
              enabled: false
              tolerance: 3.0
            """
        )
    )
    return path


def test_load_from_yaml(yaml_file):
    config = load_config(config_path=yaml_file)
    assert config.target_ratio == 0.75
    assert config.max_upscale == 1.2
    assert config.angle_enabled is False
    assert config.angle_tolerance == 3.0


def test_missing_keys_use_defaults(yaml_file):
    config = load_config(config_path=yaml_file)
    assert config.canvas_width == 1000
    assert config.srgb_convert is True


def test_cli_overrides_take_precedence(yaml_file):
    config = load_config(
        config_path=yaml_file,
        overrides={"target_ratio": 0.60, "angle_enabled": True},
    )
    assert config.target_ratio == 0.60
    assert config.angle_enabled is True


def test_no_file_uses_defaults():
    config = load_config(config_path=None)
    assert isinstance(config, NormalizerConfig)
    assert config.target_ratio == 0.80


def test_icc_profile_resolved_to_absolute(yaml_file):
    config = load_config(config_path=yaml_file)
    assert Path(config.icc_profile).is_absolute()


def test_find_config_returns_explicit(tmp_path):
    config_path = tmp_path / "my.yaml"
    config_path.touch()
    assert find_config(tmp_path, explicit=config_path) == config_path


def test_find_config_falls_back_to_input_dir(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.touch()
    assert find_config(tmp_path) == config_path


def test_find_config_raises_for_missing_explicit_path(tmp_path):
    missing = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError, match=str(missing)):
        find_config(tmp_path, explicit=missing)


def test_icc_profile_resolves_relative_to_config_directory(tmp_path):
    config_dir = tmp_path / "nested"
    config_dir.mkdir()
    icc = config_dir / "custom.icc"
    icc.touch()
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            color_management:
              icc_profile: ./custom.icc
            """
        )
    )

    config = load_config(config_path=config_path)
    assert Path(config.icc_profile) == icc.resolve()
