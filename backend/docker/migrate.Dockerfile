FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra migrate --no-install-project

COPY . .
RUN uv sync --frozen --no-dev --extra migrate

CMD ["uv", "run", "alembic", "upgrade", "head"]
