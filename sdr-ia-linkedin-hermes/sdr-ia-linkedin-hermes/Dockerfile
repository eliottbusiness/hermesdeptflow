FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .
COPY configs ./configs
COPY hermes ./hermes
COPY scripts ./scripts
CMD ["sdr-ai", "--help"]
