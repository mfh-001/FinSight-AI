"""Entry point for the Hugging Face Space. It runs the same app as `finsight serve`."""
import os

from finsight.app import build_app
from finsight.config import Config

# CPU Space: no model, so answers are the best matching lines with page citations.
# For a GPU Space set FINSIGHT_BACKEND=transformers and FINSIGHT_LLM_MODEL in the Space settings.
os.environ.setdefault("FINSIGHT_BACKEND", "none")

demo = build_app(Config.load())

if __name__ == "__main__":
    demo.launch()
