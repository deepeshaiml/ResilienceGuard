FROM python:3.12.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && addgroup --system rg \
    && adduser --system --ingroup rg --home /app rg \
    && mkdir -p /app/restores /app/artifacts \
    && chown -R rg:rg /app

COPY --chown=rg:rg backend/app /app/app
COPY --chown=rg:rg data /app/data

ENV DATA_ROOT=/app/data RESTORE_ROOT=/app/restores DATABASE_URL=postgresql+psycopg://rg:rg-local-demo-only@db:5432/resilienceguard
EXPOSE 8000
USER rg
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
