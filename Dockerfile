FROM python:3.11-slim

# System deps for OpenCV / Pillow, plus curl for the healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render (and most PaaS hosts) inject a dynamic $PORT at runtime instead of
# always using 8501 — default to 8501 for local `docker compose up`, but
# defer to $PORT when the platform sets one.
ENV PORT=8501
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

CMD streamlit run app_create.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
