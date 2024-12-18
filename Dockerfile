FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    net-tools \
    dnsutils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY node /app/node
COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "-m", "node"]
