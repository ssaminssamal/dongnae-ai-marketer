FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8503 HF_HOME=/app/models/hf-cache
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libsndfile1 fonts-nanum && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . ./
RUN python setup_free_tts.py
EXPOSE 8503
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8503/healthz',timeout=4)"
CMD ["python", "launch_app.py", "--host", "0.0.0.0", "--no-browser"]
