import json

import pytest

from finsight.cli import main


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("FINSIGHT_HOME", str(tmp_path / "home"))
    return tmp_path


def test_help_exits_clean(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    for word in ("ingest", "ask", "extract", "eval"):
        assert word in out


def test_ingest_then_ask_without_model(home, sample_pdf, capsys):
    assert main(["ingest", str(sample_pdf.parent)]) == 0
    assert "acme-report.pdf: 3 pages" in capsys.readouterr().out
    assert main(["ask", "what were the total net sales"]) == 0
    out = capsys.readouterr().out
    assert "1,200" in out and "acme-report.pdf p.2" in out


def test_ask_json_with_mock_backend(home, sample_pdf, capsys):
    main(["ingest", str(sample_pdf)])
    capsys.readouterr()
    code = main(["--backend", "mock", "ask", "net sales", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0 and data["citations"] == ["acme-report.pdf p.2"]


def test_extract_to_xlsx(home, sample_pdf, tmp_path, capsys):
    main(["ingest", str(sample_pdf)])
    out = tmp_path / "o.xlsx"
    assert main(["extract", "--schema", "statements", "--out", str(out)]) == 0
    assert out.exists()


def test_risk_prints_all_checks(home, sample_pdf, capsys):
    main(["ingest", str(sample_pdf)])
    capsys.readouterr()
    assert main(["risk"]) == 0
    assert "GROWTH" in capsys.readouterr().out


def test_ask_before_ingest_is_a_clean_error(home, capsys):
    assert main(["ask", "anything"]) == 1
    assert "finsight ingest" in capsys.readouterr().err


def test_delete_all(home, sample_pdf, capsys):
    main(["ingest", str(sample_pdf)])
    capsys.readouterr()
    assert main(["delete", "--all"]) == 0
    assert "deleted 1" in capsys.readouterr().out
    assert main(["docs"]) == 0
