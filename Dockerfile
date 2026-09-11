# Imagen oficial con Linux Jammy y dependencias de Chromium preinstaladas
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del proyecto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Asegura que el binario de Chromium coincida exactamente con la versión de Playwright instalada
RUN playwright install chromium

# Copiar el código fuente
COPY . .

# Crear la estructura de carpetas de salida dentro del contenedor
RUN mkdir -p data/processed

# Punto de entrada por defecto (puede sobreescribirse desde la terminal o compose)
ENTRYPOINT ["python", "main.py"]
CMD ["--max-pages", "2", "--format", "csv", "--output-dir", "data/processed"]
