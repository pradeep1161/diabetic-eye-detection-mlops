FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
ENV MLFLOW_TRACKING_URI=./mlruns
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
