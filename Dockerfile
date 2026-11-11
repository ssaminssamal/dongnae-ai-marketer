FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8503 HF_HOME=/app/models/hf-cache
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libsndfile1 fonts-nanum && rm -rf /var/lib/apt/lists/*
# Hugging Face Spaces runs containers as uid 1000, so the app folder must belong to that user.
RUN useradd -m -u 1000 user
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY --chown=user:user . ./
RUN mkdir -p outputs .data .runtime models && chown -R user:user /app && chmod +x start.sh
USER user
RUN python setup_free_tts.py
EXPOSE 8503
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8503/healthz',timeout=4)"
CMD ["./start.sh"]
