import pytest

from finsight.config import Config


def test_defaults_are_not_downscaled():
    assert Config().max_side >= 1024


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("FINSIGHT_HOME", str(tmp_path))
    monkeypatch.setenv("FINSIGHT_TOP_K", "7")
    monkeypatch.setenv("FINSIGHT_USE_VISION", "true")
    cfg = Config.load()
    assert cfg.home_path == tmp_path
    assert cfg.top_k == 7
    assert cfg.use_vision is True


def test_yaml_file(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("backend: mock\nmax_side: 2000\n")
    cfg = Config.load(str(p))
    assert cfg.backend == "mock" and cfg.max_side == 2000


def test_small_max_side_rejected():
    with pytest.raises(ValueError):
        Config(max_side=512)
