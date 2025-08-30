FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_CACHE_DIR='/tmp/poetry_cache'\
    PATH="/app/.venv/bin:$PATH" \
    USER=dockeruser \
    USER_ID=1000 \
    GROUP=dockergroup \
    GROUP_ID=1000

COPY --chown=${USER}:${GROUP} --chmod=0755 pyproject.toml poetry.lock README.md /app/

RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

FROM python:3.11-slim AS runtime

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    USER=dockeruser \
    USER_ID=1000 \
    GROUP=dockergroup \
    GROUP_ID=1000

# Install Chrome, ChromeDriver, and other dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    gosu \
    procps \
    wget \
    gnupg \
    python3-gunicorn \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${GROUP_ID}" "${GROUP}" && \
    useradd \
        --uid "${USER_ID}" \
        --gid "${GROUP}" \
        --create-home \
        --home /var/empty \
        --shell /bin/nologin \
        "${USER}" && \
    mkdir -p /config /data /logs && \
    chown -R "${USER}":"${GROUP}" /config /logs && \
    chmod -R a+rwX /config /logs

COPY --from=builder --chown=${USER}:${GROUP} --chmod=0755 ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY --chown=${USER}:${GROUP} --chmod=0755 src/super_simple_kiosk    /app/super_simple_kiosk
COPY --chown=${USER}:${GROUP} --chmod=0755 run_scripts /app/run_scripts
COPY --chown=${USER}:${GROUP} --chmod=0755 utils       /app/utils
COPY --chown=${USER}:${GROUP} --chmod=0755 wsgi.py     /app/wsgi.py

# Set up the environment variables we're expecting
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LOGFILE=/logs/super_simple_kiosk.log \
    FLASK_ENV=production \
    FLASK_DEBUG=false \
    DISPLAY_CONFIG_FILE=/config/urls.yaml \
    DISPLAY_STATE_FILE=/data/state.json

VOLUME /config /data /logs

EXPOSE 5000

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/api/health || exit 1

ENTRYPOINT ["/app/run_scripts/start_module.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "wsgi:app"]
