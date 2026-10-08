"""Model backends. All of them take a prompt and optional page images and return text."""

from __future__ import annotations

import base64
import io
from typing import Callable, Protocol

import requests
from PIL import Image

from .config import Config


class Backend(Protocol):
    name: str

    def chat(
        self, system: str, user: str, images: list[Image.Image] | None = None, max_tokens: int = 400
    ) -> str: ...


class MockBackend:
    """For tests. Returns whatever the reply function returns, or a fixed string."""

    name = "mock"

    def __init__(self, reply: Callable[[str, str], str] | str = "mock reply"):
        self.reply = reply
        self.calls: list[tuple[str, str, int]] = []

    def chat(self, system, user, images=None, max_tokens=400):
        self.calls.append((system, user, len(images or [])))
        return self.reply(system, user) if callable(self.reply) else self.reply


def _data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


class OpenAICompatBackend:
    """Any server that speaks /v1/chat/completions: vLLM, llama.cpp server, Ollama, LM Studio."""

    def __init__(self, base_url: str, model: str, api_key: str = "none", timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.name = f"openai-compatible:{model}"

    def chat(self, system, user, images=None, max_tokens=400):
        content: list[dict] = [{"type": "text", "text": user}]
        for img in images or []:
            content.append({"type": "image_url", "image_url": {"url": _data_url(img)}})
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content if images else user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        r = requests.post(
            f"{self.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


class TransformersBackend:
    """Runs a model in-process. Text models and Qwen2-VL / Qwen2.5-VL vision models."""

    def __init__(self, model_id: str, device: str = "auto", quantization: str = "none"):
        import torch  # imported here so the base install stays light

        self.torch = torch
        self.model_id = model_id
        self.name = f"transformers:{model_id}"
        self.vision = "-vl" in model_id.lower()
        if device == "auto":
            device = (
                "cuda"
                if torch.cuda.is_available()
                else "mps"
                if torch.backends.mps.is_available()
                else "cpu"
            )
        self.device = device
        kwargs: dict = {}
        if quantization in ("4bit", "8bit"):
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=quantization == "4bit",
                load_in_8bit=quantization == "8bit",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )
            kwargs["device_map"] = "auto"
        else:
            kwargs["torch_dtype"] = torch.float16 if device != "cpu" else torch.float32

        from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

        if self.vision:
            import transformers

            cls_name = (
                "Qwen2_5_VLForConditionalGeneration"
                if "2.5" in model_id
                else "Qwen2VLForConditionalGeneration"
            )
            model_cls = getattr(transformers, cls_name)
            self.processor = AutoProcessor.from_pretrained(model_id)
        else:
            model_cls = AutoModelForCausalLM
            self.processor = AutoTokenizer.from_pretrained(model_id)
        self.model = model_cls.from_pretrained(model_id, **kwargs).eval()
        if "device_map" not in kwargs:
            self.model.to(device)

    def chat(self, system, user, images=None, max_tokens=400):
        torch = self.torch
        if self.vision and images:
            content = [{"type": "image"} for _ in images] + [{"type": "text", "text": user}]
            msgs = [{"role": "system", "content": system}, {"role": "user", "content": content}]
            text = self.processor.apply_chat_template(
                msgs, tokenize=False, add_generation_prompt=True
            )
            inputs = self.processor(text=[text], images=images, return_tensors="pt")
        else:
            msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            tok = getattr(self.processor, "tokenizer", self.processor)
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = tok([text], return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items() if hasattr(v, "to")}
        with torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
        new = out[0][inputs["input_ids"].shape[1] :]
        tok = getattr(self.processor, "tokenizer", self.processor)
        return tok.decode(new, skip_special_tokens=True).strip()


def make_backend(cfg: Config) -> Backend | None:
    if cfg.backend == "none":
        return None
    if cfg.backend == "mock":
        return MockBackend()
    if cfg.backend == "openai":
        return OpenAICompatBackend(cfg.llm_base_url, cfg.llm_model, cfg.llm_api_key)
    if cfg.backend == "transformers":
        return TransformersBackend(cfg.llm_model, cfg.device, cfg.quantization)
    raise ValueError(f"unknown backend: {cfg.backend}")
