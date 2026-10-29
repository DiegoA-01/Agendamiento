FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY . .

EXPOSE 8000

# Desarrollo: runserver. El servidor de producción (WSGI/ASGI) queda pendiente de aprobación
# porque no está en la lista de dependencias de la sección 2 de la spec.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
