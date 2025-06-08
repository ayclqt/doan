# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOAD=0

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN uv sync --frozen --no-dev

FROM python:3.12-bookworm-slim

COPY --from=builder /app /app

WORKDIR /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT ["litestar","run"]

CMD ["--host", "0.0.0.0"]
