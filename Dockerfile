FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY pip_wheels/ /tmp/pip_wheels/
RUN pip install --no-cache-dir --no-index --find-links=/tmp/pip_wheels -r requirements.txt

COPY . .

RUN mkdir -p /app/documents /app/logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
