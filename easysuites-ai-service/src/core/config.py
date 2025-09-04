from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from pathlib import Path

class Settings(BaseSettings):
    """Configurações do microserviço de autenticação"""
    
    # Configurações da API
    app_name: str = "EasySuites Authentication Service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"  # development, staging, production
    
    # Configurações do servidor
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Configurações de LLM
    llm_provider: str = "css"  # css, openai, ollama, huggingface
    
    # Configurações do OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.1
    openai_timeout: int = 30
    
    # Configurações do Ollama (local, gratuito)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"  # llama2, codellama, mistral, etc.
    ollama_timeout: int = 60
    
    # Configurações do HuggingFace
    huggingface_api_key: Optional[str] = None
    huggingface_model: str = "microsoft/DialoGPT-medium"
    
    # Configurações do navegador
    browser_headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    browser_timeout: int = 30000
    browser_navigation_timeout: int = 30000
    browser_wait_timeout: int = 10000
    browser_user_agent: Optional[str] = None
    browser_viewport_width: int = 1920
    browser_viewport_height: int = 1080
    browser_slow_mo: int = 0  # Delay em ms entre ações
    
    # Configurações de autenticação
    auth_max_retries: int = 3
    auth_default_timeout: int = 30000
    auth_retry_delay: int = 2000  # Delay entre tentativas em ms
    auth_captcha_timeout: int = 60000  # Timeout para resolução de CAPTCHA
    
    # Configurações de segurança
    api_key_header: str = "X-API-Key"
    api_key: Optional[str] = None
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hora em segundos
    
    # Configurações de logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file_enabled: bool = True
    log_file_path: str = "logs/auth_service.log"
    log_file_max_size: int = 10485760  # 10MB
    log_file_backup_count: int = 5
    log_json_format: bool = False
    
    # Configurações de CORS
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Configurações de monitoramento
    metrics_enabled: bool = True
    health_check_interval: int = 30  # segundos
    
    # Configurações de cache
    cache_enabled: bool = False
    cache_ttl: int = 300  # 5 minutos
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Mapeamento de variáveis de ambiente
        fields = {
            "llm_provider": {"env": "LLM_PROVIDER"},
            "openai_api_key": {"env": "OPENAI_API_KEY"},
            "openai_model": {"env": "OPENAI_MODEL"},
            "openai_max_tokens": {"env": "OPENAI_MAX_TOKENS"},
            "openai_temperature": {"env": "OPENAI_TEMPERATURE"},
            "openai_timeout": {"env": "OPENAI_TIMEOUT"},
            "ollama_base_url": {"env": "OLLAMA_BASE_URL"},
            "ollama_model": {"env": "OLLAMA_MODEL"},
            "ollama_timeout": {"env": "OLLAMA_TIMEOUT"},
            "huggingface_api_key": {"env": "HUGGINGFACE_API_KEY"},
            "huggingface_model": {"env": "HUGGINGFACE_MODEL"},
            "browser_headless": {"env": "BROWSER_HEADLESS"},
            "browser_type": {"env": "BROWSER_TYPE"},
            "browser_timeout": {"env": "BROWSER_TIMEOUT"},
            "browser_navigation_timeout": {"env": "BROWSER_NAVIGATION_TIMEOUT"},
            "browser_user_agent": {"env": "BROWSER_USER_AGENT"},
            "browser_slow_mo": {"env": "BROWSER_SLOW_MO"},
            "auth_max_retries": {"env": "AUTH_MAX_RETRIES"},
            "auth_retry_delay": {"env": "AUTH_RETRY_DELAY"},
            "auth_captcha_timeout": {"env": "AUTH_CAPTCHA_TIMEOUT"},
            "api_key": {"env": "API_KEY"},
            "rate_limit_requests": {"env": "RATE_LIMIT_REQUESTS"},
            "log_level": {"env": "LOG_LEVEL"},
            "log_file_enabled": {"env": "LOG_FILE_ENABLED"},
            "log_file_path": {"env": "LOG_FILE_PATH"},
            "log_json_format": {"env": "LOG_JSON_FORMAT"},
            "debug": {"env": "DEBUG"},
            "environment": {"env": "ENVIRONMENT"},
            "host": {"env": "HOST"},
            "port": {"env": "PORT"},
            "workers": {"env": "WORKERS"},
            "cors_origins": {"env": "CORS_ORIGINS"},
            "metrics_enabled": {"env": "METRICS_ENABLED"},
            "cache_enabled": {"env": "CACHE_ENABLED"}
        }
    
    def get_cors_origins(self) -> List[str]:
        """Processa as origens CORS de string para lista"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins
    
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção"""
        return self.environment.lower() == "production"
    
    def get_log_file_path(self) -> Path:
        """Retorna o caminho completo do arquivo de log"""
        log_path = Path(self.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path

# Instância global das configurações
settings = Settings()

# Validação das configurações de LLM
if settings.llm_provider == "openai" and not settings.openai_api_key:
    print("AVISO: LLM_PROVIDER configurado como 'openai' mas OPENAI_API_KEY não está configurada.")
    print("Configure a variável OPENAI_API_KEY ou mude LLM_PROVIDER para 'css' ou 'ollama'")
elif settings.llm_provider == "css":
    print("INFO: Usando estratégia CSS (sem LLM) para análise de páginas.")
elif settings.llm_provider == "ollama":
    print(f"INFO: Usando Ollama local ({settings.ollama_base_url}) com modelo {settings.ollama_model}.")
    print("Certifique-se de que o Ollama está rodando localmente.")

# Configurar a chave da OpenAI no ambiente se fornecida
if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key