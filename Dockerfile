FROM python:3.12-slim
# WITH_TTS=1 — серверная озвучка башкирского (+~1 ГБ), WITH_ASR=1 — расшифровка аудио (faster-whisper)
ARG WITH_TTS=0
ARG WITH_ASR=1
WORKDIR /srv
COPY requirements.txt requirements-tts.txt requirements-asr.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$WITH_ASR" = "1" ]; then pip install --no-cache-dir -r requirements-asr.txt; fi && \
    if [ "$WITH_TTS" = "1" ]; then pip install --no-cache-dir -r requirements-tts.txt; fi
COPY app ./app
COPY import_hf.py import_schools.py ./
WORKDIR /srv/app
ENV TRUST_PROXY=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
