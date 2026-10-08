import json
import os
import time

from finsight.config import Config
from finsight.store import Store


def test_add_load_delete(tmp_path, sample_pdf):
    store = Store(Config(home=str(tmp_path / "home")))
    store.add(sample_pdf)
    docs = store.load_all()
    assert [d.name for d in docs] == ["acme-report.pdf"]
    assert len(docs[0].pages) == 3
    assert store.pdf_path("acme-report.pdf").exists()
    assert store.delete("acme-report.pdf") == 1
    assert store.load_all() == []


def test_delete_all_removes_files(tmp_path, sample_pdf):
    store = Store(Config(home=str(tmp_path / "home")))
    store.add(sample_pdf)
    store.delete()
    assert not any((tmp_path / "home" / "docs").iterdir())


def test_retention(tmp_path, sample_pdf):
    store = Store(Config(home=str(tmp_path / "home"), retention_days=1))
    store.add(sample_pdf)
    meta = next((tmp_path / "home" / "docs").glob("*/pages.json"))
    raw = json.loads(meta.read_text())
    raw["added"] = time.time() - 3 * 86400
    meta.write_text(json.dumps(raw))
    assert store.purge_expired() == 1
    assert os.listdir(tmp_path / "home" / "docs") == []


def test_tables_and_raw_text_survive_the_round_trip(tmp_path, sample_pdf):
    store = Store(Config(home=str(tmp_path / "home")))
    fresh = store.add(sample_pdf)
    loaded = store.load_all()[0]
    for a, b in zip(fresh.pages, loaded.pages, strict=True):
        assert (a.tables, a.raw_tables, a.raw) == (b.tables, b.raw_tables, b.raw)
    assert loaded.page(2).raw_tables and "Total net sales" in loaded.page(2).raw
