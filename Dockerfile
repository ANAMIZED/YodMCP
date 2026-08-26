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

# Glama inspects MCP over stdio. Use `yodmcp --http` for streamable HTTP.
CMD ["yodmcp"]
