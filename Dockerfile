FROM python:3.12-alpine3.20

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install the necessary utilities for user and group management
RUN apk add --no-cache shadow

WORKDIR /task_handler_service

ADD requirements.txt .

# Install system dependencies including MySQL client (via MariaDB connector)
RUN set -ex \
    && apk add --no-cache gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    libpq-dev \
    && pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

ADD . .