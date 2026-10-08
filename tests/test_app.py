import pytest

pytest.importorskip("gradio")

from finsight.app import Session, build_app  # noqa: E402
from finsight.config import Config  # noqa: E402


def test_session_files_are_removed_on_close(tmp_path, sample_pdf, monkeypatch):
    monkeypatch.delenv("FINSIGHT_PERSIST", raising=False)
    s = Session(Config(home=str(tmp_path / "home")))
    s.engine.add(sample_pdf)
    folder = s.tmp
    s.close()
    import os

    assert not os.path.exists(folder)


def test_persist_mode_keeps_files(tmp_path, sample_pdf, monkeypatch):
    monkeypatch.setenv("FINSIGHT_PERSIST", "1")
    s = Session(Config(home=str(tmp_path / "home")))
    s.engine.add(sample_pdf)
    s.close()
    assert list((tmp_path / "home" / "docs").glob("*/source.pdf"))


def test_app_builds():
    assert build_app(Config(backend="none")) is not None
