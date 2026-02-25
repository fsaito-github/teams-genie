# Azure Container Apps image for Databricks Genie Teams Bot
# Exposes: /api/messages and /api/health

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY containerapp/requirements.txt /app/containerapp/requirements.txt
RUN pip install --no-cache-dir -r /app/containerapp/requirements.txt

# Copy application source
COPY . /app

# Default port for ACA is typically 80 externally; container listens on PORT
ENV PORT=8000
EXPOSE 8000

CMD ["python", "-m", "containerapp.app"]
