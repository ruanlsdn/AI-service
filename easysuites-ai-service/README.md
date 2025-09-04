# Easysuites Web Crawler Service

Serviço de web crawler inteligente para automação de interações web e extração de dados, desenvolvido para o ecossistema EasySuites.

## 📋 Visão Geral

Este serviço implementa as funcionalidades especificadas no PRD_Easysuites_WebCrawler.md, fornecendo:

- **Teste de Autenticação**: Validação de fluxos de login com detecção inteligente de formulários
- **Detecção de Campos**: Mapeamento automático de elementos web (inputs, botões, tabelas, listas)
- **Resiliência**: Estratégias de fallback para casos de falha
- **Integração com IA**: Utilização de GPT-4o-mini para análise inteligente

## 🚀 Tecnologias Utilizadas

- **Python 3.8+**
- **FastAPI**: Framework web moderno e rápido
- **Playwright**: Automação de navegador
- **Browser-use**: Integração com LLM para análise web
- **Pydantic**: Validação de dados
- **OpenAI GPT-4o-mini**: Processamento inteligente

## 📦 Instalação

### Pré-requisitos

```bash
# Python 3.8 ou superior
python --version

# Playwright browsers
playwright install chromium
```

### Instalação das Dependências

```bash
# Clone o repositório
git clone <repository-url>
cd easysuites-ai-service

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves de API
```

### Variáveis de Ambiente

Crie um arquivo `.env` com as seguintes variáveis:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Service Configuration
PORT=8000
HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
```

## 🏃‍♂️ Como Executar

### Desenvolvimento

```bash
# Executar com reload automático
python -m src.main

# Ou usando uvicorn diretamente
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Produção

```bash
# Executar com configurações de produção
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📡 Endpoints da API

### 1. Teste de Autenticação

Valida fluxos de login em websites.

**Endpoint:** `POST /api/v1/web-crawlers/auth-test`

**Request:**
```json
{
  "url": "https://example.com/login",
  "credentials": {
    "username": "seu_usuario",
    "password": "sua_senha",
    "email": "usuario@example.com"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Autenticação bem-sucedida",
  "execution_time": 3.5,
  "request_id": "uuid-unico",
  "timestamp": "2024-01-01T00:00:00"
}
```

### 2. Detecção de Campos

Detecta e mapeia elementos web em páginas.

**Endpoint:** `POST /api/v1/web-crawlers/field-detection`

**Request:**
```json
{
  "url": "https://example.com/form"
}
```

**Response:**
```json
{
  "success": true,
  "fields": [
    {
      "name": "Campo de Email",
      "type": "email",
      "selector": "input[type='email']",
      "description": "Campo de entrada para endereço de email",
      "columns": []
    },
    {
      "name": "Tabela de Dados",
      "type": "table",
      "selector": "table.data-table",
      "description": "Tabela com dados de usuários",
      "columns": ["Nome", "Email", "Telefone"]
    }
  ],
  "execution_time": 2.8,
  "request_id": "uuid-unico",
  "timestamp": "2024-01-01T00:00:00",
  "warning": null
}
```

### 3. Health Check

Verifica o status do serviço.

**Endpoint:** `GET /api/v1/web-crawlers/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "service": "easysuites-web-crawler"
}
```

### 4. Documentação Interativa

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## 🧪 Testes

### Executar Testes

```bash
# Executar todos os testes
pytest tests/

# Executar com cobertura
pytest tests/ --cov=src --cov-report=html

# Executar testes específicos
pytest tests/test_endpoints.py -v
```

### Tipos de Testes

- **Testes de Endpoint**: Validação dos endpoints REST
- **Testes de Schema**: Validação dos modelos Pydantic
- **Testes de Integração**: Fluxos completos de uso
- **Testes de Erro**: Tratamento de exceções

## 🎯 Exemplos de Uso

### Exemplo 1: Teste de Login

```python
import requests

