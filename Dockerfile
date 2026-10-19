FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/tmp
WORKDIR /app

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /data \
    && chown appuser:appuser /data

COPY --chown=appuser:appuser app.py ./
COPY --chown=appuser:appuser index.html ./
COPY --chown=appuser:appuser backend ./backend
COPY --chown=appuser:appuser admin ./admin
COPY --chown=appuser:appuser assets ./assets
COPY --chown=appuser:appuser css ./css
COPY --chown=appuser:appuser img ./img
COPY --chown=appuser:appuser js ./js
COPY --chown=appuser:appuser scripts ./scripts

USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/', timeout=3)"

CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:3000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "60", "app:app"]
