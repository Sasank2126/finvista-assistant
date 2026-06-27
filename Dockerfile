FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY app/ ./app/

# Copy streamlit config to home directory of finvista user
RUN useradd -m -u 1000 finvista && \
    mkdir -p /app/chroma_db && \
    mkdir -p /home/finvista/.streamlit && \
    cp /app/app/.streamlit/config.toml /home/finvista/.streamlit/config.toml && \
    chown -R finvista:finvista /app && \
    chown -R finvista:finvista /home/finvista/.streamlit

USER finvista

ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    CHROMA_DB_PATH=/app/chroma_db \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["bash", "/app/app/startup.sh"]
