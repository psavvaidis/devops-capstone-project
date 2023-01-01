FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install -r --no-cache-dir requirements.txt 

COPY service/ ./service/

# Switch to a non-root user
RUN useradd --uid 1000 theia && chown -R theia /app
USER theia

EXPOSE 8080
CMD ["gunicorn"  , "--bind=0.0.0.0:8090", "--log-level=info", "service:app"]
