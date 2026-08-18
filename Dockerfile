FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir -e .
ENV YODMCP_MEMORY_BACKEND=sqlite \
    YODMCP_MEMORY_DB=/data/yodmcp_memory.db \
    YODMCP_PLAN=free
VOLUME ["/data"]
EXPOSE 8080 9000 8000
CMD ["yodmcp-api", "--host", "0.0.0.0", "--port", "8080"]
