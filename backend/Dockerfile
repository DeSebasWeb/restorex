FROM python:3.12-slim

WORKDIR /app

# Force unbuffered Python output for Docker logs
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client openssh-client && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "src/entry_points/api/app.py"]