# Testar autenticação
response = requests.post("http://localhost:8000/api/v1/web-crawlers/auth-test", json={
    "url": "https://example.com/login",
    "credentials": {
        "username": "admin",
        "password": "secret123"
    }
})

print(f"Status: {response.json()['success']}")
print(f"Mensagem: {response.json()['message']}")
```

### Exemplo 2: Detecção de Campos

```python
import requests

# Detectar campos em uma página
response = requests.post("http://localhost:8000/api/v1/web-crawlers/field-detection", json={
    "url": "https://example.com/formulario"
})

fields = response.json()['fields']
for field in fields:
    print(f"Campo: {field['name']} - Tipo: {field['type']}")
    print(f"Seletor: {field['selector']}")
    print(f"Descrição: {field['description']}")
    print("---")
```

### Exemplo 3: Fluxo Completo

```python
import requests
import time

# Passo 1: Detectar campos
fields_response = requests.post("http://localhost:8000/api/v1/web-crawlers/field-detection", json={
    "url": "https://example.com/login"
})

# Passo 2: Analisar campos detectados
login_fields = [f for f in fields_response.json()['fields'] if f['type'] in ['text', 'password', 'email']]
print(f"Campos de login encontrados: {len(login_fields)}")

# Passo 3: Testar autenticação
auth_response = requests.post("http://localhost:8000/api/v1/web-crawlers/auth-test", json={
    "url": "https://example.com/login",
    "credentials": {
        "username": "user@example.com",
        "password": "mypassword"
    }
})

print(f"Autenticação: {'Sucesso' if auth_response.json()['success'] else 'Falha'}")
```

## 🔧 Configuração Avançada

### Configuração de Proxy

```python
# Em src/services/browser_service.py
browser = await playwright.chromium.launch(
    headless=True,
    proxy={
        "server": "http://proxy-server:8080",
        "username": "proxy-user",
        "password": "proxy-pass"
    }
)
```

### Configuração de Timeout

```python
# Em src/services/browser_service.py
await page.goto(url, wait_until="networkidle", timeout=30000)
```

### Configuração de User-Agent

```python
# Em src/services/browser_service.py
context = await browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
```

## 📊 Monitoramento

### Logs

Os logs são configurados automaticamente com níveis:
- **INFO**: Operações normais
- **WARNING**: Situações de alerta
- **ERROR**: Erros críticos

### Métricas

Cada resposta inclui:
- `execution_time`: Tempo de execução em segundos
- `request_id`: ID único para rastreamento
- `timestamp`: Marca temporal da requisição

## 🚨 Solução de Problemas

### Problema: Playwright não encontrado

```bash
# Instalar browsers do Playwright
playwright install chromium

# Verificar instalação
playwright show-browsers
```

### Problema: Erro de permissão no Linux

```bash
# Instalar dependências do sistema
sudo apt-get install -y libnss3-dev libatk-bridge2.0-dev libdrm-dev libxcomposite-dev libxdamage-dev libxrandr-dev libgbm-dev libxss-dev libasound2-dev
```

### Problema: Timeout em páginas lentas

```bash
# Aumentar timeout no .env
BROWSER_TIMEOUT=60000
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença do EasySuites. Consulte o arquivo LICENSE para mais detalhes.

## 🆘 Suporte

Para suporte técnico ou dúvidas:

- **Email**: suporte@easysuites.com.br
- **Documentação**: /docs endpoint quando o serviço estiver rodando
- **Issues**: GitHub Issues do projeto

## 🔄 Changelog

### v1.0.0
- ✨ Implementação inicial dos endpoints de autenticação e detecção
- 🎯 Detecção inteligente de campos com fallback
- 🔐 Validação de fluxos de login
- 📊 Monitoramento e logging abrangente
- 🧪 Testes completos de integração
- 📚 Documentação interativa OpenAPI

---

Desenvolvido com ❤️ para o ecossistema EasySuites