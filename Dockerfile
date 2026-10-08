# CPU image. Retrieval and extraction work out of the box.
# Set FINSIGHT_BACKEND=openai and FINSIGHT_LLM_BASE_URL to use a local model server.
FROM python:3.12.7-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 FINSIGHT_HOME=/data FINSIGHT_HOST=0.0.0.0

COPY pyproject.toml README.md ./
COPY finsight ./finsight
COPY samples ./samples
COPY legacy/recorded_run ./legacy/recorded_run
RUN pip install ".[app]"

VOLUME /data
EXPOSE 7860
CMD ["finsight", "serve", "--port", "7860"]
