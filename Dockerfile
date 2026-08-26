# Glama inspects MCP over stdio. Do not start yodmcp-api here.
# Admin generator: build ["pip install --no-cache-dir ."]
#                  CMD   ["python", "-m", "yodmcp"]
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY skills ./skills

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin mcp \
    && mkdir -p /data \
    && chown -R mcp:mcp /app /data

USER mcp

ENV YODMCP_MEMORY_BACKEND=sqlite \
    YODMCP_MEMORY_DB=/data/yodmcp_memory.db \
    YODMCP_SYSTEM_DB=/data/yodmcp_system.db \
    YODMCP_TASKS_BACKEND=sqlite \
    YODMCP_METER_BACKEND=sqlite \
    YODMCP_PLAN=free

VOLUME ["/data"]

CMD ["python", "-m", "yodmcp"]
