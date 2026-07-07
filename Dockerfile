FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

# Remove packages dir (not needed for API-only deployment)
RUN rm -rf /app/packages /app/docs /app/sdks /app/tests /app/scripts /app/.github

# Install engine with our pyproject.toml fix (version hardcoded)
RUN pip install --no-cache-dir -e "/app/engine[legacy]" && \
    pip install --no-cache-dir fastapi uvicorn python-multipart

# Download InsightFace models at build time
RUN python -c "from insightface.app import FaceAnalysis; app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); app.prepare(ctx_id=-1, det_size=(640, 640))"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
