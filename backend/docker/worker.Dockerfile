FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra worker-ml --no-install-project

COPY . .
RUN uv sync --frozen --no-dev --extra worker-ml

CMD ["uv", "run", "python", "-m", "app.entrypoints.worker"]
