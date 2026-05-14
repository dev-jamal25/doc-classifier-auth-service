FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra worker-ml --no-install-project

COPY . .
RUN uv sync --frozen --no-dev --extra worker-ml

# TODO(infra): replace with a real worker entrypoint once app/entrypoints/worker.py exists.
CMD ["sh", "-c", "echo 'ERROR: worker entrypoint not yet implemented' && exit 1"]
