# Usar imagem base Python
FROM python:3.11-slim

# Instalar dependências mínimas do sistema para Playwright
RUN apt-get update && apt-get install -y \
    # Dependências básicas para compilação
    gcc \
    # Dependências essenciais para Playwright/Chromium
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    # Limpeza
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar dependências do sistema para Playwright
RUN playwright install-deps

# Instalar apenas Chromium do Playwright (suficiente para MVP)
RUN playwright install chromium

# Definir variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copiar código da aplicação
COPY . /app/

# Expor porta
EXPOSE 8000

# Labels para metadados
LABEL maintainer="EasySuites Team" \
      version="1.0.0-mvp" \
      description="EasySuites AI Service - Web Crawler MVP" \
      org.opencontainers.image.source="https://github.com/easysuites/easysuites-ai-service"

# Comando para iniciar a aplicação
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]