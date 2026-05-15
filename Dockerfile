FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KMP_DUPLICATE_LIB_OK=TRUE

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-deployment.txt ./
RUN pip install --no-cache-dir -r requirements-deployment.txt

COPY . .

EXPOSE 8000

CMD ["python", "surveillance_live_service.py", "--host", "0.0.0.0", "--port", "8000"]
