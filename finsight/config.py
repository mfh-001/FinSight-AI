"""Settings. Everything can be set by FINSIGHT_* env vars or a yaml file."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

import yaml


@dataclass
class Config:
    home: str = "~/.finsight"
    # page images, only used for scanned pages and the vision model
    render_dpi: int = 170
    max_side: int = 1536  # long side in px, never below 1024
    # none: retrieval only, mock: tests, openai: any OpenAI-compatible server, transformers: local
    backend: str = "none"
    llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "none"
    device: str = "auto"
    quantization: str = "none"  # none, 4bit, 8bit
    use_vision: bool = False  # send page images to the model
    visual_retriever: str = ""  # e.g. vidore/colpali-v1.2, empty means off
    top_k: int = 4
    max_new_tokens: int = 400
    retention_days: int = 0  # 0 keeps files until you delete them

    def __post_init__(self) -> None:
        if self.max_side < 1024:
            raise ValueError("max_side must be at least 1024")

    @property
    def home_path(self) -> Path:
        return Path(self.home).expanduser()

    @classmethod
    def load(cls, path: str | None = None) -> Config:
        data: dict = {}
        path = path or os.environ.get("FINSIGHT_CONFIG")
        if path:
            data = yaml.safe_load(Path(path).read_text()) or {}
        for f in fields(cls):
            env = os.environ.get("FINSIGHT_" + f.name.upper())
            if env is not None:
                data[f.name] = _cast(f.type, env)
        return cls(**data)


def _cast(typ: object, value: str):
    name = typ if isinstance(typ, str) else getattr(typ, "__name__", "")
    if name == "int":
        return int(value)
    if name == "bool":
        return value.lower() in ("1", "true", "yes")
    return value
