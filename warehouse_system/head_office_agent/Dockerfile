FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set python path so that imports from app work if run from /app/app
ENV PYTHONPATH=/app/app:/app

CMD ["python", "app/main.py"]
