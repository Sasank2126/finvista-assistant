#!/bin/bash
echo "Starting FinVista..."

# Auto-index PDFs on startup
python3 /app/app/preload.py

# Start Streamlit
exec streamlit run /app/app/streamlit_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.maxUploadSize=200
