FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps (kept minimal; wheels cover numpy/scipy/matplotlib)
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

EXPOSE 8000

# Start FastAPI with Uvicorn
CMD ["uvicorn", "ecg_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
