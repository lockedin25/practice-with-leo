# Python 3.13 rather than the 3.13-or-3.14 that development happens to run.
# Verified rather than assumed: the dependency set resolves unchanged on 3.12 and
# 3.13, and the suite is identical on 3.13. 3.13 also drops the "pydantic.v1 is
# not compatible with Python 3.14" warning that 3.14 emits.
FROM python:3.13-slim AS builder

# uv resolves from the committed lockfile, so the image is reproducible and no
# resolution happens at build time.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

# The virtual environment is built at the path it will finally live at. A venv's
# console scripts carry an absolute shebang, so copying .venv from /build to
# /srv leaves every entry point pointing at an interpreter that is not there,
# and the container dies with "exec ...: no such file or directory".
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/srv/.venv

WORKDIR /build

# Dependencies are their own layer: they change far less often than the
# application, so editing a route does not reinstall langchain.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# The project itself, installed without dev extras.
COPY app ./app
COPY README.md ./
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS runtime

# No system packages are needed. All audio work happens in the browser, so there
# is no ffmpeg or codec dependency, which keeps the image small and the CVE
# surface close to the base.

# A non-root user owns the code and the volume. Running as root inside a
# container is a needless escalation if anything else goes wrong.
RUN useradd --create-home --uid 10001 leo

WORKDIR /srv

COPY --from=builder --chown=leo:leo /srv/.venv /srv/.venv
COPY --chown=leo:leo app ./app

# Case content. Read-only at runtime, but the catalogue will not start without
# it: CaseCatalogue.from_reservoir loads every package at import.
COPY --chown=leo:leo reservoir ./reservoir
COPY --chown=leo:leo corpus ./corpus
COPY --chown=leo:leo knowledge_base ./knowledge_base
COPY --chown=leo:leo evaluation ./evaluation

# The mount point for the persistent volume. Created and owned here so the
# application can write even if the platform attaches the volume empty.
RUN mkdir -p /data && chown leo:leo /data
VOLUME ["/data"]

ENV PATH="/srv/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/data/casecall.db

USER leo
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4).status == 200 else 1)"

# One worker, deliberately. SQLite has a single writer, so a second worker on the
# same volume would contend for it rather than add throughput. Concurrency comes
# from the thread pool that already serves the synchronous route handlers; the
# time to add workers is the same time as the move to Postgres.
# Invoked through the interpreter rather than the console script, so the entry
# point does not depend on a shebang surviving the copy between stages.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--timeout-keep-alive", "75"]
