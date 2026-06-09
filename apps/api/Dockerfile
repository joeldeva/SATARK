FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/satark/apps/api

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY apps/api /srv/satark/apps/api
COPY data /srv/satark/data

EXPOSE 8001

CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn main:app --host 0.0.0.0 --port 8001"]
