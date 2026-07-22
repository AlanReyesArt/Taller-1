FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y gcc build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto
EXPOSE 7860

# Iniciar Langflow
CMD ["langflow", "run", "--host", "0.0.0.0", "--port", "7860"]
