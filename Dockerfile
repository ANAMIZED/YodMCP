FROM python:3.12-slim

# Non-root user for production safety
RUN useradd --create-home --shell /bin/bash --uid 10001 yodmcp

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY skills ./skills

RUN pip install --no-cache-dir -e . \
    && mkdir -p /data \
    && chown -R yodmcp:yodmcp /app /data

USER yodmcp

ENV YODMCP_MEMORY_BACKEND=sqlite \
    YODMCP_MEMORY_DB=/data/yodmcp_memory.db \
    YODMCP_SYSTEM_DB=/data/yodmcp_system.db \
    YODMCP_TASKS_BACKEND=sqlite \
    YODMCP_METER_BACKEND=sqlite \
    YODMCP_PLAN=free \
    PYTHONUNBUFFERED=1

VOLUME ["/data"]
EXPOSE 8080 9000 8000

# Liveness: hits open /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)" || exit 1

CMD ["yodmcp-api", "--host", "0.0.0.0", "--port", "8080"]
