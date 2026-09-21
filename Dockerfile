# pdf-tools: the Flask app behind gunicorn, nothing else.
FROM python:3.12-slim

# ffmpeg is the app's one optional external tool: HEIC/AVIF/RAW photos and
# video contact sheets. It is also most of the image — 955 MB with it, 370 MB
# without — so it can be left out with `--build-arg WITH_FFMPEG=0`. Every other
# format keeps working and those uploads are politely refused.
ARG WITH_FFMPEG=1
RUN if [ "$WITH_FFMPEG" = "1" ]; then \
      apt-get update \
   && apt-get install -y --no-install-recommends ffmpeg \
   && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app

# Dependencies first, so editing the source does not re-run the install.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app.py config.py ./
COPY pdf_tools/ pdf_tools/
COPY templates/ templates/
COPY static/ static/

# Uploads are spooled to /tmp and deleted; nothing else is ever written.
RUN useradd --create-home --uid 10001 pdftools
USER pdftools

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 5000

# One worker by default: each request in flight pays the memory cost again
# (see the Memory table in the README). The timeout is generous because
# compressing a big upload is slow.
CMD ["sh", "-c", "exec gunicorn -w ${WORKERS:-1} -b 0.0.0.0:${PORT:-5000} --timeout ${TIMEOUT:-600} app:app"]
