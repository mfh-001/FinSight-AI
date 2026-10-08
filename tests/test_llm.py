import json

import pytest
from PIL import Image

from finsight.config import Config
from finsight.llm import MockBackend, OpenAICompatBackend, make_backend


def test_make_backend_variants():
    assert make_backend(Config(backend="none")) is None
    assert isinstance(make_backend(Config(backend="mock")), MockBackend)
    b = make_backend(Config(backend="openai", llm_model="m", llm_base_url="http://x/v1"))
    assert isinstance(b, OpenAICompatBackend)
    with pytest.raises(ValueError):
        make_backend(Config(backend="nope"))


def test_mock_records_calls():
    m = MockBackend(lambda s, u: u.upper())
    assert m.chat("sys", "hi") == "HI"
    assert m.calls == [("sys", "hi", 0)]


def test_openai_payload(monkeypatch):
    seen = {}

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": " ok "}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        seen.update(url=url, body=json, headers=headers)
        return R()

    monkeypatch.setattr("finsight.llm.requests.post", fake_post)
    b = OpenAICompatBackend("http://host:8000/v1/", "qwen", "k")
    assert b.chat("s", "q", images=[Image.new("RGB", (8, 8))]) == "ok"
    assert seen["url"] == "http://host:8000/v1/chat/completions"
    assert seen["body"]["temperature"] == 0
    parts = seen["body"]["messages"][1]["content"]
    assert parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert seen["headers"]["Authorization"] == "Bearer k"
    json.dumps(seen["body"])
